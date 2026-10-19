"""Non-destructive proposals for converting legacy structured lessons.

This module deliberately has no Django imports and performs no persistence.
Callers must review ``conflicts`` and ``unmapped_content`` before applying any
of ``safe_fields``. The complete source payload is always returned unchanged.
"""

from copy import deepcopy


_SECTION_KEYS = {'heading', 'paragraphs', 'steps', 'bullets', 'table', 'callouts'}
_TABLE_KEYS = {'headers', 'rows'}
_CALLOUT_KEYS = {'kind', 'text'}
_SCENARIO_KEYS = {'title', 'body', 'prompt'}
_REVISION_KEYS = {'core', 'takeaways', 'rule'}


def _has_content(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _markdown_cell(value):
    return value.replace('|', r'\|').replace('\r\n', '\n').replace('\n', '<br>')


def _convert_sections(sections):
    """Convert the documented legacy section schema to standard Markdown."""
    if not isinstance(sections, list):
        raise ValueError('sections must be a list')

    rendered = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict) or set(section) - _SECTION_KEYS:
            raise ValueError(f'section {index} has an unsupported shape')

        heading = section.get('heading', '')
        if not isinstance(heading, str):
            raise ValueError(f'section {index} heading must be text')
        if heading:
            rendered.append(f'## {heading}')

        for key in ('paragraphs', 'steps', 'bullets'):
            values = section.get(key, [])
            if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
                raise ValueError(f'section {index} {key} must be a list of text')
            if key == 'paragraphs':
                rendered.extend(item for item in values if item)
            elif key == 'steps':
                if values:
                    rendered.append('\n'.join(
                        f'{number}. {item}' for number, item in enumerate(values, 1)))
            else:
                if values:
                    rendered.append('\n'.join(f'- {item}' for item in values))

        table = section.get('table')
        if table is not None:
            if (not isinstance(table, dict) or set(table) - _TABLE_KEYS
                    or not isinstance(table.get('headers'), list)
                    or not isinstance(table.get('rows'), list)):
                raise ValueError(f'section {index} table has an unsupported shape')
            headers, rows = table['headers'], table['rows']
            if not headers or any(not isinstance(cell, str) for cell in headers):
                raise ValueError(f'section {index} table headers must be nonempty text cells')
            if any(not isinstance(row, list) or len(row) != len(headers)
                   or any(not isinstance(cell, str) for cell in row) for row in rows):
                raise ValueError(f'section {index} table rows do not match its headers')
            table_lines = [
                '| ' + ' | '.join(map(_markdown_cell, headers)) + ' |',
                '| ' + ' | '.join('---' for _ in headers) + ' |',
            ]
            table_lines.extend('| ' + ' | '.join(map(_markdown_cell, row)) + ' |' for row in rows)
            rendered.append('\n'.join(table_lines))

        callouts = section.get('callouts', [])
        if not isinstance(callouts, list):
            raise ValueError(f'section {index} callouts must be a list')
        for callout in callouts:
            if (not isinstance(callout, dict) or set(callout) - _CALLOUT_KEYS
                    or not isinstance(callout.get('kind'), str)
                    or not isinstance(callout.get('text'), str)
                    or callout['kind'] not in {'tip', 'note', 'warning', 'example'}):
                raise ValueError(f'section {index} has an unsupported callout')
            rendered.append(f"!!! {callout['kind']}\n    {callout['text']}")

    return '\n\n'.join(part for part in rendered if part)


def _convert_scenario(value):
    if isinstance(value, str):
        return value
    if not isinstance(value, dict) or set(value) - _SCENARIO_KEYS:
        raise ValueError('scenario has an unsupported shape')
    if any(not isinstance(item, str) for item in value.values()):
        raise ValueError('scenario values must be text')

    parts = []
    if value.get('title'):
        parts.append(f"### {value['title']}")
    if value.get('body'):
        parts.append(value['body'])
    if value.get('prompt'):
        parts.append(f"> {value['prompt']}")
    return '\n\n'.join(parts)


def _convert_revision(value):
    if isinstance(value, str):
        return value
    if not isinstance(value, dict) or set(value) - _REVISION_KEYS:
        raise ValueError('revision has an unsupported shape')
    if any(not isinstance(item, (str, list)) for item in value.values()):
        raise ValueError('revision values have an unsupported type')
    core, takeaways, rule = value.get('core', ''), value.get('takeaways', []), value.get('rule', '')
    if not isinstance(core, str) or not isinstance(rule, str) or not isinstance(takeaways, list):
        raise ValueError('revision core/rule must be text and takeaways must be a list')
    if any(not isinstance(item, str) for item in takeaways):
        raise ValueError('revision takeaways must contain only text')

    parts = []
    if core:
        parts.append(f'**Most important idea:** {core}')
    if takeaways:
        parts.append('\n'.join(f'- {item}' for item in takeaways))
    if rule:
        parts.append(f'**Rule:** {rule}')
    return '\n\n'.join(parts)


def propose_lesson_conversion(payload, existing_fields=None):
    """Return a non-mutating conversion proposal and a complete review report.

    ``safe_fields`` contains candidates whose destinations are blank or
    null-like. ``proposed_fields`` also includes conflicting candidates so a
    reviewer can compare them; it must not be applied without resolving the
    corresponding conflict. Unknown keys and unsupported structures are kept
    in ``unmapped_content`` and the exact source is independently copied to
    ``source_payload``.
    """
    existing = deepcopy(existing_fields or {})
    source = deepcopy(payload)
    proposed = {}
    safe = {}
    conflicts = []
    unmapped = {}
    unmapped_reasons = {}

    def retain_unmapped(key, value, reason):
        unmapped[key] = deepcopy(value)
        unmapped_reasons[key] = reason

    if payload is None:
        return {
            'source_payload': source,
            'proposed_fields': proposed,
            'safe_fields': safe,
            'conflicts': conflicts,
            'unmapped_content': unmapped,
            'unmapped_reasons': unmapped_reasons,
        }
    if not isinstance(payload, dict):
        retain_unmapped('$payload', payload, 'The source payload must be a JSON object.')
        return {
            'source_payload': source,
            'proposed_fields': proposed,
            'safe_fields': safe,
            'conflicts': conflicts,
            'unmapped_content': unmapped,
            'unmapped_reasons': unmapped_reasons,
        }

    def offer(source_key, target, candidate):
        if not _has_content(candidate):
            return
        proposed[target] = candidate
        if _has_content(existing.get(target)):
            conflicts.append({
                'source_key': source_key,
                'target_field': target,
                'existing_value': deepcopy(existing[target]),
                'proposed_value': deepcopy(candidate),
            })
        else:
            safe[target] = candidate

    for key, target in (('intro', 'lesson_intro'),):
        if key in payload:
            value = payload[key]
            if isinstance(value, str):
                offer(key, target, value)
            elif value is not None:
                retain_unmapped(key, value, 'Expected text for the lesson intro.')

    for key, target, converter in (
        ('scenario', 'lesson_scenario', _convert_scenario),
        ('revision', 'lesson_revision', _convert_revision),
    ):
        if key not in payload:
            continue
        value = payload[key]
        if not _has_content(value):
            continue
        try:
            offer(key, target, converter(value))
        except ValueError as error:
            retain_unmapped(key, value, str(error))

    if 'objectives' in payload:
        value = payload['objectives']
        if isinstance(value, str):
            candidate = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            candidate = '\n'.join(value)
        elif value is None or value == []:
            candidate = ''
        else:
            candidate = None
            retain_unmapped('objectives', value,
                            'Objectives must be text or a list containing only text.')
        if candidate:
            offer('objectives', 'objectives', candidate)

    for key, target, valid in (
        ('minutes', 'estimated_minutes', lambda value: isinstance(value, int) and not isinstance(value, bool) and value > 0),
        ('level', 'difficulty_level', lambda value: isinstance(value, str)),
    ):
        if key not in payload:
            continue
        value = payload[key]
        if value is None or value == '':
            continue
        if valid(value):
            offer(key, target, value)
        else:
            retain_unmapped(key, value, f'Value is invalid for {target}.')

    if 'sections' in payload and _has_content(payload['sections']):
        try:
            candidate = _convert_sections(payload['sections'])
        except ValueError as error:
            retain_unmapped('sections', payload['sections'], str(error))
        else:
            offer('sections', 'lesson_body', candidate)

    # Historical diagrams and worked examples have structured presentation
    # semantics with no one-to-one current fields. Retain them for review.
    for key in ('diagrams', 'example'):
        if key in payload and _has_content(payload[key]):
            retain_unmapped(
                key, payload[key],
                'The current lesson-body format has no reviewed representation for this structure.',
            )

    recognized = {
        'intro', 'scenario', 'revision', 'objectives', 'minutes', 'level',
        'sections', 'diagrams', 'example',
    }
    for key in payload:
        if key not in recognized:
            retain_unmapped(key, payload[key], 'Unknown top-level key; retained unchanged.')

    return {
        'source_payload': source,
        'proposed_fields': proposed,
        'safe_fields': safe,
        'conflicts': conflicts,
        'unmapped_content': unmapped,
        'unmapped_reasons': unmapped_reasons,
    }
