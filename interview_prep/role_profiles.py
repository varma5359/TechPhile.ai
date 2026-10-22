"""Versioned, configurable interview profiles for TechPhile career paths."""

PROFILE_VERSION = '1.0'

SENIORITY_LEVELS = {
    'entry': {'label': 'Entry level / fresher', 'years': '0–2', 'expectation': 'Foundational concepts, learning ability, and clear reasoning.'},
    'mid': {'label': 'Mid level', 'years': '3–5', 'expectation': 'Independent delivery, trade-offs, and reliable execution.'},
    'senior': {'label': 'Senior', 'years': '6–9', 'expectation': 'System ownership, technical direction, and mentoring.'},
    'lead': {'label': 'Lead / principal', 'years': '10+', 'expectation': 'Organization-level decisions, strategy, and cross-team influence.'},
}
SENIORITY_EXPECTATIONS = {key: value['expectation'] for key, value in SENIORITY_LEVELS.items()}

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
