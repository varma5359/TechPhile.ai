"""Deterministic allocation of role, JD, resume, and research evidence."""

import math

from .role_profiles import get_role_profile


def allocate_question_counts(profile, total, evidence_by_category=None):
    categories = profile['categories']
    base, remainder = divmod(total, len(categories))
    counts = {category: base for category in categories}
    for category in categories[:remainder]:
        counts[category] += 1
    evidence_by_category = evidence_by_category or {}
    # Give categories directly supported by mandatory requirements one extra
    # slot by transferring from the least-supported category, without changing
    # the total. The stable tie-break keeps output repeatable.
    for category in categories:
        if evidence_by_category.get(category) and counts[category] < total:
            donor = min(categories, key=lambda name: (len(evidence_by_category.get(name, [])), -counts[name], name))
            if donor != category and counts[donor] > 1:
                counts[donor] -= 1
                counts[category] += 1
    return counts


def build_competency_blueprint(role_family, requirements, resume_facts, market_sources, standard_ratio=0.70):
    profile = get_role_profile(role_family)
    supported = {category: [] for category in profile['categories']}
    for requirement in requirements:
        text = requirement.get('requirement', '').casefold()
        for competency in profile['competencies']:
            if any(token in text for token in competency.casefold().split() if len(token) > 2 and token not in {'and', 'for', 'the'}):
                category = next((item for item in profile['categories'] if item.casefold() in competency.casefold()), profile['categories'][0])
                supported[category].append(requirement.get('id'))
                break
    category_counts = allocate_question_counts(profile, 30, supported)
    standard_count = int(math.floor(30 * standard_ratio + 0.5))
    return {
        'role_family': role_family,
        'profile_version': '1.0',
        'competencies': profile['competencies'],
        'assessment_categories': profile['categories'],
        'seniority_expectation': profile['seniority_expectation'],
        'per_round': {
            'total': 30,
            'standardized': standard_count,
            'personalized': 30 - standard_count,
            'category_counts': category_counts,
        },
        'source_counts': {
            'jd_requirements': len(requirements),
            'resume_facts': len(resume_facts),
            'verified_market_sources': sum(1 for source in market_sources if source.get('vacancy_status') == 'verified_open'),
        },
    }
