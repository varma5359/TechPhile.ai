"""Versioned output contract and deterministic validation for generated prep."""

import math
import re

from .answer_content import validate_answer_content

PIPELINE_VERSION = '1.9'
PROMPT_VERSION = '2.4'
OUTPUT_SCHEMA_VERSION = '1.7'
QUESTIONS_PER_ROUND = 30
ROUND_COUNT = 2  # Maximum; a preparation can contain one or two rounds.
STANDARD_RATIO = 0.70
CODING_PROMPT_REQUIRED = (
    'title', 'language', 'difficulty', 'problem_statement',
    'example_input', 'expected_output', 'explanation',
)


def coding_prompt_errors(prompt):
    """Validate the minimum structured prompt required for a coding/SQL task."""
    if not isinstance(prompt, dict):
        return ['structured coding prompt must be an object']
    errors = []
    for field in CODING_PROMPT_REQUIRED:
        if not isinstance(prompt.get(field), str) or not prompt[field].strip():
            errors.append(f'coding prompt needs {field.replace("_", " ")}')
    for field in ('function_signature', 'constraints', 'additional_requirements'):
        if field in prompt and not isinstance(prompt[field], str):
            errors.append(f'coding prompt {field.replace("_", " ")} must be text')
    return errors


def normalize_question(text):
    return re.sub(r'[^a-z0-9]+', ' ', str(text or '').casefold()).strip()


def count_valid_unique_questions(question_rounds, allowed_categories=None, valid_evidence_ids=None, require_coding_contract=False):
    """Count complete, unique questions using the server-side output contract."""
    if not isinstance(question_rounds, list):
        return 0
    allowed_categories = set(allowed_categories) if allowed_categories is not None else None
    valid_evidence_ids = set(valid_evidence_ids) if valid_evidence_ids is not None else None
    seen = set()
    count = 0
    for question_round in question_rounds:
        if not isinstance(question_round, dict) or not isinstance(question_round.get('questions'), list):
            continue
        for question in question_round['questions']:
            if not isinstance(question, dict):
                continue
            text = question.get('question')
            if not isinstance(text, str):
                continue
            normalized = normalize_question(text)
            if not normalized or normalized in seen:
                continue
            if allowed_categories is not None and question.get('category') not in allowed_categories:
                continue
            question_type = question.get('question_type')
            if question_type not in {'standardized', 'personalized'} and (require_coding_contract or question_type is not None):
                continue
            if 'answer_content' in question:
                if validate_answer_content(question.get('answer_content')):
                    continue
            elif not isinstance(question.get('answer_guidance'), str) or not question['answer_guidance'].strip():
                continue
            if not isinstance(question.get('explanation'), str) or not question['explanation'].strip():
                continue
            refs = question.get('evidence_refs')
            if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) for ref in refs):
                continue
            if valid_evidence_ids is not None and not set(refs).issubset(valid_evidence_ids):
                continue
            if question_type == 'personalized' and not any(
                isinstance(ref, str) and ref.startswith('RES-') for ref in refs
            ):
                continue
            question_kind = question.get('question_kind')
            if question_kind is None and not require_coding_contract:
                question_kind = 'scenario'
            if question_kind not in {'coding', 'sql', 'conceptual', 'scenario', 'behavioral'}:
                continue
            solution = question.get('coding_solution')
            if solution is None and not require_coding_contract:
                solution = ''
            if not isinstance(solution, str):
                continue
            if question_kind in {'coding', 'sql'} and not re.search(r'```[\w+#.-]*\s*\n[\s\S]+?\n```', solution):
                continue
            coding_prompt = question.get('coding_prompt')
            if coding_prompt is not None and (
                question_kind in {'coding', 'sql'}
                or (isinstance(coding_prompt, dict) and any(str(value).strip() for value in coding_prompt.values()))
            ) and coding_prompt_errors(coding_prompt):
                continue
            seen.add(normalized)
            count += 1
    return count


def filter_valid_unique_question_rounds(question_rounds, allowed_categories=None, valid_evidence_ids=None):
    """Return only complete unique questions while retaining their saved IDs."""
    if not isinstance(question_rounds, list):
        return []
    filtered = []
    seen = set()
    for round_row in question_rounds:
        if not isinstance(round_row, dict) or not isinstance(round_row.get('questions'), list):
            continue
        questions = []
        for original in round_row['questions']:
            if not isinstance(original, dict):
                continue
            if count_valid_unique_questions(
                [{'questions': [original]}],
                allowed_categories=allowed_categories,
                valid_evidence_ids=valid_evidence_ids,
            ) != 1:
                continue
            key = normalize_question(original.get('question'))
            if not key or key in seen:
                continue
            question = dict(original)
            if question.get('question_kind') is None:
                question['question_kind'] = 'scenario'
            if question.get('coding_solution') is None:
                question['coding_solution'] = ''
            if question.get('question_type') not in {'standardized', 'personalized'}:
                question['question_type'] = (
                    'personalized'
                    if any(str(ref).startswith('RES-') for ref in question.get('evidence_refs', []))
                    else 'standardized'
                )
            questions.append(question)
            seen.add(key)
        filtered.append({**round_row, 'questions': questions})
    return filtered


def validate_intelligence_output(result, allowed_categories, valid_evidence_ids, standard_ratio=STANDARD_RATIO, target_count=None):
    """Validate a 30- or 60-question set and assign stable IDs."""
    errors = []
    if not isinstance(result, dict):
        return ['Output must be an object.']
    if not isinstance(result.get('analysis'), str) or not result['analysis'].strip():
        errors.append('A role-fit analysis is required.')
    structured_coding_required = (
        isinstance(result.get('versions'), dict)
        and result['versions'].get('schema') == OUTPUT_SCHEMA_VERSION
    )
    rounds = result.get('rounds')
    if not isinstance(rounds, list) or len(rounds) not in {1, 2}:
        return errors + ['A preparation must contain one or two question rounds.']

    gaps = result.get('skill_gaps')
    if not isinstance(gaps, list):
        errors.append('Skill gaps must be a list.')
    else:
        for gap in gaps:
            if not isinstance(gap, dict) or not isinstance(gap.get('gap'), str) or not gap['gap'].strip():
                errors.append('Every skill gap needs a description.')
            elif not isinstance(gap.get('evidence_refs'), list) or not gap['evidence_refs'] or not set(gap['evidence_refs']).issubset(set(valid_evidence_ids)):
                errors.append('Every skill gap needs valid source references.')

    seen_text = set()
    seen_round_numbers = set()
    allowed_evidence = set(valid_evidence_ids)
    total_questions = 0
    for round_index, question_round in enumerate(rounds, start=1):
        if not isinstance(question_round, dict):
            errors.append(f'Round {round_index} must be an object.')
            continue
        if question_round.get('round_number') != round_index:
            errors.append(f'Round {round_index} has an invalid round number.')
        title = question_round.get('title')
        if not isinstance(title, str) or not title.strip():
            errors.append(f'Round {round_index} needs a title.')
        if title in seen_round_numbers:
            errors.append('Round titles must be unique.')
        seen_round_numbers.add(title)
        questions = question_round.get('questions')
        if not isinstance(questions, list) or not 1 <= len(questions) <= QUESTIONS_PER_ROUND:
            errors.append(f'Round {round_index} must contain between 1 and {QUESTIONS_PER_ROUND} questions.')
            continue
        total_questions += len(questions)
        expected_standard = math.floor(len(questions) * standard_ratio + 0.5)
        standard_count = 0
        for question_index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                errors.append(f'Round {round_index}, question {question_index} must be an object.')
                continue
            question_kind = question.get('question_kind')
            if question_kind is not None and question_kind not in {'coding', 'sql', 'conceptual', 'scenario', 'behavioral'}:
                errors.append(f'Round {round_index}, question {question_index} has an invalid question kind.')
            solution = question.get('coding_solution')
            if solution is not None and not isinstance(solution, str):
                errors.append(f'Round {round_index}, question {question_index} needs a coding solution field.')
            elif question_kind in {'coding', 'sql'} and not re.search(r'```[\w+#.-]*\s*\n[\s\S]+?\n```', solution or ''):
                errors.append(f'Round {round_index}, question {question_index} needs a fenced coding solution.')
            coding_prompt = question.get('coding_prompt')
            if structured_coding_required and question_kind in {'coding', 'sql'} and coding_prompt is None:
                errors.append(f'Round {round_index}, question {question_index} needs a structured coding prompt.')
            if coding_prompt is not None and (
                question_kind in {'coding', 'sql'}
                or (isinstance(coding_prompt, dict) and any(str(value).strip() for value in coding_prompt.values()))
            ):
                errors.extend(
                    f'Round {round_index}, question {question_index}: {error}.'
                    for error in coding_prompt_errors(coding_prompt)
                )
            text = question.get('question')
            normalized = normalize_question(text)
            if not normalized:
                errors.append(f'Round {round_index}, question {question_index} has no question text.')
            elif normalized in seen_text:
                errors.append('Question text must be unique across both rounds.')
            seen_text.add(normalized)
            if question.get('category') not in allowed_categories:
                errors.append(f'Round {round_index}, question {question_index} has an invalid category.')
            kind = question.get('question_type')
            if kind not in {'standardized', 'personalized'}:
                errors.append(f'Round {round_index}, question {question_index} has an invalid question type.')
            if kind == 'standardized':
                standard_count += 1
            if 'answer_content' in question:
                errors.extend(
                    f'Round {round_index}, question {question_index}: {error}.'
                    for error in validate_answer_content(question.get('answer_content'))
                )
            elif not isinstance(question.get('answer_guidance'), str) or not question['answer_guidance'].strip():
                errors.append(f'Round {round_index}, question {question_index} needs an answer.')
            if not isinstance(question.get('explanation'), str) or not question['explanation'].strip():
                errors.append(f'Round {round_index}, question {question_index} needs an explanation.')
            refs = question.get('evidence_refs')
            if not isinstance(refs, list) or not refs or not set(refs).issubset(allowed_evidence):
                errors.append(f'Round {round_index}, question {question_index} has invalid evidence references.')
            elif kind == 'personalized' and not any(ref.startswith('RES-') for ref in refs):
                errors.append(f'Round {round_index}, question {question_index} is personalized without resume evidence.')
            if not str(question.get('id', '')).strip():
                question['id'] = f'r{round_index}-q{question_index:02d}'
        if standard_count != expected_standard:
            errors.append(f'Round {round_index} must have {expected_standard} standardized questions and {QUESTIONS_PER_ROUND - expected_standard} personalized questions.')
    valid_unique_count = count_valid_unique_questions(
        rounds, allowed_categories=allowed_categories, valid_evidence_ids=valid_evidence_ids,
    )
    if not 30 <= total_questions <= 60 or valid_unique_count != total_questions:
        errors.append('A preparation must contain between 30 and 60 questions.')
    if target_count is not None and valid_unique_count != target_count:
        errors.append(f'A preparation must contain exactly {target_count} valid questions.')
    return errors
