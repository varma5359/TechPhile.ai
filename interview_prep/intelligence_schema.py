"""Versioned output contract and deterministic validation for generated prep."""

import math
import re

PIPELINE_VERSION = '1.4'
PROMPT_VERSION = '1.5'
OUTPUT_SCHEMA_VERSION = '1.1'
QUESTIONS_PER_ROUND = 30
ROUND_COUNT = 2
STANDARD_RATIO = 0.70


def normalize_question(text):
    return re.sub(r'[^a-z0-9]+', ' ', (text or '').casefold()).strip()


def validate_intelligence_output(result, allowed_categories, valid_evidence_ids, standard_ratio=STANDARD_RATIO):
    """Validate both complete rounds and assign stable IDs from their order."""
    errors = []
    if not isinstance(result, dict):
        return ['Output must be an object.']
    if not isinstance(result.get('analysis'), str) or not result['analysis'].strip():
        errors.append('A role-fit analysis is required.')
    rounds = result.get('rounds')
    if not isinstance(rounds, list) or len(rounds) != ROUND_COUNT:
        return errors + ['Exactly two question rounds are required.']

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
    expected_standard = math.floor(QUESTIONS_PER_ROUND * standard_ratio + 0.5)
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
        if not isinstance(questions, list) or len(questions) != QUESTIONS_PER_ROUND:
            errors.append(f'Round {round_index} must contain exactly {QUESTIONS_PER_ROUND} questions.')
            continue
        standard_count = 0
        for question_index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                errors.append(f'Round {round_index}, question {question_index} must be an object.')
                continue
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
            for field in ('answer_guidance', 'explanation'):
                if not isinstance(question.get(field), str) or not question[field].strip():
                    errors.append(f'Round {round_index}, question {question_index} needs {field.replace("_", " ")}.')
            refs = question.get('evidence_refs')
            if not isinstance(refs, list) or not refs or not set(refs).issubset(allowed_evidence):
                errors.append(f'Round {round_index}, question {question_index} has invalid evidence references.')
            elif kind == 'personalized' and not any(ref.startswith('RES-') for ref in refs):
                errors.append(f'Round {round_index}, question {question_index} is personalized without resume evidence.')
            question['id'] = f'r{round_index}-q{question_index:02d}'
        if standard_count != expected_standard:
            errors.append(f'Round {round_index} must have {expected_standard} standardized questions and {QUESTIONS_PER_ROUND - expected_standard} personalized questions.')
    return errors
