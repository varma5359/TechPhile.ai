"""Versioned, configurable interview profiles for TechPhile career paths."""

PROFILE_VERSION = '1.1'

SENIORITY_LEVELS = {
    'entry': {'label': 'Entry level / fresher', 'years': '0–2', 'expectation': 'Foundational concepts, learning ability, and clear reasoning.'},
    'mid': {'label': 'Mid level', 'years': '3–5', 'expectation': 'Independent delivery, trade-offs, and reliable execution.'},
    'senior': {'label': 'Senior', 'years': '6–9', 'expectation': 'System ownership, technical direction, and mentoring.'},
    'lead': {'label': 'Lead / principal', 'years': '10+', 'expectation': 'Organization-level decisions, strategy, and cross-team influence.'},
}
SENIORITY_EXPECTATIONS = {key: value['expectation'] for key, value in SENIORITY_LEVELS.items()}

# Describe the scope and independence an interviewer should expect at each
# level so a complex job description cannot silently set candidate seniority.
SENIORITY_INTERVIEW_GUIDANCE = {
    'entry': (
        'Interview for a fresher or candidate with up to two years of experience. '
        'Assess foundations, clear reasoning, coachability, and small practical tasks. '
        'Assume the candidate may only have coursework, self-study, internships, or '
        'personal projects; invite those examples and allow a simple hypothetical when '
        'they have no work example. Use familiar, bounded datasets and ask one decision '
        'at a time. Most questions should be foundational, some should apply a concept '
        'to a realistic small task, and only a few should stretch the candidate. '
        'Do not expect production ownership, architecture, deployment, monitoring, '
        'large-scale optimization, strict service targets, or advanced incident response. '
        'If the JD mentions these, test awareness or basic concepts only, without expecting '
        'the candidate to have operated them.'
    ),
    'mid': (
        'Interview for roughly three to five years of experience. Assess independent '
        'delivery of bounded features, practical debugging, validation, trade-offs, and '
        'collaboration. Use realistic team scenarios, but do not assume organization-wide '
        'ownership or principal-level architecture.'
    ),
    'senior': (
        'Interview for roughly six to nine years of experience. Assess end-to-end '
        'ownership, design decisions, reliability, operational trade-offs, mentoring, '
        'and how the candidate handles ambiguity across a system or team.'
    ),
    'lead': (
        'Interview for a lead or principal candidate with ten or more years of experience. '
        'Assess technical strategy, architecture across teams, organizational trade-offs, '
        'risk management, influence, and developing other engineers.'
    ),
}

DATA_ANALYTICS_LEVEL_EXAMPLES = {
    'entry': (
        'For a fresher Data Analyst, prefer SELECT/WHERE/GROUP BY and a simple join on '
        'small tables; spotting a missing or duplicate value; explaining mean versus '
        'median; reading a simple chart; checking a basic KPI definition; and describing '
        'a class, internship, or personal project. Avoid requiring predictive-model '
        'operations or production data-pipeline experience.'
    ),
    'mid': (
        'For a mid-level Data Analyst, include independent analysis tasks such as using '
        'CTEs or window functions where relevant, reconciling a metric, validating a '
        'dashboard change, interpreting an experiment, and explaining trade-offs to a '
        'stakeholder.'
    ),
    'senior': (
        'For a senior Data Analyst, include ambiguous metric definitions, analytical '
        'design choices, data-quality safeguards, stakeholder alignment, review of '
        'others’ analysis, and ownership of reliable reporting.'
    ),
    'lead': (
        'For a lead/principal Data Analyst, include measurement strategy, metric '
        'governance, cross-team data priorities, investment trade-offs, and growing '
        'analytical capability across teams.'
    ),
}

COMMON_CATEGORIES = ['Role fundamentals', 'Problem solving', 'Projects and experience', 'Communication and collaboration']

ROLE_PROFILES = {
    'data-analytics': {
        'label': 'Data Analytics', 'aliases': ['data analyst', 'analytics engineer'],
        'competencies': ['SQL and data modelling', 'data quality', 'statistical reasoning', 'visualisation', 'business communication'],
        'categories': COMMON_CATEGORIES + ['SQL and data modelling', 'Statistics and experimentation', 'Data visualisation'],
    },
    'business-analytics': {
        'label': 'Business Analytics', 'aliases': ['business analyst', 'business intelligence analyst'],
        'competencies': ['requirements analysis', 'metrics and KPIs', 'SQL', 'dashboards', 'stakeholder communication'],
        'categories': COMMON_CATEGORIES + ['Requirements and metrics', 'SQL and reporting', 'Stakeholder scenarios'],
    },
    'machine-learning-engineering': {
        'label': 'Machine Learning Engineering', 'aliases': ['machine learning engineer', 'ml engineer'],
        'competencies': ['model evaluation', 'feature engineering', 'deployment', 'monitoring', 'data pipelines'],
        'categories': COMMON_CATEGORIES + ['Machine learning fundamentals', 'Model evaluation', 'Production systems'],
    },
    'computer-vision-engineering': {
        'label': 'Computer Vision Engineering', 'aliases': ['computer vision engineer', 'vision engineer'],
        'competencies': ['image processing', 'deep learning', 'dataset quality', 'model evaluation', 'deployment'],
        'categories': COMMON_CATEGORIES + ['Computer vision', 'Model evaluation', 'Production systems'],
    },
    'generative-ai-engineering': {
        'label': 'Generative AI Engineering', 'aliases': ['generative ai engineer', 'llm engineer'],
        'competencies': ['LLM application design', 'prompt and output evaluation', 'retrieval', 'safety', 'deployment'],
        'categories': COMMON_CATEGORIES + ['LLM systems', 'Evaluation and safety', 'Production systems'],
    },
    'rag-development': {
        'label': 'RAG Development', 'aliases': ['rag engineer', 'retrieval augmented generation engineer'],
        'competencies': ['document ingestion', 'chunking and retrieval', 'ranking', 'grounding and citations', 'evaluation'],
        'categories': COMMON_CATEGORIES + ['Retrieval design', 'Grounding and evaluation', 'Production systems'],
    },
    'agentic-ai-development': {
        'label': 'Agentic AI Development', 'aliases': ['agentic ai engineer', 'ai agent developer'],
        'competencies': ['tool orchestration', 'state and memory', 'evaluation', 'permissions and safety', 'reliability'],
        'categories': COMMON_CATEGORIES + ['Agent architecture', 'Tool use and safety', 'Reliability and evaluation'],
    },
    'general-software-engineering': {
        'label': 'General Software Engineering', 'aliases': ['software engineer', 'software developer', 'backend developer'],
        'competencies': ['programming fundamentals', 'API and system design', 'testing', 'debugging', 'collaboration'],
        'categories': COMMON_CATEGORIES + ['Programming and APIs', 'System design', 'Testing and reliability'],
    },
}


def get_role_profile(profile_key):
    """Return a profile by key, falling back to general software engineering."""
    profile = ROLE_PROFILES.get(profile_key, ROLE_PROFILES['general-software-engineering']).copy()
    profile['seniority_expectation'] = SENIORITY_EXPECTATIONS
    return profile


def profile_choices():
    return [(key, profile['label']) for key, profile in ROLE_PROFILES.items()]
