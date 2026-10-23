"""Deterministic allocation of role, JD, resume, and research evidence."""

import math
import re

from .role_profiles import PROFILE_VERSION, get_role_profile


# Each profile competency has one explicit canonical assessment category.
# Text aliases below map common JD wording to those canonical competencies.
_COMPETENCY_CATEGORIES = {
    'data-analytics': {
        'SQL and data modelling': 'SQL and data modelling',
        'data quality': 'Role fundamentals',
        'statistical reasoning': 'Statistics and experimentation',
        'visualisation': 'Data visualisation',
        'business communication': 'Communication and collaboration',
    },
    'business-analytics': {
        'requirements analysis': 'Requirements and metrics',
        'metrics and KPIs': 'Requirements and metrics',
        'SQL': 'SQL and reporting',
        'dashboards': 'SQL and reporting',
        'stakeholder communication': 'Stakeholder scenarios',
    },
    'machine-learning-engineering': {
        'model evaluation': 'Model evaluation',
        'feature engineering': 'Machine learning fundamentals',
        'deployment': 'Production systems',
        'monitoring': 'Production systems',
        'data pipelines': 'Production systems',
    },
    'computer-vision-engineering': {
        'image processing': 'Computer vision',
        'deep learning': 'Computer vision',
        'dataset quality': 'Computer vision',
        'model evaluation': 'Model evaluation',
        'deployment': 'Production systems',
    },
    'generative-ai-engineering': {
        'LLM application design': 'LLM systems',
        'prompt and output evaluation': 'Evaluation and safety',
        'retrieval': 'LLM systems',
        'safety': 'Evaluation and safety',
        'deployment': 'Production systems',
    },
    'rag-development': {
        'document ingestion': 'Retrieval design',
        'chunking and retrieval': 'Retrieval design',
        'ranking': 'Retrieval design',
        'grounding and citations': 'Grounding and evaluation',
        'evaluation': 'Grounding and evaluation',
    },
    'agentic-ai-development': {
        'tool orchestration': 'Agent architecture',
        'state and memory': 'Agent architecture',
        'evaluation': 'Reliability and evaluation',
        'permissions and safety': 'Tool use and safety',
        'reliability': 'Reliability and evaluation',
    },
    'general-software-engineering': {
        'programming fundamentals': 'Programming and APIs',
        'API and system design': 'System design',
        'testing': 'Testing and reliability',
        'debugging': 'Testing and reliability',
        'collaboration': 'Communication and collaboration',
    },
}

_COMPETENCY_ALIASES = {
    'SQL and data modelling': ('sql', 'query', 'queries', 'relational database', 'data model', 'schema design', 'table joins'),
    'data quality': ('data quality', 'data validation', 'data integrity', 'missing records', 'duplicate records', 'data accuracy', 'data freshness'),
    'statistical reasoning': ('statistics', 'statistical analysis', 'hypothesis testing', 'experiment design', 'confidence interval', 'significance testing'),
    'visualisation': ('visualization', 'visualisation', 'dashboard', 'chart', 'data storytelling', 'reporting visuals'),
    'business communication': ('business communication', 'explain findings', 'present findings', 'business stakeholders'),
    'requirements analysis': ('requirements', 'business needs', 'acceptance criteria', 'functional specification'),
    'metrics and KPIs': ('metrics', 'kpi', 'key performance indicator', 'success measure', 'measurement definition'),
    'SQL': ('sql', 'query', 'relational database', 'table joins'),
    'dashboards': ('dashboard', 'reporting dashboard', 'business intelligence report'),
    'stakeholder communication': ('stakeholder communication', 'stakeholder alignment', 'present findings', 'customer needs'),
    'model evaluation': ('model evaluation', 'model performance', 'precision', 'recall', 'classification metrics', 'evaluation metric'),
    'feature engineering': ('feature engineering', 'feature selection', 'input features', 'feature transformation'),
    'deployment': ('deployment', 'deploy a service', 'release a model', 'production rollout'),
    'monitoring': ('monitoring', 'model drift', 'service observability', 'production metrics'),
    'data pipelines': ('data pipeline', 'etl', 'data ingestion', 'batch processing', 'stream processing'),
    'image processing': ('image processing', 'image segmentation', 'image enhancement', 'computer vision'),
    'deep learning': ('deep learning', 'neural network', 'convolutional network', 'cnn'),
    'dataset quality': ('dataset quality', 'label quality', 'annotation quality', 'class imbalance', 'training data quality'),
    'LLM application design': ('llm application', 'large language model', 'generative ai application', 'language model integration'),
    'prompt and output evaluation': ('prompt evaluation', 'prompt testing', 'output evaluation', 'response quality'),
    'retrieval': ('retrieval', 'semantic search', 'vector search', 'document search'),
    'safety': ('safety', 'guardrails', 'prompt injection', 'unsafe output'),
    'document ingestion': ('document ingestion', 'document parsing', 'file ingestion', 'document processing'),
    'chunking and retrieval': ('chunking', 'text segmentation', 'retrieval pipeline', 'document retrieval'),
    'ranking': ('ranking', 'reranking', 'search relevance', 'result ordering'),
    'grounding and citations': ('grounding', 'citations', 'source attribution', 'evidence attribution'),
    'tool orchestration': ('tool orchestration', 'tool calling', 'function calling', 'workflow orchestration'),
    'state and memory': ('agent memory', 'conversation memory', 'state management', 'session state'),
    'permissions and safety': ('permissions', 'authorization', 'access control', 'safety policy'),
    'reliability': ('reliability', 'fault tolerance', 'retry behavior', 'failure recovery'),
    'programming fundamentals': ('programming', 'data structures', 'algorithms', 'object oriented programming', 'coding fundamentals', 'python', 'java', 'javascript', 'typescript', 'c plus plus', 'c sharp'),
    'API and system design': ('api', 'endpoint', 'rest api', 'http service', 'api design', 'system design', 'service architecture', 'backend architecture'),
    'testing': ('testing', 'unit test', 'integration test', 'test coverage', 'automated tests'),
    'debugging': ('debugging', 'troubleshooting', 'root cause analysis', 'diagnose a defect'),
    'collaboration': ('collaboration', 'code review', 'teamwork', 'cross functional work'),
}


def _tokens(value):
    """Normalize phrases to whole words so short substrings cannot match."""
    tokens = re.findall(r'[a-z0-9]+', str(value or '').casefold())
    normalized = []
    for token in tokens:
        if token.endswith('ies') and len(token) > 5:
            token = token[:-3] + 'y'
        elif token.endswith('s') and not token.endswith(('ss', 'us', 'is')) and len(token) > 4:
            token = token[:-1]
        normalized.append(token)
    return normalized


def _phrase_present(text_tokens, phrase_tokens):
    if not phrase_tokens or len(phrase_tokens) > len(text_tokens):
        return False
    width = len(phrase_tokens)
    return any(text_tokens[index:index + width] == phrase_tokens for index in range(len(text_tokens) - width + 1))


def map_jd_requirements(role_family, requirements):
    """Attach canonical competencies/categories without guessing a category.

    A valid supplied category is retained when no competency phrase matches.
    An invalid or absent category is explicitly routed to the profile's
    general fundamentals category and marked ``unmapped`` for review.
    """
    profile = get_role_profile(role_family)
    categories = set(profile['categories'])
    category_by_competency = _COMPETENCY_CATEGORIES.get(
        role_family, _COMPETENCY_CATEGORIES['general-software-engineering'],
    )
    mapped = []
    diagnostics = {'mapped': 0, 'category_only': 0, 'unmapped': []}
    fallback_category = 'Role fundamentals' if 'Role fundamentals' in categories else None

    for original in requirements:
        if not isinstance(original, dict):
            continue
        row = dict(original)
        source_category = row.get('source_category', row.get('category', ''))
        text_tokens = _tokens(row.get('requirement', ''))
        matched_competencies = []
        for competency in profile['competencies']:
            phrases = (competency, *_COMPETENCY_ALIASES.get(competency, ()))
            if any(_phrase_present(text_tokens, _tokens(phrase)) for phrase in phrases):
                matched_competencies.append(competency)

        matched_categories = list(dict.fromkeys(
            category_by_competency[competency]
            for competency in matched_competencies
            if category_by_competency.get(competency) in categories
        ))
        if matched_categories:
            row['category'] = matched_categories[0]
            row['mapped_categories'] = matched_categories
            row['mapped_competencies'] = matched_competencies
            row['mapping_status'] = 'competency'
            diagnostics['mapped'] += 1
        elif source_category in categories:
            row['category'] = source_category
            row['mapped_categories'] = [source_category]
            row['mapped_competencies'] = []
            row['mapping_status'] = 'category'
            diagnostics['category_only'] += 1
        else:
            row['category'] = fallback_category
            row['mapped_categories'] = [fallback_category] if fallback_category else []
            row['mapped_competencies'] = []
            row['mapping_status'] = 'unmapped'
            diagnostics['unmapped'].append(row.get('id'))
        row['source_category'] = source_category
        mapped.append(row)
    return mapped, diagnostics


def allocate_question_counts(profile, total, evidence_by_category=None):
    categories = profile['categories']
    if not categories or total <= 0:
        return {category: 0 for category in categories}
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


def _category_sequence(categories, counts):
    sequence = []
    remaining = dict(counts)
    while any(remaining.values()):
        for category in categories:
            if remaining.get(category, 0):
                sequence.append(category)
                remaining[category] -= 1
    return sequence


def build_competency_blueprint(role_family, requirements, resume_facts, market_sources, standard_ratio=0.70, total_questions=30):
    profile = get_role_profile(role_family)
    requirements, mapping_diagnostics = map_jd_requirements(role_family, requirements)
    supported = {category: [] for category in profile['categories']}
    for requirement in requirements:
        if not requirement.get('mandatory'):
            continue
        for category in requirement.get('mapped_categories', []):
            if category in supported:
                supported[category].append(requirement.get('id'))

    round_sizes = [min(30, total_questions - start) for start in range(0, total_questions, 30)]
    round_allocations = []
    for round_size in round_sizes:
        category_counts = allocate_question_counts(profile, round_size, supported)
        standard_count = math.floor(round_size * standard_ratio + 0.5)
        round_allocations.append({
            'total': round_size,
            'standardized': standard_count,
            'personalized': round_size - standard_count,
            'category_counts': category_counts,
            'category_sequence': _category_sequence(profile['categories'], category_counts),
        })

    first_round = round_allocations[0] if round_allocations else {
        'total': 0, 'standardized': 0, 'personalized': 0,
        'category_counts': {category: 0 for category in profile['categories']},
        'category_sequence': [],
    }
    return {
        'role_family': role_family,
        'profile_version': PROFILE_VERSION,
        'competencies': profile['competencies'],
        'assessment_categories': profile['categories'],
        'seniority_expectation': profile['seniority_expectation'],
        'per_round': {key: value for key, value in first_round.items()},
        'round_allocations': round_allocations,
        'total_questions': total_questions,
        'jd_requirement_mapping': mapping_diagnostics,
        'source_counts': {
            'jd_requirements': len(requirements),
            'resume_facts': len(resume_facts),
            'verified_market_sources': sum(1 for source in market_sources if source.get('vacancy_status') == 'verified_open'),
        },
    }
