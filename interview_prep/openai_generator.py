"""Provider client and role-aware, evidence-grounded preparation pipeline."""

import json
import hashlib
import logging
import re
import time
from difflib import SequenceMatcher
from copy import deepcopy
from pathlib import Path

import requests
from django.conf import settings

from .answer_content import answer_content_texts, validate_answer_content
from .blueprint import build_competency_blueprint
from .intelligence_schema import (
    OUTPUT_SCHEMA_VERSION,
    PIPELINE_VERSION,
    PROMPT_VERSION,
    QUESTIONS_PER_ROUND,
    ROUND_COUNT,
    validate_intelligence_output,
)
from .market_research import research_job_market
from .prompts import INTERVIEWER_SYSTEM_PROMPT, INPUT_ANALYSIS_SCHEMA, QUESTION_BATCH_SCHEMA
from .role_profiles import PROFILE_VERSION, get_role_profile
from .role_profiles import SENIORITY_LEVELS

logger = logging.getLogger(__name__)

QUESTION_VARIATION_ANGLES = (
    'diagnose an unexpected failure',
    'compare two approaches and explain a trade-off',
    'design a step-by-step solution',
    'review an imperfect result and improve it',
    'explain findings to a non-technical stakeholder',
    'prioritize work under a real constraint',
    'define checks and success measures',
    'respond to a changed requirement',
    'reflect on a specific project decision',
    'investigate an ambiguous situation before acting',
)

ANSWER_PLACEHOLDER_PATTERNS = (
    re.compile(r'\boption\s+[ab]\b', re.IGNORECASE),
    re.compile(r'what it improves', re.IGNORECASE),
    re.compile(r'cost or limitation to check', re.IGNORECASE),
    re.compile(r'_{3,}'),
    re.compile(r'\bfill in the blanks?\b', re.IGNORECASE),
    re.compile(r'\binsert your example here\b', re.IGNORECASE),
    re.compile(r'\[\s*(?:real project|your responsibility|the steps you took|the outcome)', re.IGNORECASE),
)

_QUESTION_STOP_WORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'between', 'by', 'can', 'could',
    'describe', 'do', 'does', 'explain', 'for', 'from', 'give', 'how', 'if',
    'in', 'into', 'is', 'it', 'its', 'of', 'on', 'or', 'our', 'please',
    'should', 'the', 'their', 'them', 'then', 'this', 'through', 'to', 'under',
    'use', 'using', 'what', 'when', 'where', 'which', 'who', 'why', 'will',
    'with', 'would', 'you', 'your', 'approach',
}
_QUESTION_SYNONYMS = {
    'analyse': 'analyze', 'analysing': 'analyze', 'analyzed': 'analyze',
    'investigate': 'diagnose', 'investigating': 'diagnose', 'investigation': 'diagnose',
    'decline': 'decrease', 'dropped': 'decrease', 'drop': 'decrease', 'fall': 'decrease',
    'combine': 'merge', 'combining': 'merge', 'merged': 'merge', 'merging': 'merge',
    'datasets': 'dataset', 'tables': 'table', 'records': 'record', 'rows': 'row',
    'tradeoffs': 'tradeoff', 'trade-offs': 'tradeoff', 'versus': 'vs',
}


class PreparationProviderError(Exception):
    """Raised when the configured model cannot return valid preparation."""


def preparation_fingerprint(resume_text, job_description, company_name, job_title, role_family, seniority, previous_questions=None):
    """Hash normalized inputs without storing the resume or its extracted facts."""
    _, model, _ = _provider_config()
    material = {
        'resume': resume_text,
        'job_description': job_description,
        'company': company_name or '',
        'job_title': job_title,
        'role_family': role_family,
        'seniority': seniority,
        'model': model,
        'provider': settings.INTERVIEW_PREP_AI_PROVIDER,
        'pipeline': PIPELINE_VERSION,
        'prompt': PROMPT_VERSION,
        'profile': PROFILE_VERSION,
        'ratio': settings.INTERVIEW_PREP_STANDARD_QUESTION_RATIO,
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def _provider_config():
    provider = settings.INTERVIEW_PREP_AI_PROVIDER
    if provider == 'groq':
        return settings.INTERVIEW_PREP_GROQ_API_KEY, settings.INTERVIEW_PREP_GROQ_MODEL, 'https://api.groq.com/openai/v1/responses'
    if provider == 'openai':
        return settings.INTERVIEW_PREP_OPENAI_API_KEY, settings.INTERVIEW_PREP_OPENAI_MODEL, 'https://api.openai.com/v1/responses'
    raise PreparationProviderError('The selected preparation provider is not supported.')


def is_provider_configured():
    try:
        key, _, _ = _provider_config()
    except PreparationProviderError:
        return False
    return bool(key)


def _request_json(instructions, dynamic_input, schema, model, endpoint, api_key, max_tokens=3500, groq_json_mode=False):
    """Call the selected provider, retrying one transport/format failure."""
    request_endpoint = endpoint
    retry_input = {**dynamic_input, 'required_output_schema': schema}
    json_object_fallback = settings.INTERVIEW_PREP_AI_PROVIDER == 'groq' and groq_json_mode
    fallback_instructions = instructions + (
        '\nReturn one valid JSON object matching required_output_schema in the user input. '
        'Keep it concise and include all required fields. The application validates the result before use.'
    )
    payload = {
        'model': model,
        'max_output_tokens': max_tokens,
        'instructions': instructions,
        'input': json.dumps(dynamic_input, ensure_ascii=False),
        'text': {'format': {
            'type': 'json_schema',
            'name': 'interview_intelligence',
            'strict': True,
            'schema': schema,
        }},
    }
    if settings.INTERVIEW_PREP_AI_PROVIDER == 'groq' and model.startswith('openai/gpt-oss-'):
        # Lower reasoning overhead helps avoid Groq's per-minute token ceiling
        # during the sequence of small question batches.
        payload['reasoning'] = {'effort': 'low'}
    if settings.INTERVIEW_PREP_AI_PROVIDER == 'openai':
        payload['store'] = False

    if json_object_fallback:
        request_endpoint = endpoint.rsplit('/', 1)[0] + '/chat/completions'
        payload = {
            'model': model,
            'max_completion_tokens': max_tokens,
            'messages': [
                {'role': 'system', 'content': fallback_instructions},
                {'role': 'user', 'content': json.dumps(retry_input, ensure_ascii=False)},
            ],
            'response_format': {'type': 'json_object'},
        }
        if model.startswith('openai/gpt-oss-'):
            payload['reasoning_effort'] = 'low'

    last_error = None
    rate_limit_retries = 0
    schema_retries = 0
    transient_retries = 0
    json_object_retries = 0
    for attempt in range(6):
        started = time.monotonic()
        try:
            response = requests.post(
                request_endpoint,
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json=payload,
                timeout=(5, 90),
            )
            try:
                response.raise_for_status()
            except requests.HTTPError:
                try:
                    error_data = response.json().get('error', {})
                except (ValueError, AttributeError):
                    error_data = {}
                logger.warning(
                    'Interview AI provider rejected request: provider=%s status=%s code=%s message=%s',
                    settings.INTERVIEW_PREP_AI_PROVIDER,
                    response.status_code,
                    error_data.get('code', 'unknown'),
                    str(error_data.get('message', 'No provider error message'))[:240],
                )
                raise
            data = response.json()
            if json_object_fallback:
                choices = data.get('choices', [])
                message = choices[0].get('message', {}) if choices and isinstance(choices[0], dict) else {}
                text = message.get('content', '') if isinstance(message, dict) else ''
                if not isinstance(text, str) or not text:
                    logger.warning('Groq Chat Completions JSON fallback returned no message content.')
                    raise ValueError('Incomplete JSON fallback response')
            else:
                text = ''.join(
                    part['text']
                    for item in data.get('output', []) if item.get('type') == 'message'
                    for part in item.get('content', [])
                    if part.get('type') == 'output_text' and isinstance(part.get('text'), str)
                )
                if data.get('status') != 'completed' or not text:
                    logger.warning(
                        'Interview AI provider returned no completed text: provider=%s status=%s output_types=%s',
                        settings.INTERVIEW_PREP_AI_PROVIDER,
                        data.get('status', 'missing'),
                        [item.get('type') for item in data.get('output', []) if isinstance(item, dict)],
                    )
                    raise ValueError('Incomplete model response')
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise ValueError('Expected a JSON object')
            usage = data.get('usage') or {}
            return parsed, {
                'input_tokens': int(usage.get('input_tokens', usage.get('prompt_tokens', 0)) or 0),
                'output_tokens': int(usage.get('output_tokens', usage.get('completion_tokens', 0)) or 0),
                'elapsed_ms': int((time.monotonic() - started) * 1000),
                'api_calls': 1,
            }
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError) as exc:
            last_error = exc
            is_rate_limited = isinstance(exc, requests.HTTPError) and getattr(exc.response, 'status_code', None) == 429
            provider_error = {}
            if isinstance(exc, requests.HTTPError):
                try:
                    provider_error = exc.response.json().get('error', {})
                except (ValueError, AttributeError):
                    provider_error = {}
            is_schema_validation_error = (
                isinstance(exc, requests.HTTPError)
                and getattr(exc.response, 'status_code', None) == 400
                and provider_error.get('code') == 'json_validate_failed'
            )
            is_transient = (
                not isinstance(exc, requests.HTTPError)
                or getattr(exc.response, 'status_code', 0) >= 500
            )
            if is_rate_limited and rate_limit_retries < 3 and attempt < 5:
                rate_limit_retries += 1
                try:
                    wait_seconds = float(exc.response.headers.get('Retry-After', 0))
                except (TypeError, ValueError):
                    wait_seconds = 0
                if wait_seconds <= 0:
                    try:
                        message = exc.response.json().get('error', {}).get('message', '')
                    except (ValueError, AttributeError):
                        message = ''
                    match = re.search(r'try again in ([0-9.]+)s', message, re.IGNORECASE)
                    wait_seconds = float(match.group(1)) if match else 5
                time.sleep(min(max(wait_seconds, 1), 60))
            elif is_schema_validation_error:
                if json_object_fallback and json_object_retries < 2 and attempt < 5:
                    json_object_retries += 1
                    retry_input['json_mode_retry'] = (
                        'The previous JSON response was rejected. Return a fresh, complete object matching the schema. '
                        'Keep every answer concise and ensure the JSON is syntactically valid.'
                    )
                    payload['max_completion_tokens'] = int(payload.get('max_completion_tokens', max_tokens)) + 800
                    payload['messages'][1]['content'] = json.dumps(retry_input, ensure_ascii=False)
                    logger.info('Retrying Groq JSON-mode generation after provider rejection (retry=%s).', json_object_retries)
                elif not json_object_fallback and schema_retries < 2 and attempt < 5:
                    schema_retries += 1
                    retry_input = dict(dynamic_input)
                    retry_input['schema_validation_retry'] = (
                        'The provider rejected the previous generated content against the supplied JSON schema. '
                        'Regenerate the response and ensure every field, array item, enum value, and evidence ID '
                        'strictly matches the schema. Do not copy an invalid value from the previous attempt.'
                    )
                    payload['input'] = json.dumps(retry_input, ensure_ascii=False)
                    payload['instructions'] = instructions + (
                        '\nThe previous attempt failed provider-side JSON schema validation. '
                        'Return only a response that exactly matches every schema constraint.'
                    )
                    logger.info('Retrying provider-side structured-output validation failure (retry=%s).', schema_retries)
                elif settings.INTERVIEW_PREP_AI_PROVIDER == 'groq' and not json_object_fallback and attempt < 5:
                    # Keep a final recovery path for provider/model schema-decoding
                    # failures. The caller still validates the returned object
                    # locally before it can be persisted.
                    json_object_fallback = True
                    retry_input = dict(dynamic_input)
                    retry_input['required_output_schema'] = schema
                    retry_input['schema_validation_retry'] = (
                        'Strict schema-constrained generation failed. Return one valid JSON object that follows '
                        'required_output_schema exactly, including every required field and allowed enum value. '
                        'Do not include Markdown fences or explanatory text.'
                    )
                    payload['input'] = json.dumps(retry_input, ensure_ascii=False)
                    fallback_instructions = instructions + (
                        '\nReturn a valid JSON object matching the required_output_schema in the user input exactly. '
                        'The application validates it against the full schema before use.'
                    )
                    request_endpoint = endpoint.rsplit('/', 1)[0] + '/chat/completions'
                    payload = {
                        'model': model,
                        'max_completion_tokens': max_tokens,
                        'messages': [
                            {'role': 'system', 'content': fallback_instructions},
                            {'role': 'user', 'content': json.dumps(retry_input, ensure_ascii=False)},
                        ],
                        'response_format': {'type': 'json_object'},
                    }
                    if model.startswith('openai/gpt-oss-'):
                        payload['reasoning_effort'] = 'low'
                    logger.warning('Groq strict structured output failed; retrying once in JSON object mode with local validation.')
                else:
                    break
            elif json_object_fallback and isinstance(exc, ValueError) and json_object_retries < 2 and attempt < 5:
                json_object_retries += 1
                retry_input['json_mode_retry'] = 'The previous response was incomplete or invalid JSON. Return a fresh complete JSON object, concisely.'
                payload['max_completion_tokens'] = int(payload.get('max_completion_tokens', max_tokens)) + 800
                payload['messages'][1]['content'] = json.dumps(retry_input, ensure_ascii=False)
                logger.warning('Retrying Groq JSON-mode generation after malformed JSON output (retry=%s).', json_object_retries)
            elif is_transient and transient_retries < 2 and attempt < 5:
                transient_retries += 1
                time.sleep(transient_retries)
            elif not is_rate_limited and not is_schema_validation_error:
                break
    if isinstance(last_error, requests.HTTPError) and getattr(last_error.response, 'status_code', None) == 429:
        raise PreparationProviderError(
            'Groq has reached its current rate limit. Wait for the limit to reset, then retry; no preparation was saved.'
        ) from last_error
    if isinstance(last_error, requests.HTTPError) and getattr(last_error.response, 'status_code', None) == 400:
        try:
            final_error = last_error.response.json().get('error', {})
        except (ValueError, AttributeError):
            final_error = {}
        if final_error.get('code') == 'json_validate_failed':
            raise PreparationProviderError(
                'Your interviewer could not complete this set yet. Your role details are still available; please try again.'
            ) from last_error
        raise PreparationProviderError(
            'Your interviewer could not prepare this set. Please contact support if the problem continues.'
        ) from last_error
    if isinstance(last_error, requests.HTTPError):
        status_code = getattr(last_error.response, 'status_code', None)
        if status_code in {401, 403}:
            raise PreparationProviderError(
                'The interview preparation service could not authenticate. Please contact support.'
            ) from last_error
        if status_code == 404:
            raise PreparationProviderError(
                'The interview preparation service is not configured correctly. Please contact support.'
            ) from last_error
        if status_code is not None and status_code < 500:
            raise PreparationProviderError(
                f'Your interviewer could not prepare this set (error {status_code}). Please contact support.'
            ) from last_error
    logger.error(
        'Interview AI request failed after retries: provider=%s error_type=%s',
        settings.INTERVIEW_PREP_AI_PROVIDER,
        type(last_error).__name__ if last_error else 'unknown',
    )
    raise PreparationProviderError('The interview preparation service is temporarily unavailable. Please try again shortly.') from last_error


def _question_bank(role_family):
    path = Path(__file__).with_name('question_bank.json')
    entries = json.loads(path.read_text(encoding='utf-8')).get('entries', [])
    return [entry for entry in entries if entry.get('role_profile') in {role_family, 'general-software-engineering'}]


def _numbered_evidence(items, prefix, value_key):
    clean = []
    id_map = {}
    for index, item in enumerate(items[:30], start=1):
        if not isinstance(item, dict) or not str(item.get(value_key, '')).strip():
            continue
        identifier = f'{prefix}-{len(clean) + 1:02d}'
        if item.get('id'):
            id_map[item['id']] = identifier
        clean.append({**item, 'id': identifier})
    return clean, id_map


def _check_extraction(extracted):
    if not isinstance(extracted.get('analysis'), str) or not extracted['analysis'].strip():
        raise PreparationProviderError('Your interviewer could not complete the role review. Please try again.')
    facts, fact_id_map = _numbered_evidence(extracted.get('resume_facts', []), 'RES', 'fact')
    requirements, requirement_id_map = _numbered_evidence(extracted.get('jd_requirements', []), 'JD', 'requirement')
    if not requirements:
        raise PreparationProviderError('The job description did not produce usable requirements.')
    for requirement in requirements:
        raw_refs = requirement.get('resume_fact_refs', [])
        refs = [fact_id_map[ref] for ref in raw_refs if ref in fact_id_map] if isinstance(raw_refs, list) else []
        requirement['resume_fact_refs'] = list(dict.fromkeys(refs))
        if not refs:
            requirement['match_level'] = 'not_evidenced'
            requirement['match_rationale'] = requirement.get('match_rationale') or 'No supporting example was found in the supplied resume.'
        elif requirement.get('match_level') not in {'strong', 'partial'}:
            requirement['match_level'] = 'partial'
        requirement['suggestion'] = str(requirement.get('suggestion', '')).strip() or (
            'Add a truthful resume example that shows how you used this skill, the scope of your work, and the result.'
        )
    gaps = extracted.get('skill_gaps', [])
    requirement_ids = {row['id'] for row in requirements}
    fact_ids = {row['id'] for row in facts}
    clean_gaps = []
    for gap in gaps:
        if not isinstance(gap, dict) or not str(gap.get('gap', '')).strip():
            continue
        requirement_ref = requirement_id_map.get(gap.get('requirement_ref'))
        if requirement_ref not in requirement_ids:
            continue
        refs = [fact_id_map[ref] for ref in gap.get('resume_fact_refs', []) if ref in fact_id_map]
        clean_gaps.append({
            'gap': gap['gap'].strip(),
            'evidence_refs': [requirement_ref, *refs],
        })
    return facts, requirements, clean_gaps, {**fact_id_map, **requirement_id_map}


def _build_jd_match(requirements):
    """Create a transparent, evidence-weighted resume/JD coverage estimate."""
    weights = {'strong': 1.0, 'partial': 0.5, 'not_evidenced': 0.0}
    total_weight = matched_weight = 0
    counts = {'strong': 0, 'partial': 0, 'not_evidenced': 0}
    for requirement in requirements:
        level = requirement.get('match_level', 'not_evidenced')
        if level not in weights:
            level = 'not_evidenced'
            requirement['match_level'] = level
        counts[level] += 1
        weight = 2 if requirement.get('mandatory') else 1
        total_weight += weight
        matched_weight += weight * weights[level]
    return {
        'score': round(100 * matched_weight / total_weight) if total_weight else 0,
        'total_requirements': len(requirements),
        'counts': counts,
        'method': 'Mandatory requirements count twice; strong evidence earns full credit, partial evidence half, and requirements not shown in the resume earn none.',
    }


def _question_tokens(text):
    tokens = re.findall(r'[a-z0-9]+', str(text or '').casefold())
    normalized = []
    for token in tokens:
        token = _QUESTION_SYNONYMS.get(token, token)
        if token.endswith('ies') and len(token) > 5:
            token = token[:-3] + 'y'
        elif token.endswith('s') and not token.endswith(('ss', 'us', 'is')) and len(token) > 4:
            token = token[:-1]
        if token not in _QUESTION_STOP_WORDS and len(token) > 2:
            normalized.append(token)
    return set(normalized)


def _questions_are_semantic_duplicates(candidate, earlier):
    """Conservative, offline duplicate check; similar topics alone are not enough."""
    candidate_text = str(candidate.get('question', '')).strip()
    earlier_text = str(earlier.get('question', '')).strip()
    if not candidate_text or not earlier_text:
        return False
    exact_normalize = lambda text: ' '.join(re.findall(r'[a-z0-9]+', text.casefold()))
    if exact_normalize(candidate_text) == exact_normalize(earlier_text):
        return True

    candidate_focus = str(candidate.get('assessment_focus', '')).strip()
    earlier_focus = str(earlier.get('assessment_focus', '')).strip()
    focus_tokens = _question_tokens(candidate_focus)
    earlier_focus_tokens = _question_tokens(earlier_focus)
    if len(focus_tokens) >= 3 and len(earlier_focus_tokens) >= 3:
        focus_shared = focus_tokens & earlier_focus_tokens
        focus_ratio = len(focus_shared) / max(1, min(len(focus_tokens), len(earlier_focus_tokens)))
        focus_jaccard = len(focus_shared) / max(1, len(focus_tokens | earlier_focus_tokens))
        focus_text_ratio = SequenceMatcher(None, ' '.join(sorted(focus_tokens)), ' '.join(sorted(earlier_focus_tokens))).ratio()
        if len(focus_shared) >= 3 and (focus_ratio >= 0.85 or focus_jaccard >= 0.72 or focus_text_ratio >= 0.90):
            return True
        # Similar wording can still test different skills (for example, a
        # metric investigation versus explaining the result to a stakeholder).
        # Let clearly different, specific focus labels distinguish those cases.
        if focus_ratio < 0.50 and focus_jaccard < 0.35:
            return False

    tokens = _question_tokens(candidate_text)
    earlier_tokens = _question_tokens(earlier_text)
    shared = tokens & earlier_tokens
    if len(shared) < 5:
        return False
    overlap = len(shared) / max(1, min(len(tokens), len(earlier_tokens)))
    jaccard = len(shared) / max(1, len(tokens | earlier_tokens))
    # Requiring strong overlap and several shared content words avoids treating
    # two questions about the same broad skill as duplicates.
    if overlap >= 0.78 and jaccard >= 0.58:
        return True
    # Catch paraphrases with extra context, such as "revise the promoted-sale
    # dashboard" versus "update a KPI definition and its reporting model".
    return len(shared) >= 6 and overlap >= 0.50 and jaccard >= 0.27


def _coverage_target(category, question_number, requirements, competencies, rotation=0):
    # Keep JD needs first, then offer role skills as alternatives. This gives
    # duplicate retries a different target instead of asking for another
    # wording of the same competency.
    candidates = [
        f"JD requirement: {row['requirement']}"
        for row in requirements
        if row.get('category') == category and row.get('requirement')
    ]
    category_competencies = [item for item in competencies if category.casefold() in item.casefold()]
    for competency in category_competencies or competencies:
        target = f'Role skill: {competency}'
        if target not in candidates:
            candidates.append(target)
    if candidates:
        index = (question_number - 1 + rotation) % len(candidates)
        return candidates[index]
    return f"Assess a distinct practical skill within {category}"


def _batch_validation_errors(questions, expected_types, expected_categories, evidence_ids, prior_questions):
    errors = []
    if not isinstance(questions, list) or len(questions) != len(expected_types):
        return ['incorrect question count']
    seen = [q for q in prior_questions if isinstance(q, dict)]
    for index, (question, expected_type, expected_category) in enumerate(zip(questions, expected_types, expected_categories), start=1):
        if not isinstance(question, dict):
            errors.append(f'question {index} is not an object')
            continue
        if not str(question.get('question', '')).strip() or not str(question.get('explanation', '')).strip():
            errors.append(f'question {index} is missing question text or question explanation')
        answer_content_errors = validate_answer_content(question.get('answer_content'))
        errors.extend(f'question {index} answer content: {error}' for error in answer_content_errors)
        answer_text = ' '.join(answer_content_texts(question.get('answer_content')))
        if any(pattern.search(answer_text) for pattern in ANSWER_PLACEHOLDER_PATTERNS):
            errors.append(f'question {index} answer guidance contains a generic placeholder')
        refs = question.get('evidence_refs')
        refs_valid = (
            isinstance(refs, list)
            and bool(refs)
            and all(isinstance(ref, str) and ref in evidence_ids for ref in refs)
        )
        if not refs_valid:
            errors.append(f'question {index} has missing or invalid evidence references')
        if expected_type == 'personalized' and refs_valid and not any(ref.startswith('RES-') for ref in refs):
            errors.append(f'question {index} is personalized without resume evidence')
        question_key = ' '.join(re.findall(r'[a-z0-9]+', str(question.get('question', '')).casefold()))
        seen_keys = {
            ' '.join(re.findall(r'[a-z0-9]+', str(earlier.get('question', '')).casefold()))
            for earlier in seen
        }
        if question_key and question_key in seen_keys:
            errors.append(f'question {index} repeats an exact earlier question')
        elif any(_questions_are_semantic_duplicates(question, earlier) for earlier in seen):
            errors.append(f'question {index} is semantically equivalent to an earlier question')
        elif str(question.get('question', '')).strip():
            seen.append(question)
    return errors


def _batch_is_valid(questions, expected_types, expected_categories, evidence_ids, prior_questions):
    return not _batch_validation_errors(questions, expected_types, expected_categories, evidence_ids, prior_questions)


def _invalid_question_indexes(errors, question_count):
    """Extract the bad slots so retries can replace only those questions."""
    if any('incorrect question count' in error for error in errors):
        return list(range(question_count))
    indexes = set()
    for error in errors:
        match = re.match(r'question (\d+)', error)
        if match:
            index = int(match.group(1)) - 1
            if 0 <= index < question_count:
                indexes.add(index)
    return sorted(indexes) or list(range(question_count))


def _quality_failure_message(errors):
    if errors and all('repeats an exact earlier question' in error or 'semantically equivalent' in error for error in errors):
        return "Your interviewer couldn't finalize this practice set because some questions overlapped too closely. No preparation was saved; please try again. Your job details are still available."
    if errors and all('evidence' in error for error in errors):
        return "Your interviewer couldn't connect some questions to the supplied experience. No preparation was saved; please try again. Your job details are still available."
    return "Your interviewer couldn't complete one question group. No preparation was saved; please try again. Your job details are still available."


def _only_semantic_overlap_errors(errors):
    """Whether a batch failed only a heuristic meaning-similarity check."""
    return bool(errors) and all('semantically equivalent' in error for error in errors)


def _duplicate_batch_questions(questions, prior_questions):
    """Return question texts that repeat earlier work so a retry can replace them."""
    if not isinstance(questions, list):
        return []
    seen = [row for row in prior_questions if isinstance(row, dict)]
    duplicates = []
    for question in questions:
        if not isinstance(question, dict):
            continue
        text = str(question.get('question', '')).strip()
        if text and any(_questions_are_semantic_duplicates(question, row) for row in seen):
            duplicates.append(text)
        elif text:
            seen.append(question)
    return duplicates


def _normalize_generated_evidence_refs(questions, valid_evidence_ids, evidence_aliases=None):
    """Map common unpadded model IDs such as RES-1 to canonical RES-01 IDs."""
    valid_evidence_ids = set(valid_evidence_ids)
    evidence_aliases = evidence_aliases or {}
    if not isinstance(questions, list):
        return
    for question in questions:
        if not isinstance(question, dict) or not isinstance(question.get('evidence_refs'), list):
            continue
        normalized_refs = []
        for ref in question['evidence_refs']:
            if isinstance(ref, str):
                ref = evidence_aliases.get(ref, ref)
                match = re.fullmatch(r'(RES|JD|ROLE|MKT)-(\d+)', ref)
                if match:
                    padded = f'{match.group(1)}-{int(match.group(2)):02d}'
                    if padded in valid_evidence_ids:
                        ref = padded
            normalized_refs.append(ref)
        question['evidence_refs'] = normalized_refs


def _question_batch_schema(valid_evidence_ids, question_count):
    """Constrain evidence IDs; batch size is validated after generation."""
    schema = deepcopy(QUESTION_BATCH_SCHEMA)
    reference_schema = schema['properties']['questions']['items']['properties']['evidence_refs']
    reference_schema['items']['enum'] = sorted(valid_evidence_ids)
    return schema


def generate_preparation(
    resume_text, job_description, company_name, job_title,
    role_family='general-software-engineering', seniority='entry', previous_questions=None,
    progress_callback=None, resume_content=None,
):
    """Analyze input, build a role blueprint, and generate two validated rounds."""
    api_key, model, endpoint = _provider_config()
    if not api_key:
        raise PreparationProviderError('Interview preparation is not available right now.')
    provider = settings.INTERVIEW_PREP_AI_PROVIDER
    retry_all_questions = bool((resume_content or {}).get('_generation_retry_all'))
    resume_rounds = {} if retry_all_questions else {
        int(row.get('round_number', index + 1)): row
        for index, row in enumerate((resume_content or {}).get('rounds', []))
        if isinstance(row, dict) and isinstance(row.get('questions'), list)
    }
    resumed_questions = [
        question for question_round in resume_rounds.values()
        for question in question_round.get('questions', []) if isinstance(question, dict)
    ]
    resumed_count = len(resumed_questions)
    if progress_callback:
        progress_callback({'phase': 'reviewing', 'completed': resumed_count, 'total': ROUND_COUNT * QUESTIONS_PER_ROUND,
                           'message': 'Reviewing your resume and role requirements…'})
    profile = get_role_profile(role_family)
    try:
        research = research_job_market(role_family, job_title, company_name)
    except Exception:
        # Research is optional; a provider outage never fabricates market facts
        # and never blocks preparation based on the supplied JD and role profile.
        research = {'status': 'unavailable', 'provider': None, 'sources': [], 'message': 'Current vacancy research was unavailable.'}

    source_input = {
        'target_role': job_title,
        'role_family': profile['label'],
        'seniority': {'level': seniority, **SENIORITY_LEVELS.get(seniority, {})},
        'company': company_name or None,
        'job_description': job_description,
        'resume_text': resume_text,
        'role_competencies': profile['competencies'],
        'role_categories': profile['categories'],
        'market_research': research,
    }
    extracted, usage = _request_json(
        INTERVIEWER_SYSTEM_PROMPT + '\nFirst analyze role requirements and extract explicit facts from the resume, including transferable evidence even when it does not directly match the target JD. Do not generate questions yet. Return an empty resume_facts list only if the supplied resume contains no readable experience, project, skills, or education facts.',
        source_input, INPUT_ANALYSIS_SCHEMA, model, endpoint, api_key, max_tokens=2500,
    )
    try:
        facts, requirements, skill_gaps, evidence_aliases = _check_extraction(extracted)
        if not facts:
            raise PreparationProviderError('The resume did not provide usable role-related evidence.')
    except PreparationProviderError:
        extracted, retry_usage = _request_json(
            INTERVIEWER_SYSTEM_PROMPT + '\nRepair the extraction: capture every explicit experience, project, tool, education, and transferable skill in the resume, even when it is not a direct JD match. Do not invent facts. Return usable resume facts and JD requirements with IDs, and ensure each skill gap references those IDs.',
            {**source_input, 'quality_retry': 'The first extraction contained no usable resume facts. Re-read the supplied resume carefully. Extract explicit and transferable facts without requiring exact JD keyword matches. Use unique RES-1... and JD-1... IDs and reference them consistently. Leave resume_facts empty only if the resume text contains no readable factual information.'},
            INPUT_ANALYSIS_SCHEMA, model, endpoint, api_key, max_tokens=2500,
        )
        usage['input_tokens'] += retry_usage['input_tokens']
        usage['output_tokens'] += retry_usage['output_tokens']
        usage['elapsed_ms'] += retry_usage['elapsed_ms']
        usage['api_calls'] += retry_usage['api_calls']
        facts, requirements, skill_gaps, evidence_aliases = _check_extraction(extracted)
        if not facts:
            raise PreparationProviderError('We could not identify readable experience, skills, projects, or education in the resume text. Paste the resume as plain text and include any transferable work or project examples.')
    jd_match = _build_jd_match(requirements)
    if progress_callback:
        progress_callback({'phase': 'questions', 'completed': resumed_count, 'total': ROUND_COUNT * QUESTIONS_PER_ROUND,
                           'message': 'Building question-specific practice answers…'})
    foundation_threshold = settings.INTERVIEW_PREP_FOUNDATION_MATCH_SCORE
    strong_alignment_threshold = settings.INTERVIEW_PREP_MINIMUM_JD_MATCH_SCORE
    if jd_match['score'] < foundation_threshold:
        preparation_strategy = 'Foundation-first: teach and practise role fundamentals, then build toward mandatory JD requirements not shown in the resume. Missing resume evidence does not mean the candidate lacks the skill.'
    elif jd_match['score'] < strong_alignment_threshold:
        preparation_strategy = 'Targeted: prioritize mandatory JD requirements with missing or partial resume evidence, then reinforce demonstrated skills with role scenarios.'
    else:
        preparation_strategy = 'Comprehensive: cover the role profile, mandatory and preferred JD requirements, resume examples, seniority expectations, and relevant scenarios.'
    market_sources = research.get('sources', [])
    profile_evidence = [{'id': f'ROLE-{index:02d}', 'competency': value} for index, value in enumerate(profile['competencies'], start=1)]
    market_sources = [{**source, 'id': f'MKT-{index:02d}'} for index, source in enumerate(market_sources, start=1)]
    evidence_ids = {row['id'] for row in [*facts, *requirements, *profile_evidence, *market_sources]}
    blueprint = build_competency_blueprint(
        role_family, requirements, facts,
        [source for source in market_sources if source.get('vacancy_status') == 'verified_open'],
        standard_ratio=settings.INTERVIEW_PREP_STANDARD_QUESTION_RATIO,
    )
    preparation_focus = sorted(
        requirements,
        key=lambda row: (
            not row.get('mandatory', False),
            {'not_evidenced': 0, 'partial': 1, 'strong': 2}.get(row.get('match_level'), 0),
            row.get('requirement', '').casefold(),
        ),
    )
    bank = _question_bank(role_family)
    bank_evidence_ids = {
        str(entry['id']) for entry in bank
        if isinstance(entry, dict) and entry.get('id')
    }
    evidence_ids.update(bank_evidence_ids)
    prior_preparation_questions = [
        {
            'question': str(item.get('question', ''))[:300],
            'assessment_focus': str(item.get('assessment_focus', ''))[:100],
        }
        for item in (previous_questions or [])
        if isinstance(item, dict) and str(item.get('question', '')).strip()
    ]
    # A second preparation for the same JD is expected to overlap with the
    # first. Keep a small sample as optional variation context; never require
    # novelty across separate preparations.
    prior_preparation_questions = prior_preparation_questions[-20:]
    rounds = []
    current_preparation_questions = list(resumed_questions)
    completed_question_count = resumed_count
    standard_count = blueprint['per_round']['standardized']
    category_counts = blueprint['per_round']['category_counts']
    category_sequence = []
    remaining_counts = dict(category_counts)
    while any(remaining_counts.values()):
        for category in profile['categories']:
            if remaining_counts.get(category, 0):
                category_sequence.append(category)
                remaining_counts[category] -= 1
    for round_number in range(1, ROUND_COUNT + 1):
        round_questions = list(resume_rounds.get(round_number, {}).get('questions', []))
        # Keep personalized questions in their own batch so the provider schema
        # can require resume evidence IDs for every item in that batch.
        batch_specs = []
        for question_type, start, end in (
            ('standardized', 0, standard_count),
            ('personalized', standard_count, QUESTIONS_PER_ROUND),
        ):
            # Compact Markdown answers let us keep reliable batches without
            # paying for repeated strict-schema decoding retries.
            for batch_start in range(start, end, 5):
                batch_end = min(batch_start + 5, end)
                batch_specs.append((batch_start, [question_type] * (batch_end - batch_start)))
        for batch_start, batch_types in batch_specs:
            if len(round_questions) >= batch_start + len(batch_types):
                continue
            batch_categories = category_sequence[batch_start:batch_start + len(batch_types)]
            batch_evidence_ids = (
                {identifier for identifier in evidence_ids if identifier.startswith('RES-')}
                if batch_types and all(kind == 'personalized' for kind in batch_types)
                else evidence_ids
            )
            batch_schema = _question_batch_schema(batch_evidence_ids, len(batch_types))
            batch_input = {
                'target_role': job_title,
                'seniority': seniority,
                'company': company_name or None,
                'role_profile': profile,
                'role_and_seniority_expectations': profile['seniority_expectation'].get(seniority, ''),
                'resume_facts': facts,
                'jd_requirements': requirements,
                'preparation_focus': [
                    {
                        'requirement': row['requirement'],
                        'category': row.get('category', ''),
                        'priority': ('mandatory gap' if row.get('mandatory') and row.get('match_level') == 'not_evidenced' else 'mandatory partial evidence' if row.get('mandatory') and row.get('match_level') == 'partial' else 'JD skill gap' if row.get('match_level') == 'not_evidenced' else 'partly evidenced JD skill' if row.get('match_level') == 'partial' else 'demonstrated skill to deepen'),
                        'resume_evidence_status': row.get('match_level', 'not_evidenced'),
                    }
                    for row in preparation_focus
                ],
                'preparation_strategy': preparation_strategy,
                'competency_blueprint': blueprint,
                'market_research': research,
                'question_bank_entries': bank,
                'prior_preparation_questions': prior_preparation_questions,
                'questions_already_in_this_preparation': [
                    {
                        'question': str(question.get('question', ''))[:300],
                        'assessment_focus': str(question.get('assessment_focus', ''))[:100],
                    }
                    for question in current_preparation_questions
                ],
                'current_round': round_number,
                'batch_start_index': batch_start,
                'question_types_in_order': batch_types,
                'question_categories_in_order': batch_categories,
                'question_slots': [
                    {
                        'question_number': batch_start + index + 1,
                        'question_type': kind,
                        'category': batch_categories[index],
                        'coverage_target': _coverage_target(
                            batch_categories[index], batch_start + index + 1,
                            preparation_focus, profile['competencies'], rotation=round_number - 1,
                        ),
                        'assessment_angle': QUESTION_VARIATION_ANGLES[(batch_start + index + (round_number - 1) * 3) % len(QUESTION_VARIATION_ANGLES)],
                    }
                    for index, kind in enumerate(batch_types)
                ],
                'personalized_evidence_ids': [identifier for identifier in evidence_ids if identifier.startswith('RES-')],
                'allowed_categories': profile['categories'],
                'valid_evidence_ids': sorted(batch_evidence_ids),
            }
            batch, batch_usage = _request_json(
                INTERVIEWER_SYSTEM_PROMPT + '\nGenerate only the requested question batch. Match question_type, category, assessment_angle, and coverage_target to each question_slots entry. Treat company as context only; the same JD and resume should produce substantially the same skill coverage regardless of company name. Questions in prior_preparation_questions are from separate saved sets: overlap is expected and is not a validation failure; use them only as optional context for useful scenario variation. Do not repeat a question already listed in questions_already_in_this_preparation or merely change a few words. Every personalized question must be explicitly about a supplied resume fact and cite at least one ID from personalized_evidence_ids. Standardized questions must remain role-based. Cite only valid evidence IDs.',
                batch_input, batch_schema, model, endpoint, api_key,
                max_tokens=4500,
                groq_json_mode=provider == 'groq',
            )
            batch_questions = batch.get('questions', [])
            if not isinstance(batch_questions, list) or len(batch_questions) != len(batch_types):
                batch_questions = [{} for _ in batch_types]
            _normalize_generated_evidence_refs(batch_questions, evidence_ids, evidence_aliases)
            # Keep final type/category allocation deterministic even if the
            # model uses a near-synonym in its structured response.
            if isinstance(batch_questions, list):
                for question, question_type, category in zip(batch_questions, batch_types, batch_categories):
                    if isinstance(question, dict):
                        question['question_type'] = question_type
                        question['category'] = category
            earlier_questions = [
                {
                    'question': str(question.get('question', ''))[:300],
                    'assessment_focus': str(question.get('assessment_focus', ''))[:100],
                }
                for question in current_preparation_questions if isinstance(question, dict)
            ]
            validation_errors = _batch_validation_errors(
                batch_questions, batch_types, batch_categories, evidence_ids, earlier_questions
            )
            for retry_number in range(3):
                if not validation_errors:
                    break
                invalid_indexes = _invalid_question_indexes(validation_errors, len(batch_types))
                logger.info(
                    'Interview question batch failed quality checks (round=%s start=%s retry=%s bad_slots=%s): %s',
                    round_number, batch_start, retry_number + 1,
                    [index + 1 for index in invalid_indexes], validation_errors[:10],
                )
                retry_types = [batch_types[index] for index in invalid_indexes]
                retry_categories = [batch_categories[index] for index in invalid_indexes]
                retry_slots = [
                    {
                        'question_number': batch_start + index + 1,
                        'question_type': batch_types[index],
                        'category': batch_categories[index],
                        'coverage_target': _coverage_target(
                            batch_categories[index], batch_start + index + 1,
                            preparation_focus, profile['competencies'], rotation=round_number + retry_number,
                        ),
                        'assessment_angle': QUESTION_VARIATION_ANGLES[(batch_start + index + (round_number - 1) * 3 + (retry_number + 1) * 4) % len(QUESTION_VARIATION_ANGLES)],
                    }
                    for index in invalid_indexes
                ]
                valid_siblings = [
                    {
                        'question': str(batch_questions[index].get('question', ''))[:300],
                        'assessment_focus': str(batch_questions[index].get('assessment_focus', ''))[:100],
                    }
                    for index in range(len(batch_questions))
                    if index not in invalid_indexes and isinstance(batch_questions[index], dict)
                ]
                retry_context = earlier_questions + valid_siblings
                retry_input = {
                    **batch_input,
                    'batch_start_index': batch_start + invalid_indexes[0],
                    'question_types_in_order': retry_types,
                    'question_categories_in_order': retry_categories,
                    'question_slots': retry_slots,
                    'questions_already_in_this_preparation': retry_context,
                    'prior_preparation_questions': prior_preparation_questions,
                    'quality_retry': 'The previous output failed these checks: ' + '; '.join(validation_errors[:10]) + '. Return exactly one replacement per question_slots entry. Follow each coverage_target and assessment_angle. Prior preparation questions are only optional variation context; overlap with another preparation is allowed. Do not repeat or semantically duplicate a question already in questions_already_in_this_preparation or duplicate_question_texts_to_replace. Select a different uncovered skill/decision for each replacement, not a synonym or broader rewrite. Write a substantive answer that directly teaches the specific question; do not use generic placeholders, fill-in templates, or generic Option A/Option B comparisons. Include complete answer guidance and explanation and only valid evidence IDs.',
                    'duplicate_question_texts_to_replace': _duplicate_batch_questions(batch_questions, retry_context),
                }
                retry_schema = _question_batch_schema(batch_evidence_ids, len(invalid_indexes))
                batch, retry_usage = _request_json(
                    INTERVIEWER_SYSTEM_PROMPT + '\nGenerate only the requested replacement questions. Match question_type, category, assessment_angle, and coverage_target to each question_slots entry. Treat prior preparations as optional variation context; repeated core questions across preparations are allowed. Do not repeat or semantically duplicate questions already in the current preparation. Every personalized question must be explicitly about a supplied resume fact and cite at least one ID from personalized_evidence_ids. Standardized questions must remain role-based. Cite only valid evidence IDs.',
                    retry_input, retry_schema, model, endpoint, api_key,
                    max_tokens=4500,
                    groq_json_mode=provider == 'groq',
                )
                batch_usage['input_tokens'] += retry_usage['input_tokens']
                batch_usage['output_tokens'] += retry_usage['output_tokens']
                batch_usage['elapsed_ms'] += retry_usage['elapsed_ms']
                batch_usage['api_calls'] += retry_usage['api_calls']
                replacements = batch.get('questions', [])
                if not isinstance(replacements, list):
                    replacements = []
                _normalize_generated_evidence_refs(replacements, evidence_ids, evidence_aliases)
                for offset, (question, question_type, category) in enumerate(zip(replacements, retry_types, retry_categories)):
                    if isinstance(question, dict):
                        question['question_type'] = question_type
                        question['category'] = category
                        batch_questions[invalid_indexes[offset]] = question
                validation_errors = _batch_validation_errors(
                    batch_questions, batch_types, batch_categories, evidence_ids, earlier_questions
                )
            if _only_semantic_overlap_errors(validation_errors):
                # Semantic similarity is a heuristic, and some related
                # interview questions legitimately share a scenario. After
                # targeted replacements have been attempted, prefer a complete
                # useful set over discarding it for an uncertain match. Exact
                # duplicate text and all structural/evidence errors still fail.
                logger.warning(
                    'Retaining semantically related questions after targeted replacements (round=%s start=%s count=%s).',
                    round_number, batch_start, len(validation_errors),
                )
                validation_errors = []
            if validation_errors:
                logger.warning(
                    'Interview question batch rejected after retries (round=%s start=%s): %s',
                    round_number, batch_start, validation_errors[:10],
                )
                raise PreparationProviderError(_quality_failure_message(validation_errors))
            usage['input_tokens'] += batch_usage['input_tokens']
            usage['output_tokens'] += batch_usage['output_tokens']
            usage['elapsed_ms'] += batch_usage['elapsed_ms']
            usage['api_calls'] += batch_usage['api_calls']
            for question_index, question in enumerate(batch_questions, start=len(round_questions) + 1):
                question['id'] = f'r{round_number}-q{question_index:02d}'
            round_questions.extend(batch_questions)
            current_preparation_questions.extend(batch_questions)
            completed_question_count += len(batch_questions)
            if progress_callback:
                progress_callback({
                    'phase': 'questions',
                    'completed': completed_question_count,
                    'total': ROUND_COUNT * QUESTIONS_PER_ROUND,
                    'round': round_number,
                    'message': f'Validated {completed_question_count} of {ROUND_COUNT * QUESTIONS_PER_ROUND} questions',
                    'preview_questions': [str(question.get('question', '')) for question in batch_questions],
                    'validated_questions': batch_questions,
                    'round_questions': list(round_questions),
                    'round_number': round_number,
                })
        rounds.append({'round_number': round_number, 'title': f'Practice round {round_number}', 'questions': round_questions})
    result = {
        'analysis': extracted['analysis'],
        'skill_gaps': skill_gaps,
        'requirements': requirements,
        'jd_match': jd_match,
        'evidence_catalog': [
            *[{'id': row['id'], 'source': f'Resume evidence {index}'} for index, row in enumerate(facts, 1)],
            *[{'id': row['id'], 'source': f'Job description requirement {index}'} for index, row in enumerate(requirements, 1)],
            *[{'id': row['id'], 'source': f'Role profile competency {index}'} for index, row in enumerate(profile_evidence, 1)],
            *[{'id': entry['id'], 'source': 'Saved role question bank'} for entry in bank if entry.get('id')],
            *[{'id': row['id'], 'source': row.get('title') or row.get('employer') or 'Verified market source', 'url': row['url'], 'published_at': row.get('published_at'), 'vacancy_status': row['vacancy_status']} for row in market_sources],
        ],
        'market_research': {'status': research['status'], 'message': research.get('message', ''), 'sources': market_sources},
        'blueprint': blueprint,
        'rounds': rounds,
        'versions': {
            'pipeline': PIPELINE_VERSION, 'prompt': PROMPT_VERSION,
            'schema': OUTPUT_SCHEMA_VERSION, 'role_profile': PROFILE_VERSION,
        },
        'generation_metrics': {
            'provider': provider,
            'model': model,
            **usage,
            'estimated_cost_usd': (
                round(
                    usage['input_tokens'] * settings.INTERVIEW_PREP_INPUT_USD_PER_MILLION_TOKENS / 1_000_000
                    + usage['output_tokens'] * settings.INTERVIEW_PREP_OUTPUT_USD_PER_MILLION_TOKENS / 1_000_000,
                    8,
                )
                if settings.INTERVIEW_PREP_INPUT_USD_PER_MILLION_TOKENS > 0
                and settings.INTERVIEW_PREP_OUTPUT_USD_PER_MILLION_TOKENS > 0
                else None
            ),
        },
    }
    errors = validate_intelligence_output(
        result, profile['categories'], evidence_ids,
        standard_ratio=settings.INTERVIEW_PREP_STANDARD_QUESTION_RATIO,
    )
    if errors:
        raise PreparationProviderError(
            'Your interviewer could not complete the final quality check. Please try again.'
        )
    return result
