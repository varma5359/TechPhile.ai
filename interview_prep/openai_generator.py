"""Provider client and role-aware, evidence-grounded preparation pipeline."""

import json
import hashlib
import logging
import math
import re
import time
from datetime import date
from difflib import SequenceMatcher
from copy import deepcopy
from pathlib import Path

import requests
from django.conf import settings

from .answer_content import answer_content_texts, validate_answer_content
from .blueprint import build_competency_blueprint, map_jd_requirements
from .candidate_profile import PROFILE_SECTIONS
from .intelligence_schema import (
    OUTPUT_SCHEMA_VERSION,
    PIPELINE_VERSION,
    PROMPT_VERSION,
    QUESTIONS_PER_ROUND,
    coding_prompt_errors,
    count_valid_unique_questions,
    filter_valid_unique_question_rounds,
    validate_intelligence_output,
)
from .market_research import research_job_market
from .prompts import INTERVIEWER_SYSTEM_PROMPT, INPUT_ANALYSIS_SCHEMA, QUESTION_BATCH_SCHEMA
from .role_profiles import (
    DATA_ANALYTICS_LEVEL_EXAMPLES,
    PROFILE_VERSION,
    SENIORITY_INTERVIEW_GUIDANCE,
    SENIORITY_LEVELS,
    get_role_profile,
)

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


def preparation_fingerprint(resume_text, job_description, company_name, job_title, role_family, seniority, previous_questions=None, target_question_count=None):
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
        'target_question_count': target_question_count,
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
                    'Interview AI provider rejected request: provider=%s status=%s code=%s',
                    settings.INTERVIEW_PREP_AI_PROVIDER,
                    response.status_code,
                    error_data.get('code', 'unknown'),
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
                or getattr(exc.response, 'status_code', 0) in {408, 425, 429}
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
            'The interview preparation service is busy. Your saved progress is available; please try again shortly.'
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
                'Interview preparation is temporarily unavailable. Please try again later or contact support if this continues.'
            ) from last_error
        if status_code == 404:
            raise PreparationProviderError(
                'Interview preparation is temporarily unavailable. Please try again later or contact support if this continues.'
            ) from last_error
        if status_code is not None and status_code < 500:
            raise PreparationProviderError(
                'Your interviewer could not finish this preparation. Your saved progress is available; please try again shortly.'
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
        clean.append({
            **item,
            value_key: str(item[value_key]).strip()[:500] if prefix == 'RES' else item[value_key],
            'id': identifier,
        })
        if prefix == 'RES' and clean[-1].get('fact_type') not in {
            'skill', 'education', 'project', 'experience', 'employment_history', 'certification', 'other',
        }:
            clean[-1]['fact_type'] = 'other'
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


def _clean_career_gaps(extracted, evidence_aliases, facts):
    """Derive timeline gaps from explicit employment intervals, never model durations.

    A missing or ambiguous date on any employment entry makes chronology
    incomplete, so no gap is asserted. Year-only dates are intentionally
    insufficient to establish a six-month interval.
    """
    del extracted, evidence_aliases  # Model-authored gap claims are not evidence.
    employment = [row for row in facts if row.get('fact_type') == 'employment_history']
    if len(employment) < 2:
        return []

    month_names = {
        name.casefold(): index for index, names in enumerate((
            ('jan', 'january'), ('feb', 'february'), ('mar', 'march'),
            ('apr', 'april'), ('may',), ('jun', 'june'), ('jul', 'july'),
            ('aug', 'august'), ('sep', 'sept', 'september'), ('oct', 'october'),
            ('nov', 'november'), ('dec', 'december'),
        ), start=1) for name in names
    }
    month_pattern = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
    date_pattern = re.compile(
        rf'(?<![a-z0-9])(?:{month_pattern}\s+\d{{4}}|\d{{4}}\s+{month_pattern}|(?:0?[1-9]|1[0-2])[/.-]\d{{4}}|\d{{4}}[/.-](?:0?[1-9]|1[0-2]))(?!\d)',
        re.I,
    )

    def to_month(value):
        parts = re.findall(r'[a-z]+|\d+', value.casefold())
        if len(parts) != 2:
            return None
        if parts[0].isalpha():
            month, year = month_names.get(parts[0]), parts[1]
        elif parts[1].isalpha():
            month, year = month_names.get(parts[1]), parts[0]
        elif len(parts[0]) == 4:
            year, month = parts[0], parts[1]
        else:
            month, year = int(parts[0]), parts[1]
        try:
            year = int(year)
            month = int(month)
        except (TypeError, ValueError):
            return None
        if not 1900 <= year <= date.today().year or not 1 <= month <= 12:
            return None
        return year * 12 + month - 1

    current_month = date.today().year * 12 + date.today().month - 1
    intervals = []
    for row in employment:
        fact = str(row.get('fact', ''))
        dates = list(date_pattern.finditer(fact))
        is_current = bool(re.search(r'\b(?:present|current|currently|now)\b', fact, re.I))
        if not row.get('id') or len(dates) != (1 if is_current else 2):
            return []
        start = to_month(dates[0].group())
        end = current_month if is_current else to_month(dates[1].group())
        if start is None or end is None or start > end:
            return []
        intervals.append((start, end, [row['id']]))

    intervals.sort(key=lambda item: (item[0], item[1]))
    merged = []
    for start, end, refs in intervals:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end), list(dict.fromkeys([*merged[-1][2], *refs])))
        else:
            merged.append((start, end, refs))

    def label(month_index):
        return f'{("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[month_index % 12]} {month_index // 12}'

    gaps = []
    for previous, following in zip(merged, merged[1:]):
        months = following[0] - previous[1] - 1
        if months >= 6:
            gaps.append({
                'period': f'{label(previous[1] + 1)}–{label(following[0] - 1)}',
                'months': months,
                'evidence_refs': list(dict.fromkeys([*previous[2], *following[2]])),
                'reason_stated': False,
            })
    return gaps


def extract_candidate_profile(resume_text, job_description, job_title, role_family, requested_seniority='entry'):
    """Extract a reviewable profile and evidence from pasted resume text."""
    api_key, model, endpoint = _provider_config()
    if not api_key:
        raise PreparationProviderError('Interview preparation is not available right now.')
    role_profile = get_role_profile(role_family)
    dynamic_input = {
        'target_role': job_title,
        'role_family': role_profile['label'],
        'requested_seniority': {'level': requested_seniority, **SENIORITY_LEVELS.get(requested_seniority, {})},
        'job_description': job_description,
        'resume_text': resume_text,
        'role_competencies': role_profile['competencies'],
        'role_categories': role_profile['categories'],
    }
    instructions = (
        INTERVIEWER_SYSTEM_PROMPT
        + '\nExtract the candidate profile and job requirements for review before creating questions. '
        'Separate skills, education, projects, experience, employment history and dates, certifications, '
        'and other explicit resume details. Do not duplicate a detail across categories unless useful. '
        'Recommend the most defensible target seniority based on stated role duration, responsibility, '
        'scope, and outcomes; explain the evidence and list missing or uncertain facts as questions. '
        'Never invent a date, qualification, skill, responsibility, or reason for a gap. '
        'Return only the required structured output.'
    )
    extracted, _usage = _request_json(
        instructions, dynamic_input, INPUT_ANALYSIS_SCHEMA, model, endpoint, api_key,
        max_tokens=2800,
    )
    try:
        facts, requirements, skill_gaps, evidence_aliases = _check_extraction(extracted)
        if not facts:
            raise PreparationProviderError('The resume did not provide usable role-related evidence.')
    except PreparationProviderError:
        extracted, _usage = _request_json(
            instructions + '\nThe previous output did not contain usable resume facts. Re-read the resume carefully and repair the extraction without inventing details.',
            {**dynamic_input, 'quality_retry': 'Extract at least one explicit skill, education, project, experience, employment, certification, or transferable detail if present.'},
            INPUT_ANALYSIS_SCHEMA, model, endpoint, api_key, max_tokens=2800,
        )
        facts, requirements, skill_gaps, evidence_aliases = _check_extraction(extracted)
        if not facts:
            raise PreparationProviderError('We could not identify readable details in the resume. Add skills, education, projects, or work examples and try again.')

    career_gaps = _clean_career_gaps(extracted, evidence_aliases, facts)
    canonical_skill_gaps = []
    for gap in skill_gaps:
        refs = gap.get('evidence_refs', [])
        requirement_ref = next((ref for ref in refs if ref.startswith('JD-')), '')
        fact_refs = [ref for ref in refs if ref.startswith('RES-')]
        if requirement_ref:
            canonical_skill_gaps.append({
                'gap': gap['gap'], 'requirement_ref': requirement_ref,
                'resume_fact_refs': fact_refs,
            })
    canonical = {
        'analysis': extracted['analysis'],
        'resume_facts': facts,
        'jd_requirements': requirements,
        'skill_gaps': canonical_skill_gaps,
        'career_gaps': career_gaps,
        'recommended_seniority': extracted.get('recommended_seniority')
        if extracted.get('recommended_seniority') in SENIORITY_LEVELS else requested_seniority,
        'seniority_rationale': str(extracted.get('seniority_rationale', '')).strip(),
        'uncertain_information': [
            str(item).strip()[:300] for item in extracted.get('uncertain_information', [])
            if isinstance(item, str) and item.strip()
        ][:12],
    }
    section_by_type = {key: [] for key, _label in PROFILE_SECTIONS}
    type_to_section = {
        'skill': 'skills', 'education': 'education', 'project': 'projects',
        'experience': 'experience', 'employment_history': 'employment_history',
        'certification': 'certifications', 'other': 'other_details',
    }
    for fact in facts:
        section = type_to_section.get(fact.get('fact_type'), 'other_details')
        section_by_type[section].append({'id': fact['id'], 'text': fact['fact']})
    return {
        **section_by_type,
        'summary': canonical['analysis'][:1200],
        'recommended_seniority': canonical['recommended_seniority'],
        'seniority_rationale': canonical['seniority_rationale'],
        'uncertain_information': canonical['uncertain_information'],
        'career_gaps': career_gaps,
        'extraction': canonical,
    }


def _question_plan(facts, job_description, role_family, seniority, career_gaps=None, company_name='', target_question_count=None, requirements=None):
    """Select 30 or 60 questions and evidence-backed question allocations."""
    facts_text = ' '.join(
        f"{row.get('fact', '')} {' '.join(row.get('competencies', []))}"
        for row in facts
    ).casefold()
    technical_families = {
        'general-software-engineering', 'data-analytics', 'business-analytics',
        'machine-learning-engineering', 'computer-vision-engineering',
        'generative-ai-engineering', 'rag-development', 'agentic-ai-development',
    }
    technical = role_family in technical_families and any(
        token in f"{facts_text} {job_description.casefold()}"
        for token in ('sql', 'python', 'java', 'javascript', 'software', 'database', 'programming', 'developer', 'engineer')
    )
    skill_names = (
        'Python', 'SQL', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'C', 'R',
        'Go', 'Rust', 'Ruby', 'PHP', 'Kotlin', 'Swift', 'Bash',
    )
    skills = []
    for skill in skill_names:
        token = re.escape(skill.casefold())
        trailing_boundary = r'(?![a-z0-9+#])' if skill in {'C', 'C++', 'C#'} else r'(?![a-z0-9])'
        if re.search(rf'(?<![a-z0-9]){token}{trailing_boundary}', facts_text):
            skills.append(skill)
    project_facts = [row for row in facts if row.get('fact_type') == 'project' or re.search(
        r'\b(project|capstone|coursework|portfolio)\b', row.get('fact', ''), re.I,
    )]
    jd_terms = set(re.findall(r'[a-z0-9+#.]+', job_description.casefold()))
    project_facts = sorted(
        project_facts,
        key=lambda row: -len(
            set(re.findall(r'[a-z0-9+#.]+', row.get('fact', '').casefold())) & jd_terms
        ),
    )
    # Longer sets are reserved for experienced candidates or resumes with
    # enough distinct, usable evidence to support meaningful extra coverage.
    depth = len(facts) + len({skill.casefold() for skill in skills}) * 2
    deeper_set_threshold = {'entry': 18, 'mid': 9, 'senior': 5, 'lead': 5}.get(seniority, 18)
    if target_question_count is not None and (
        isinstance(target_question_count, bool)
        or not isinstance(target_question_count, int)
        or not 30 <= target_question_count <= 60
    ):
        raise PreparationProviderError('Choose between 30 and 60 interview questions.')
    total = target_question_count if target_question_count is not None else (60 if depth >= deeper_set_threshold else 30)
    resume_coding_skills = [skill for skill in skills if skill in {
        'Python', 'SQL', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'C', 'R',
        'Go', 'Rust', 'Ruby', 'PHP', 'Kotlin', 'Swift', 'Bash',
    }]
    supported_languages = ('Python', 'SQL', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'C', 'R',
                           'Go', 'Rust', 'Ruby', 'PHP', 'Kotlin', 'Swift', 'Bash')

    def mentions_skill(text, skill):
        token = re.escape(skill.casefold())
        trailing_boundary = r'(?![a-z0-9+#])' if skill in {'C', 'C++', 'C#'} else r'(?![a-z0-9])'
        return bool(re.search(rf'(?<![a-z0-9]){token}{trailing_boundary}', str(text or '').casefold()))

    resume_language_set = {skill for skill in supported_languages if mentions_skill(facts_text, skill)}
    prioritized_requirements = sorted(
        (row for row in (requirements or []) if isinstance(row, dict)),
        key=lambda row: (not bool(row.get('mandatory')), str(row.get('requirement', '')).casefold()),
    )
    jd_languages = []
    if technical:
        for requirement in prioritized_requirements:
            text = requirement.get('requirement', '')
            for skill in supported_languages:
                if mentions_skill(text, skill) and skill not in jd_languages:
                    # Business analytics gets SQL exercises, but unrelated
                    # programming languages remain role-inappropriate there.
                    if role_family == 'business-analytics' and skill != 'SQL':
                        continue
                    jd_languages.append(skill)
    jd_missing = [skill for skill in jd_languages if skill not in resume_language_set]
    jd_supported = [skill for skill in jd_languages if skill in resume_language_set]
    can_use_resume_languages = technical and not (
        role_family == 'business-analytics' and not jd_languages and 'SQL' not in resume_language_set
    )
    coding_limit = min(15, 10 + round(5 * (total - 30) / 30))
    # JD-only skills become standardized assessment exercises. Resume-backed
    # skills may be personalized, with their RES evidence enforced downstream.
    jd_exercises = jd_missing[:min(3, coding_limit)]
    remaining_coding_slots = max(0, coding_limit - len(jd_exercises))
    resume_exercises = []
    if can_use_resume_languages:
        available_resume_skills = list(dict.fromkeys([*jd_supported, *resume_coding_skills]))
        for index in range(remaining_coding_slots):
            if available_resume_skills:
                resume_exercises.append(available_resume_skills[index % len(available_resume_skills)])
    coding_count = len(jd_exercises) + len(resume_exercises)
    gap_count = min(2, len(career_gaps or []))
    # Reserve room for role-based practice and give each selected project three
    # distinct angles. Only include projects relevant to the JD when there is a
    # relevance signal; otherwise preserve the candidate's listed order.
    project_capacity = max(0, 30 - coding_count - gap_count - 9)
    selected_projects = project_facts[:project_capacity // 3]
    project_count = len(selected_projects) * 3
    personalized_count = min(30, max(9, coding_count + project_count + gap_count))
    company_count = 1 if company_name else 0
    return {
        'total': total,
        'round_sizes': [min(30, total - start) for start in range(0, total, 30)],
        'seniority': seniority,
        'technical': technical,
        'coding_skills': resume_coding_skills,
        'jd_coding_skills': jd_exercises,
        'resume_coding_exercises': resume_exercises,
        'coding_count': coding_count,
        'project_count': project_count,
        'projects': selected_projects,
        'gap_count': gap_count,
        'company_count_per_round': company_count,
        'personalized_count': min(30, personalized_count),
        'standard_ratio': 1 - min(30, personalized_count) / 30,
    }


def _slot_exercise(question_type, question_index, round_number, plan):
    """Return the planned coding/SQL exercise for a slot, if any."""
    if round_number != 1:
        return None
    if question_type == 'standardized' and question_index < len(plan.get('jd_coding_skills', [])):
        skill = plan['jd_coding_skills'][question_index]
        return {'skill': skill, 'kind': 'sql' if skill == 'SQL' else 'coding', 'resume_supported': False}
    if question_type == 'personalized':
        tail_index = question_index - (30 - plan['personalized_count'])
        if 0 <= tail_index < len(plan.get('resume_coding_exercises', [])):
            skill = plan['resume_coding_exercises'][tail_index]
            return {'skill': skill, 'kind': 'sql' if skill == 'SQL' else 'coding', 'resume_supported': True}
    return None


def _slot_focus(question_type, question_index, round_number, plan, facts, career_gaps):
    """Provide a deterministic teaching target for each resume-led slot."""
    standard_count = plan.get('standard_count', 30 - plan['personalized_count'])
    if (
        question_type == 'standardized'
        and plan.get('company_count_per_round')
        and question_index == standard_count - 1
    ):
        return (
            'Ask one company-motivation question connecting the candidate\'s interest to this role. '
            'Use verified company research only if supplied; otherwise make no factual claims about the company.'
        )
    exercise = _slot_exercise(question_type, question_index, round_number, plan)
    if exercise:
        skill = exercise['skill']
        level_focus = {
            'entry': 'Beginner-friendly fundamentals, a small input, a clear expected result, and one simple edge case',
            'mid': 'A practical implementation or query with validation, an edge case, and a concise trade-off',
            'senior': 'A role-relevant implementation, debugging, or optimization task with complexity and reliability trade-offs',
            'lead': 'A concise implementation or code-review task emphasizing design, maintainability, and risk',
        }.get(plan.get('seniority'), 'A bounded practical task with a clear expected result')
        assessment = 'SQL query' if exercise['kind'] == 'sql' else 'programming exercise'
        experience = 'Use this as an assessment of the JD requirement; do not imply the candidate has used it.' if not exercise['resume_supported'] else 'Ground personalization in the selected resume evidence.'
        return f'Create a {skill} {assessment}. {level_focus}. Include a complete solution, example input/output, constraints, and edge cases. {experience}'
    if question_type != 'personalized':
        level_focus = {
            'entry': 'Assess a foundational concept or small practical task without assuming workplace ownership.',
            'mid': 'Assess independent delivery, debugging, validation, or trade-offs in a bounded work task.',
            'senior': 'Assess technical ownership, design decisions, reliability, or mentoring at system or team scope.',
            'lead': 'Assess cross-team strategy, architectural trade-offs, risk, and technical influence.',
        }
        return level_focus.get(plan.get('seniority'), level_focus['entry'])
    tail_index = question_index - (30 - plan['personalized_count'])
    if round_number == 1 and tail_index >= 0:
        tail_index -= len(plan.get('resume_coding_exercises', []))
        if tail_index < plan['project_count']:
            project_index = tail_index // 3
            project_angle = (
                'purpose and design', 'the candidate\'s actual contribution and technology choice',
                'a documented challenge, debugging step, or supported outcome',
            )[tail_index % 3]
            evidence = plan['projects'][project_index]
            return f"Ask about the documented project’s {project_angle}, grounded in this evidence: {evidence['fact']}"
        tail_index -= plan['project_count']
        if tail_index < min(2, len(career_gaps)):
            gap = career_gaps[tail_index]
            return f"Ask neutrally about the documented timeline gap {gap['period']}. The sample answer must not invent its reason or activities."
    return 'Ask about a specific resume skill, learning example, or transferable experience; cite the supporting resume fact.'


def _resume_evidence_for_slot(question_type, question_index, round_number, plan, category, facts, career_gaps):
    """Select the resume fact that a personalized slot is required to use."""
    if question_type != 'personalized' or not facts:
        return None

    selected = None
    tail_index = question_index - (30 - plan['personalized_count'])
    if round_number == 1 and tail_index >= 0:
        exercise = _slot_exercise(question_type, question_index, round_number, plan)
        if exercise and exercise['resume_supported']:
            skill = exercise['skill']
            selected = next((fact for fact in facts if skill and skill.casefold() in (
                str(fact.get('fact', '')) + ' ' + ' '.join(fact.get('competencies', []))
            ).casefold()), None)
        else:
            tail_index -= len(plan.get('resume_coding_exercises', []))
            if tail_index < plan['project_count']:
                project_index = tail_index // 3
                if project_index < len(plan.get('projects', [])):
                    selected = plan['projects'][project_index]
            else:
                tail_index -= plan['project_count']
                if tail_index < min(2, len(career_gaps)):
                    gap = career_gaps[tail_index]
                    gap_refs = set(gap.get('evidence_refs', []))
                    selected = next((fact for fact in facts if fact.get('id') in gap_refs), None)

    if selected is None:
        category_tokens = _question_tokens(category)
        preferred_types = (
            {'project', 'experience', 'employment_history', 'education'}
            if category.casefold() == 'projects and experience'
            else {'skill', 'project', 'experience', 'employment_history', 'education', 'certification', 'other'}
        )
        candidates = [fact for fact in facts if fact.get('fact_type') in preferred_types]
        if not candidates:
            candidates = facts
        scores = [len(category_tokens & _question_tokens(
            str(fact.get('fact', '')) + ' ' + ' '.join(fact.get('competencies', []))
        )) for fact in candidates]
        best_score = max(scores, default=0)
        best = [fact for fact, score in zip(candidates, scores) if score == best_score]
        selected = best[(question_index + round_number - 1) % len(best)] if best else None
    if not isinstance(selected, dict) or not selected.get('id'):
        return None
    return {
        'id': selected['id'],
        'fact': str(selected.get('fact', '')).strip(),
        'fact_type': selected.get('fact_type', 'other'),
    }


def _semantic_duplicate_pairs(question_rounds):
    """Return pairs of question positions that repeat an assessment objective."""
    seen = []
    duplicates = []
    for round_index, question_round in enumerate(question_rounds if isinstance(question_rounds, list) else [], start=1):
        if not isinstance(question_round, dict) or not isinstance(question_round.get('questions'), list):
            continue
        for question_index, question in enumerate(question_round['questions'], start=1):
            if not isinstance(question, dict):
                continue
            duplicate = next((
                (prior_round, prior_index) for prior_round, prior_index, prior in seen
                if _questions_are_semantic_duplicates(question, prior)
            ), None)
            if duplicate:
                duplicates.append((duplicate, (round_index, question_index)))
            seen.append((round_index, question_index, question))
    return duplicates


def _build_jd_match(requirements):
    """Create a transparent, evidence-weighted resume/JD coverage estimate."""
    weights = {'strong': 1.0, 'partial': 0.5, 'not_evidenced': 0.0}
    total_weight = matched_weight = 0
    counts = {'strong': 0, 'partial': 0, 'not_evidenced': 0}
    mapping_counts = {'mapped': 0, 'unmapped': 0}
    for requirement in requirements:
        level = requirement.get('match_level', 'not_evidenced')
        if level not in weights:
            level = 'not_evidenced'
            requirement['match_level'] = level
        is_unmapped = requirement.get('mapping_status') == 'unmapped'
        mapping_counts['unmapped' if is_unmapped else 'mapped'] += 1
        coverage_level = 'not_evidenced' if is_unmapped else level
        counts[coverage_level] += 1
        weight = 2 if requirement.get('mandatory') else 1
        total_weight += weight
        matched_weight += weight * weights[coverage_level]
    return {
        'score': round(100 * matched_weight / total_weight) if total_weight else 0,
        'total_requirements': len(requirements),
        'counts': counts,
        'mapping_counts': mapping_counts,
        'method': 'Mandatory requirements count twice; strong evidence earns full credit, partial evidence half, and requirements not shown in the resume earn none. Unmapped requirements receive no coverage credit until their role competency is mapped.',
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
        if category in row.get('mapped_categories', [row.get('category')]) and row.get('requirement')
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


def _entry_question_is_too_operational(question_text, role_family):
    """Catch entry-level questions that assume production or advanced ML ownership."""
    text = question_text.casefold()
    operational = re.search(
        r'\bproduction\b.{0,100}\b(deploy|monitor|roll.?back|incident|pipeline|drift|service level|sla)\b'
        r'|\b(deploy|monitor|roll.?back|incident|pipeline|drift|service level|sla)\b.{0,100}\bproduction\b',
        text,
    )
    hard_target = re.search(
        r'\b(refresh time|refresh duration|response time|query time)\b.{0,70}\b(under|below|within|from .{1,20} to)\b.{0,20}\d+'
        r'|\b(under|below|within)\s+\d+\s*(minutes?|seconds?)\b.{0,60}\b(refresh|performance|response|query)\b',
        text,
    )
    if operational or hard_target:
        return True
    if role_family == 'data-analytics' and re.search(
        r'\b(logistic regression|hyperparameter tuning|data drift|nan probabilities|model deployment|churn prediction model)\b',
        text,
    ):
        return True
    return False


def _batch_validation_errors(questions, expected_types, expected_categories, evidence_ids, prior_questions, seniority='entry', role_family='', expected_kinds=None, required_resume_evidence=None):
    errors = []
    if not isinstance(questions, list) or len(questions) != len(expected_types):
        return ['incorrect question count']
    seen = [q for q in prior_questions if isinstance(q, dict)]
    expected_kinds = expected_kinds or [None] * len(expected_types)
    required_resume_evidence = required_resume_evidence or [None] * len(expected_types)
    for index, (question, expected_type, expected_category, expected_kind, required_evidence) in enumerate(zip(questions, expected_types, expected_categories, expected_kinds, required_resume_evidence), start=1):
        if not isinstance(question, dict):
            errors.append(f'question {index} is not an object')
            continue
        if not str(question.get('question', '')).strip() or not str(question.get('explanation', '')).strip():
            errors.append(f'question {index} is missing question text or question explanation')
        if seniority == 'entry' and _entry_question_is_too_operational(str(question.get('question', '')), role_family):
            errors.append(f'question {index} assumes production ownership or advanced operational experience beyond fresher level')
        answer_content_errors = validate_answer_content(question.get('answer_content'))
        errors.extend(f'question {index} answer content: {error}' for error in answer_content_errors)
        question_kind = question.get('question_kind')
        if question_kind not in {'coding', 'sql', 'conceptual', 'scenario', 'behavioral'}:
            errors.append(f'question {index} has an invalid question kind')
        elif expected_kind and question_kind != expected_kind:
            errors.append(f'question {index} has the wrong kind for its assigned slot')
        elif not expected_kind and question_kind in {'coding', 'sql'}:
            errors.append(f'question {index} was not assigned a coding or SQL exercise')
        coding_solution = question.get('coding_solution')
        if not isinstance(coding_solution, str):
            errors.append(f'question {index} is missing its coding solution field')
        elif question_kind in {'coding', 'sql'} and not re.search(r'```[\w+#.-]*\s*\n[\s\S]+?\n```', coding_solution):
            errors.append(f'question {index} is missing a fenced coding solution')
        if question_kind in {'coding', 'sql'}:
            errors.extend(f'question {index} {error}' for error in coding_prompt_errors(question.get('coding_prompt')))
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
        if expected_type == 'personalized' and isinstance(required_evidence, dict):
            required_id = required_evidence.get('id')
            if not refs_valid or required_id not in refs:
                errors.append(f'question {index} does not cite its planned resume evidence')
            else:
                evidence_terms = _question_tokens(required_evidence.get('fact', '')) - {
                    'project', 'experience', 'work', 'worked', 'build', 'built', 'develop',
                    'developed', 'create', 'created', 'use', 'used', 'using', 'help', 'helped',
                    'responsibility', 'responsibilities', 'result', 'results', 'candidate',
                }
                question_terms = _question_tokens(question.get('question', ''))
                if evidence_terms and not evidence_terms.intersection(question_terms):
                    errors.append(f'question {index} does not mention a detail from its planned resume evidence')
        question_key = ' '.join(re.findall(r'[a-z0-9]+', str(question.get('question', '')).casefold()))
        seen_keys = {
            ' '.join(re.findall(r'[a-z0-9]+', str(earlier.get('question', '')).casefold()))
            for earlier in seen
        }
        if question_key and question_key in seen_keys:
            errors.append(f'question {index} repeats an exact earlier question')
        elif any(_questions_are_semantic_duplicates(question, earlier) for earlier in seen):
            errors.append(f'question {index} is semantically equivalent to an earlier question')
        if str(question.get('question', '')).strip():
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
        return (
            'A few questions were still too similar after several replacement attempts. '
            'Your completed questions are saved. Select “Resume generation” to retry the '
            'unfinished round; you can review and practise the questions already ready.'
        )
    if errors and all('evidence' in error for error in errors):
        return (
            "Your interviewer couldn't connect a few questions to the supplied experience. "
            'Questions already marked ready remain in your saved draft. Resume generation '
            'to retry the unfinished questions; your job details are still available.'
        )
    return (
        "Your interviewer couldn't validate one question group after several attempts. "
        'Questions already marked ready remain in your saved draft. Resume generation to '
        'retry the unfinished questions; your job details are still available.'
    )


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
        if not isinstance(question, dict):
            continue
        if not isinstance(question.get('coding_prompt'), dict):
            question['coding_prompt'] = {
                key: '' for key in (
                    'title', 'language', 'difficulty', 'problem_statement',
                    'function_signature', 'example_input', 'expected_output',
                    'explanation', 'constraints', 'additional_requirements',
                )
            }
        if not isinstance(question.get('evidence_refs'), list):
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
    progress_callback=None, resume_content=None, confirmed_extraction=None,
    target_question_count=None,
):
    """Analyze input and generate 30–60 validated, seniority-matched questions."""
    api_key, model, endpoint = _provider_config()
    if not api_key:
        raise PreparationProviderError('Interview preparation is not available right now.')
    provider = settings.INTERVIEW_PREP_AI_PROVIDER
    if target_question_count is None:
        target_question_count = (resume_content or {}).get('_question_target')
    if target_question_count is not None and (
        isinstance(target_question_count, bool)
        or not isinstance(target_question_count, int)
        or not 30 <= target_question_count <= 60
    ):
        raise PreparationProviderError('Choose between 30 and 60 interview questions.')
    # Older drafts may carry this legacy marker. Prefer their fallback
    # checkpoint, but never discard valid questions during continuation.
    resume_source = (resume_content or {}).get('_generation_fallback_rounds') or (resume_content or {}).get('rounds', [])
    resume_rounds = {}
    for index, row in enumerate(resume_source if isinstance(resume_source, list) else []):
        if not isinstance(row, dict) or not isinstance(row.get('questions'), list):
            continue
        try:
            round_number = int(row.get('round_number', index + 1))
        except (TypeError, ValueError):
            continue
        if round_number in {1, 2}:
            resume_rounds[round_number] = row
    resumed_questions = [
        question for question_round in resume_rounds.values()
        for question in question_round.get('questions', []) if isinstance(question, dict)
    ]
    resumed_count = count_valid_unique_questions(list(resume_rounds.values()))
    if progress_callback:
        progress_callback({'phase': 'reviewing', 'completed': resumed_count, 'total': target_question_count or 60,
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
    if confirmed_extraction:
        extracted = confirmed_extraction
        usage = {'input_tokens': 0, 'output_tokens': 0, 'elapsed_ms': 0, 'api_calls': 0}
    else:
        extracted, usage = _request_json(
            INTERVIEWER_SYSTEM_PROMPT + '\nFirst analyze role requirements and extract explicit resume facts, including transferable evidence. Identify career or education gaps of at least six months only when dates in the resume clearly support them; cite resume fact IDs containing those dates and do not infer a reason. Do not generate questions yet.',
            source_input, INPUT_ANALYSIS_SCHEMA, model, endpoint, api_key, max_tokens=2500,
        )
    try:
        facts, requirements, skill_gaps, evidence_aliases = _check_extraction(extracted)
        if not facts:
            raise PreparationProviderError('The resume did not provide usable role-related evidence.')
    except PreparationProviderError:
        if confirmed_extraction:
            raise PreparationProviderError('The confirmed resume profile could not be used. Review the profile and try again.')
        extracted, retry_usage = _request_json(
            INTERVIEWER_SYSTEM_PROMPT + '\nRepair the extraction: capture explicit experience, project, tool, education, and transferable skill facts. Do not invent facts. Identify career or education gaps only when resume dates clearly show at least six months, cite the resume facts containing those dates, and never guess the reason.',
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
    career_gaps = _clean_career_gaps(extracted, evidence_aliases, facts)
    requirements, _jd_mapping = map_jd_requirements(role_family, requirements)
    question_plan = _question_plan(
        facts, job_description, role_family, seniority, career_gaps, company_name,
        target_question_count=target_question_count, requirements=requirements,
    )
    target_total = question_plan['total']
    round_sizes = question_plan['round_sizes']
    round_count = len(round_sizes)
    jd_match = _build_jd_match(requirements)
    if progress_callback:
        progress_callback({'phase': 'questions', 'completed': resumed_count, 'total': target_total,
                           'message': 'Building question-specific practice answers…'})
    foundation_threshold = settings.INTERVIEW_PREP_FOUNDATION_MATCH_SCORE
    strong_alignment_threshold = settings.INTERVIEW_PREP_MINIMUM_JD_MATCH_SCORE
    if jd_match['score'] < foundation_threshold:
        preparation_strategy = 'Foundation-first: teach and practise role fundamentals, then build toward mandatory JD requirements not shown in the resume. Missing resume evidence does not mean the candidate lacks the skill.'
    elif jd_match['score'] < strong_alignment_threshold:
        preparation_strategy = 'Targeted: prioritize mandatory JD requirements with missing or partial resume evidence, then reinforce demonstrated skills with role scenarios.'
    else:
        preparation_strategy = 'Comprehensive: cover the role profile, mandatory and preferred JD requirements, resume examples, seniority expectations, and relevant scenarios.'
    seniority_guidance = SENIORITY_INTERVIEW_GUIDANCE.get(
        seniority, SENIORITY_INTERVIEW_GUIDANCE['entry']
    )
    if role_family == 'data-analytics':
        seniority_guidance += ' ' + DATA_ANALYTICS_LEVEL_EXAMPLES.get(seniority, '')
    preparation_strategy += f' Seniority calibration: {seniority_guidance}'
    market_sources = research.get('sources', [])
    profile_evidence = [{'id': f'ROLE-{index:02d}', 'competency': value} for index, value in enumerate(profile['competencies'], start=1)]
    market_sources = [{**source, 'id': f'MKT-{index:02d}'} for index, source in enumerate(market_sources, start=1)]
    evidence_ids = {row['id'] for row in [*facts, *requirements, *profile_evidence, *market_sources]}
    blueprint = build_competency_blueprint(
        role_family, requirements, facts,
        [source for source in market_sources if source.get('vacancy_status') == 'verified_open'],
        standard_ratio=question_plan['standard_ratio'],
        total_questions=target_total,
    )
    blueprint['seniority'] = seniority
    blueprint['question_plan'] = {
        'total_questions': target_total,
        'coding_questions': question_plan['coding_count'],
        'documented_project_questions': question_plan['project_count'],
        'career_gap_questions': min(2, len(career_gaps)),
    }
    blueprint['seniority_interview_guidance'] = seniority_guidance
    blueprint['difficulty_mix'] = {
        'entry': 'Mostly foundational, some practical application, a few stretch questions; no assumed production ownership.',
        'mid': 'Foundations plus independent task delivery, debugging, and practical trade-offs.',
        'senior': 'Advanced application, end-to-end ownership, reliability, and mentoring.',
        'lead': 'Strategic and cross-team technical decisions, organizational trade-offs, and influence.',
    }.get(seniority, 'Mostly foundational, with practical application and a few stretch questions.')
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
    filtered_resume_rounds = filter_valid_unique_question_rounds(
        list(resume_rounds.values()), allowed_categories=profile['categories'],
        valid_evidence_ids=evidence_ids,
    )
    resume_rounds = {
        int(row.get('round_number', index + 1)): row
        for index, row in enumerate(filtered_resume_rounds)
    }
    resumed_questions = [
        question for row in resume_rounds.values() for question in row.get('questions', [])
    ]
    resumed_count = count_valid_unique_questions(
        list(resume_rounds.values()), allowed_categories=profile['categories'],
        valid_evidence_ids=evidence_ids,
    )
    if progress_callback:
        progress_callback({
            'phase': 'reviewed', 'completed': resumed_count, 'total': target_total,
            'message': f'{resumed_count} valid questions are saved; continuing toward {target_total}.' if resumed_count else f'Generating your selected set of {target_total} questions.',
        })
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
    standard_ratio = question_plan['standard_ratio']
    for round_number in range(1, round_count + 1):
        round_size = round_sizes[round_number - 1]
        round_allocation = blueprint['round_allocations'][round_number - 1]
        category_sequence = round_allocation['category_sequence']
        round_questions = list(resume_rounds.get(round_number, {}).get('questions', []))
        round_standard_count = min(round_size, math.floor(round_size * standard_ratio + 0.5))
        round_plan = {
            **question_plan,
            'personalized_count': round_size - round_standard_count,
            'standard_count': round_standard_count,
        }
        if progress_callback:
            progress_callback({
                'phase': 'round_started',
                'round': round_number,
                'completed': completed_question_count,
                'total': target_total,
                'message': (
                    f'Round {round_number} of {round_count}: creating questions '
                    f'{(round_number - 1) * QUESTIONS_PER_ROUND + 1}–'
                    f'{(round_number - 1) * QUESTIONS_PER_ROUND + round_size}.'
                ),
            })
        # Keep personalized questions in their own batch so the provider schema
        # can require resume evidence IDs for every item in that batch.
        batch_specs = []
        for question_type, start, end in (
            ('standardized', 0, round_standard_count),
            ('personalized', round_standard_count, round_size),
        ):
            # Compact Markdown answers let us keep reliable batches without
            # paying for repeated strict-schema decoding retries.
            for batch_start in range(start, end, 5):
                batch_end = min(batch_start + 5, end)
                batch_specs.append((batch_start, [question_type] * (batch_end - batch_start)))
        for batch_start, batch_types in batch_specs:
            saved_prefix = max(0, len(round_questions) - batch_start)
            if saved_prefix >= len(batch_types):
                continue
            if saved_prefix:
                batch_start += saved_prefix
                batch_types = batch_types[saved_prefix:]
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
                'seniority_interview_guidance': seniority_guidance,
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
                'documented_career_gaps': career_gaps,
                'question_allocation': question_plan,
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
                'round_plan': f'Create {target_total} questions in {round_count} round(s). Keep the entry-level difficulty appropriate and do not exceed the requested question allocation.',
                'batch_start_index': batch_start,
                'question_types_in_order': batch_types,
                'question_categories_in_order': batch_categories,
                'question_slots': [
                    {
                        'question_number': batch_start + index + 1,
                        'question_type': kind,
                        'question_kind': (
                            _slot_exercise(kind, batch_start + index, round_number, round_plan) or {}
                        ).get('kind'),
                        'category': batch_categories[index],
                         'resume_evidence': _resume_evidence_for_slot(
                             kind, batch_start + index, round_number, round_plan,
                             batch_categories[index], facts, career_gaps,
                         ),
                        'coverage_target': _coverage_target(
                            batch_categories[index], batch_start + index + 1,
                            preparation_focus, profile['competencies'], rotation=round_number - 1,
                        ),
                        'assessment_angle': QUESTION_VARIATION_ANGLES[(batch_start + index + (round_number - 1) * 3) % len(QUESTION_VARIATION_ANGLES)],
                        'interview_focus': _slot_focus(
                            kind, batch_start + index, round_number, round_plan,
                            facts, career_gaps,
                        ),
                    }
                    for index, kind in enumerate(batch_types)
                ],
                'personalized_evidence_ids': [identifier for identifier in evidence_ids if identifier.startswith('RES-')],
                'allowed_categories': profile['categories'],
                'valid_evidence_ids': sorted(batch_evidence_ids),
            }
            batch, batch_usage = _request_json(
            INTERVIEWER_SYSTEM_PROMPT + '\nGenerate only the requested question batch. Follow each question_slots.interview_focus exactly. For each slot with resume_evidence, include a concrete detail from that supplied fact in the question and cite its exact ID; do not substitute another fact. Match question_type, category, assessment_angle, and coverage_target to each slot. Do not repeat a question already listed for this preparation. Every personalized question must cite resume evidence. A JD-required or preferred skill absent from the resume may be assessed as a standardized exercise, but never describe it as candidate experience. For coding or SQL slots, populate coding_prompt with title, language, difficulty, problem_statement, example_input, expected_output, and explanation; include function_signature, constraints, and additional_requirements when useful, using empty strings when unavailable. Include a complete solution in coding_solution as a fenced code block with a language label. For non-exercise questions, set coding_prompt fields and coding_solution to empty strings. Set question_kind exactly as assigned by the slot. Match difficulty to the supplied seniority. Do not invent career-gap details. Cite only valid evidence IDs.',
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
                batch_questions, batch_types, batch_categories, evidence_ids, earlier_questions,
                seniority=seniority, role_family=role_family,
                expected_kinds=[slot.get('question_kind') for slot in batch_input['question_slots']],
                required_resume_evidence=[slot.get('resume_evidence') for slot in batch_input['question_slots']],
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
                        'question_kind': (
                            _slot_exercise(batch_types[index], batch_start + index, round_number, question_plan) or {}
                        ).get('kind'),
                        'category': batch_categories[index],
                         'resume_evidence': batch_input['question_slots'][index].get('resume_evidence'),
                        'coverage_target': _coverage_target(
                            batch_categories[index], batch_start + index + 1,
                            preparation_focus, profile['competencies'], rotation=round_number + retry_number,
                        ),
                        'assessment_angle': QUESTION_VARIATION_ANGLES[(batch_start + index + (round_number - 1) * 3 + (retry_number + 1) * 4) % len(QUESTION_VARIATION_ANGLES)],
                        'interview_focus': _slot_focus(
                            batch_types[index], batch_start + index, round_number,
                            question_plan, facts, career_gaps,
                        ),
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
                    'quality_retry': 'The previous output failed these checks: ' + '; '.join(validation_errors[:10]) + '. Return exactly one replacement per question_slots entry. Follow each coverage_target and assessment_angle. Prior preparation questions are only optional variation context; overlap with another preparation is allowed. Do not repeat or semantically duplicate a question already in questions_already_in_this_preparation or duplicate_question_texts_to_replace. For every flagged overlap, choose a genuinely different skill, decision, task, or scenario from the earlier question; changing only the wording is not an alternative. Recheck every replacement against the full list of questions already prepared. Write a substantive answer at the selected seniority that directly teaches the question; do not use generic placeholders or fill-in templates. Include complete answer guidance and explanation and only valid evidence IDs.',
                    'duplicate_question_texts_to_replace': _duplicate_batch_questions(batch_questions, retry_context),
                }
                retry_schema = _question_batch_schema(batch_evidence_ids, len(invalid_indexes))
                batch, retry_usage = _request_json(
                    INTERVIEWER_SYSTEM_PROMPT + '\nGenerate only the requested replacement questions. Follow question_slots.interview_focus and assigned question_kind. Match question_type, category, assessment_angle, and coverage_target to each slot. Do not duplicate a question in the current preparation. Every personalized question must cite resume evidence. For coding or SQL slots, provide every required coding_prompt field and a complete fenced solution. For non-exercise questions, provide empty coding_prompt fields and an empty coding_solution. Do not claim that JD-only skills are candidate experience, and match difficulty to seniority. Do not invent gap explanations. Cite only valid evidence IDs.',
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
                    batch_questions, batch_types, batch_categories, evidence_ids, earlier_questions,
                    seniority=seniority, role_family=role_family,
                    expected_kinds=[slot.get('question_kind') for slot in batch_input['question_slots']],
                    required_resume_evidence=[slot.get('resume_evidence') for slot in batch_input['question_slots']],
                )
            # A provider can return a structurally weak or repetitive group even
            # after batch retries. Narrow the final recovery to one question at
            # a time; this is especially useful for the personalized tail of a
            # round, where resume evidence makes each answer more demanding.
            if validation_errors:
                invalid_indexes = _invalid_question_indexes(validation_errors, len(batch_types))
                invalid_index_set = set(invalid_indexes)
                recovery_context = earlier_questions + [
                    {
                        'question': str(batch_questions[index].get('question', ''))[:300],
                        'assessment_focus': str(batch_questions[index].get('assessment_focus', ''))[:100],
                    }
                    for index in range(len(batch_questions))
                    if index not in invalid_index_set and isinstance(batch_questions[index], dict)
                ]
                for question_index in invalid_indexes:
                    kind = batch_types[question_index]
                    category = batch_categories[question_index]
                    for recovery_attempt in range(2):
                        slot_number = batch_start + question_index + 1
                        alternative_slot = {
                            'question_number': slot_number,
                            'question_type': kind,
                            'question_kind': (
                                _slot_exercise(kind, batch_start + question_index, round_number, question_plan) or {}
                            ).get('kind'),
                            'category': category,
                             'resume_evidence': batch_input['question_slots'][question_index].get('resume_evidence'),
                            'coverage_target': _coverage_target(
                                category, slot_number,
                                preparation_focus, profile['competencies'],
                                rotation=round_number + recovery_attempt + 3,
                            ),
                            'assessment_angle': QUESTION_VARIATION_ANGLES[
                                (batch_start + question_index + (round_number - 1) * 3 + (recovery_attempt + 2) * 4)
                                % len(QUESTION_VARIATION_ANGLES)
                            ],
                            'interview_focus': _slot_focus(
                                kind, batch_start + question_index, round_number,
                                question_plan, facts, career_gaps,
                            ),
                        }
                        recovery_input = {
                            **batch_input,
                            'batch_start_index': batch_start + question_index,
                            'question_types_in_order': [kind],
                            'question_categories_in_order': [category],
                            'question_slots': [alternative_slot],
                            'questions_already_in_this_preparation': recovery_context,
                            'quality_retry': (
                                'The previous group could not pass quality checks. Generate exactly one complete replacement '
                                'for this slot. Avoid every task and decision in questions_already_in_this_preparation. '
                                'If the issue was overlap, test a genuinely different skill or scenario, not a paraphrase. '
                                'Keep the answer concise, follow the supplied experience level, cite valid evidence, and '
                                'return all required answer fields.'
                            ),
                        }
                        try:
                            replacement_batch, recovery_usage = _request_json(
                                INTERVIEWER_SYSTEM_PROMPT + '\nGenerate exactly one replacement question. Follow question_slots.question_kind and question_slots.interview_focus and match category, assessment_angle, and coverage_target. For coding or SQL, populate every required coding_prompt field and include the complete solution in a fenced code block; for other kinds use empty coding_prompt fields and coding_solution. Compare against existing questions and choose a distinct task. Do not describe a JD-only skill as candidate experience. For career gaps, do not invent personal details. Match difficulty to the supplied seniority and use only valid evidence IDs.',
                                recovery_input,
                                _question_batch_schema(batch_evidence_ids, 1),
                                model, endpoint, api_key,
                                max_tokens=2200,
                                groq_json_mode=provider == 'groq',
                            )
                        except PreparationProviderError:
                            logger.exception(
                                'Single-question recovery request failed (round=%s question=%s attempt=%s).',
                                round_number, slot_number, recovery_attempt + 1,
                            )
                            break
                        for metric in ('input_tokens', 'output_tokens', 'elapsed_ms', 'api_calls'):
                            batch_usage[metric] += recovery_usage[metric]
                        replacement_questions = replacement_batch.get('questions', [])
                        _normalize_generated_evidence_refs(replacement_questions, evidence_ids, evidence_aliases)
                        replacement = replacement_questions[0] if isinstance(replacement_questions, list) and replacement_questions else None
                        if isinstance(replacement, dict):
                            replacement['question_type'] = kind
                            replacement['category'] = category
                            replacement_errors = _batch_validation_errors(
                                [replacement], [kind], [category], evidence_ids, recovery_context,
                                seniority=seniority, role_family=role_family,
                                expected_kinds=[alternative_slot['question_kind']],
                                required_resume_evidence=[alternative_slot.get('resume_evidence')],
                            )
                            if not replacement_errors:
                                batch_questions[question_index] = replacement
                                recovery_context.append({
                                    'question': str(replacement.get('question', ''))[:300],
                                    'assessment_focus': str(replacement.get('assessment_focus', ''))[:100],
                                })
                                break
                            logger.info(
                                'Single-question recovery did not pass quality checks (round=%s question=%s attempt=%s): %s',
                                round_number, slot_number, recovery_attempt + 1, replacement_errors[:6],
                            )
                validation_errors = _batch_validation_errors(
                    batch_questions, batch_types, batch_categories, evidence_ids, earlier_questions,
                    seniority=seniority, role_family=role_family,
                    expected_kinds=[slot.get('question_kind') for slot in batch_input['question_slots']],
                    required_resume_evidence=[slot.get('resume_evidence') for slot in batch_input['question_slots']],
                )
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
            used_question_ids = {
                str(question.get('id', '')) for question in round_questions
                if isinstance(question, dict) and str(question.get('id', '')).strip()
            }
            next_question_number = 1
            for question in batch_questions:
                while f'r{round_number}-q{next_question_number:02d}' in used_question_ids:
                    next_question_number += 1
                question['id'] = f'r{round_number}-q{next_question_number:02d}'
                used_question_ids.add(question['id'])
                next_question_number += 1
            round_questions.extend(batch_questions)
            current_preparation_questions.extend(batch_questions)
            progress_round_map = {
                number: row for number, row in resume_rounds.items() if number != round_number
            }
            progress_round_map.update({
                int(row.get('round_number', index + 1)): row
                for index, row in enumerate(rounds)
                if int(row.get('round_number', index + 1)) != round_number
            })
            progress_round_map[round_number] = {
                'round_number': round_number,
                'questions': round_questions,
            }
            progress_rounds = list(progress_round_map.values())
            completed_question_count = count_valid_unique_questions(progress_rounds)
            if progress_callback:
                progress_callback({
                    'phase': 'questions',
                    'completed': completed_question_count,
                    'total': target_total,
                    'round': round_number,
                    'message': (
                        f'Round {round_number}: {len(round_questions)} of {round_size} ready '
                        f'({completed_question_count} of {target_total} overall).'
                    ),
                    'preview_questions': [str(question.get('question', '')) for question in batch_questions],
                    'validated_questions': batch_questions,
                    'round_questions': list(round_questions),
                    'round_number': round_number,
                })
        rounds.append({'round_number': round_number, 'title': f'Practice round {round_number}', 'questions': round_questions})
        if progress_callback:
            progress_callback({
                'phase': 'round_complete',
                'round': round_number,
                'completed': completed_question_count,
                'total': target_total,
                'message': (
                    f'Round {round_number} is ready with {len(round_questions)} questions. '
                    + (f'Starting round {round_number + 1} now.' if round_number < round_count else 'Your preparation is ready; finishing the quality review.')
                ),
            })
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
        'career_gaps': career_gaps,
        'rounds': rounds,
        '_question_target': target_total,
        '_generation_state': 'complete',
        '_generation_progress': {'completed': completed_question_count, 'total': target_total},
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
    semantic_duplicates = _semantic_duplicate_pairs(rounds)
    if semantic_duplicates:
        duplicate_errors = [
            f'question {current[1]} is semantically equivalent to question {prior[1]} in round {prior[0]}'
            for prior, current in semantic_duplicates
        ]
        logger.warning('Final question set contains unresolved semantic duplicates: %s', duplicate_errors[:10])
        raise PreparationProviderError(_quality_failure_message(duplicate_errors))
    errors = validate_intelligence_output(
        result, profile['categories'], evidence_ids,
        standard_ratio=question_plan['standard_ratio'],
        target_count=target_total,
    )
    if errors:
        raise PreparationProviderError(
            'Your interviewer could not complete the final quality check. Please try again.'
        )
    return result
