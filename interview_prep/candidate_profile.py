"""Candidate profile review data kept with an interview preparation draft."""

PROFILE_SECTIONS = (
    ('skills', 'Skills'),
    ('education', 'Education'),
    ('projects', 'Projects'),
    ('experience', 'Experience and responsibilities'),
    ('employment_history', 'Employment and dates'),
    ('certifications', 'Certifications'),
    ('other_details', 'Other resume details'),
)
MAX_PROFILE_ITEMS = 30
MAX_PROFILE_ITEM_LENGTH = 500


def profile_to_resume_text(profile):
    """Create concise generation input from candidate-confirmed profile facts."""
    if not isinstance(profile, dict):
        return ''
    sections = []
    for key, label in PROFILE_SECTIONS:
        rows = profile.get(key, [])
        values = [
            str(row.get('text', '')).strip()
            for row in rows
            if isinstance(row, dict) and str(row.get('text', '')).strip()
        ] if isinstance(rows, list) else []
        if values:
            sections.append(f'{label}:\n' + '\n'.join(f'- {value}' for value in values))
    return '\n\n'.join(sections)


def confirm_profile_edits(profile, submitted):
    """Validate edited profile sections and preserve stable IDs for source facts."""
    if not isinstance(profile, dict) or not isinstance(profile.get('extraction'), dict):
        raise ValueError('The saved resume profile is unavailable. Please submit the resume again.')
    updated = {**profile}
    extraction = {**profile['extraction']}
    old_rows = [row for row in extraction.get('resume_facts', []) if isinstance(row, dict)]
    old_by_id = {row.get('id'): row for row in old_rows}
    next_facts = []
    for key, _label in PROFILE_SECTIONS:
        raw = submitted.get(f'profile_{key}', '')
        values = [line.strip() for line in str(raw).splitlines() if line.strip()]
        if len(values) > MAX_PROFILE_ITEMS:
            raise ValueError(f'Keep each profile section to {MAX_PROFILE_ITEMS} items or fewer.')
        if any(len(value) > MAX_PROFILE_ITEM_LENGTH for value in values):
            raise ValueError(f'Keep each profile detail to {MAX_PROFILE_ITEM_LENGTH} characters or fewer.')
        existing = [row for row in profile.get(key, []) if isinstance(row, dict)]
        section_rows = []
        for index, value in enumerate(values):
            old = existing[index] if index < len(existing) else None
            old_id = old.get('id') if old else None
            if old_id in old_by_id:
                fact = {**old_by_id[old_id], 'fact': value}
            else:
                fact_type = {
                    'skills': 'skill',
                    'projects': 'project',
                    'employment_history': 'employment_history',
                    'certifications': 'certification',
                    'other_details': 'other',
                }.get(key, key)
                fact = {
                    'id': f'candidate-{key}-{index + 1}',
                    'fact': value,
                    'fact_type': fact_type,
                    'competencies': [key.replace('_', ' ')],
                }
            next_facts.append(fact)
            section_rows.append({'id': fact['id'], 'text': value})
        updated[key] = section_rows
    if not next_facts:
        raise ValueError('Keep at least one resume detail so your preparation can be personalized.')
    if len(next_facts) > MAX_PROFILE_ITEMS:
        raise ValueError(f'Keep your confirmed profile to {MAX_PROFILE_ITEMS} details or fewer.')

    extraction['resume_facts'] = next_facts
    current_ids = {row['id'] for row in next_facts}
    for requirement in extraction.get('jd_requirements', []):
        if not isinstance(requirement, dict):
            continue
        refs = [ref for ref in requirement.get('resume_fact_refs', []) if ref in current_ids]
        requirement['resume_fact_refs'] = refs
        if not refs:
            requirement['match_level'] = 'not_evidenced'
            requirement['match_rationale'] = 'No supporting example was selected in the confirmed profile.'
    for gap in extraction.get('skill_gaps', []):
        if isinstance(gap, dict):
            gap['resume_fact_refs'] = [ref for ref in gap.get('resume_fact_refs', []) if ref in current_ids]
    updated['extraction'] = extraction
    return updated
