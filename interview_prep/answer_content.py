"""Validation and backward-compatible normalization for rich answer content."""

BLOCK_TYPES = {'paragraph', 'steps', 'bullets', 'flow', 'example', 'table', 'code', 'callout'}
CODE_LANGUAGES = {'sql', 'python', 'text', 'bash', 'json'}


def _is_text(value, allow_blank=False):
    return isinstance(value, str) and (allow_blank or bool(value.strip()))


def _validate_block(block):
    errors = []
    if not isinstance(block, dict):
        return ['content block must be an object']
    kind = block.get('type')
    if not isinstance(kind, str) or kind not in BLOCK_TYPES:
        return ['content block has an unsupported type']
    if not _is_text(block.get('title'), allow_blank=True):
        errors.append('content block title must be text')
    if not _is_text(block.get('text'), allow_blank=True):
        errors.append('content block text must be text')
    if not isinstance(block.get('items'), list) or any(not _is_text(item) for item in block.get('items', [])):
        errors.append('content block items must be a list of non-empty strings')
    if not isinstance(block.get('headers'), list) or any(not _is_text(item) for item in block.get('headers', [])):
        errors.append('content block headers must be a list of non-empty strings')
    if not isinstance(block.get('rows'), list):
        errors.append('content block rows must be a list')
    else:
        for row in block['rows']:
            if not isinstance(row, list) or any(not _is_text(cell, allow_blank=True) for cell in row):
                errors.append('table rows must contain text cells')
                break
    if not _is_text(block.get('code'), allow_blank=True):
        errors.append('content block code must be text')
    if not isinstance(block.get('language'), str) or block.get('language') not in CODE_LANGUAGES:
        errors.append('content block language is unsupported')
    if kind in {'paragraph', 'example', 'callout'} and not str(block.get('text', '')).strip():
        errors.append(f'{kind} block needs text')
    elif kind in {'steps', 'bullets', 'flow'} and not block.get('items'):
        errors.append(f'{kind} block needs at least one item')
    elif kind == 'table':
        headers = block.get('headers')
        rows = block.get('rows')
        if not isinstance(headers, list) or len(headers) < 2:
            errors.append('table needs at least two column headings')
        if not isinstance(rows, list) or not rows:
            errors.append('table needs at least one data row')
        elif isinstance(headers, list) and any(not isinstance(row, list) or len(row) != len(headers) for row in rows):
            errors.append('table rows must match the number of column headings')
    elif kind == 'code':
        if not str(block.get('code', '')).strip():
            errors.append('code block needs code')
    return errors


def validate_answer_content(content):
    """Return validation errors for the structured answer contract."""
    if not isinstance(content, dict):
        return ['answer content must be an object']
    errors = []
    for field in ('direct_answer', 'interview_ready_answer'):
        if not _is_text(content.get(field)):
            errors.append(f'{field.replace("_", " ")} is required')
    sections = content.get('sections')
    if not isinstance(sections, list):
        errors.append('sections must be a list')
    else:
        for section_index, section in enumerate(sections, start=1):
            if not isinstance(section, dict):
                errors.append(f'section {section_index} must be an object')
                continue
            if not _is_text(section.get('title')):
                errors.append(f'section {section_index} needs a title')
            if 'markdown' in section:
                if not _is_text(section.get('markdown')):
                    errors.append(f'section {section_index} Markdown content must be text')
                continue
            blocks = section.get('blocks')
            if not isinstance(blocks, list):
                errors.append(f'section {section_index} blocks must be a list')
                continue
            for block_index, block in enumerate(blocks, start=1):
                errors.extend(
                    f'section {section_index}, block {block_index}: {error}'
                    for error in _validate_block(block)
                )
    evaluation = content.get('interviewer_evaluation')
    if not isinstance(evaluation, dict):
        errors.append('interviewer evaluation must be an object')
    else:
        checks = evaluation.get('what_interviewer_checks')
        if not isinstance(checks, list) or any(not _is_text(item) for item in checks):
            errors.append('interviewer checks must be a list of non-empty strings')
        for field in ('common_mistake', 'key_takeaway'):
            if not _is_text(evaluation.get(field), allow_blank=True):
                errors.append(f'interviewer evaluation {field.replace("_", " ")} must be text')
    if not _is_text(content.get('practice_activity'), allow_blank=True):
        errors.append('practice activity must be text')
    return errors


def _normalized_block(block):
    if _validate_block(block):
        return None
    return {
        'type': block['type'],
        'title': block.get('title', ''),
        'text': block.get('text', ''),
        'items': block.get('items', []),
        'headers': block.get('headers', []),
        'rows': block.get('rows', []),
        'code': block.get('code', ''),
        'language': block.get('language', 'text'),
    }


def normalize_answer_content(content):
    """Keep valid optional blocks and ignore malformed ones for resilient reads."""
    if not isinstance(content, dict):
        return None
    direct_answer = content.get('direct_answer')
    interview_answer = content.get('interview_ready_answer')
    if not _is_text(direct_answer) or not _is_text(interview_answer):
        return None

    sections = []
    raw_sections = content.get('sections')
    if isinstance(raw_sections, list):
        for section in raw_sections:
            if not isinstance(section, dict) or not _is_text(section.get('title')):
                continue
            markdown_content = section.get('markdown')
            if _is_text(markdown_content):
                sections.append({'title': section['title'], 'markdown': markdown_content, 'blocks': []})
                continue
            raw_blocks = section.get('blocks')
            if not isinstance(raw_blocks, list):
                continue
            blocks = [normalized for block in raw_blocks if (normalized := _normalized_block(block))]
            if blocks:
                sections.append({'title': section['title'], 'markdown': '', 'blocks': blocks})

    raw_evaluation = content.get('interviewer_evaluation')
    if not isinstance(raw_evaluation, dict):
        raw_evaluation = {}
    checks = raw_evaluation.get('what_interviewer_checks')
    if not isinstance(checks, list):
        checks = []
    evaluation = {
        'what_interviewer_checks': [item for item in checks if _is_text(item)],
        'common_mistake': raw_evaluation.get('common_mistake') if _is_text(raw_evaluation.get('common_mistake')) else '',
        'key_takeaway': raw_evaluation.get('key_takeaway') if _is_text(raw_evaluation.get('key_takeaway')) else '',
    }
    practice_activity = content.get('practice_activity')
    return {
        'direct_answer': direct_answer,
        'sections': sections,
        'interview_ready_answer': interview_answer,
        'interviewer_evaluation': evaluation,
        'practice_activity': practice_activity if _is_text(practice_activity) else '',
    }


def answer_content_texts(content):
    """Collect human-readable generated text for quality checks."""
    normalized = normalize_answer_content(content)
    if not normalized:
        return []
    values = [normalized['direct_answer'], normalized['interview_ready_answer']]
    values.append(normalized['practice_activity'])
    evaluation = normalized['interviewer_evaluation']
    values.extend(evaluation['what_interviewer_checks'])
    values.extend([evaluation['common_mistake'], evaluation['key_takeaway']])
    for section in normalized['sections']:
        values.append(section['title'])
        values.append(section['markdown'])
        for block in section['blocks']:
            values.extend([block['title'], block['text'], block['code']])
            values.extend(block['items'])
            values.extend(block['headers'])
            values.extend(cell for row in block['rows'] for cell in row)
    return [value for value in values if value]
