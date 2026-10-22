# Interview intelligence

The interview preparation pipeline is separate from manual payment review. An
approved monthly access period is still required to generate and save a paid
preparation; local test access remains development-only.

## Role-aware preparation

The configurable role profiles cover the current career paths: Business and
Data Analytics, Machine Learning Engineering, Computer Vision Engineering,
Generative AI Engineering, RAG Development, Agentic AI Development, and a
general software fallback. Each profile defines competencies, assessment
categories, and expectations across four seniority levels. Profile, prompt,
schema, and pipeline versions are saved with each completed result.

The stable interviewer instructions are in `prompts.py`. Candidate and job
details are passed separately as dynamic input. The generator first extracts
resume facts and job requirements, then creates a competency blueprint and two
distinct rounds of 30 questions. Each round uses the configured standardized
and personalized ratio, initially 70/30. One two-round preparation counts as
one of the two monthly preparation submissions.

Each batch has a bounded retry. Output is checked for count, category, evidence
references, answer guidance, duplicate text, and stable IDs before persistence.
An incomplete generation does not create a preparation set. Completed output
is reused for a learner with an identical input fingerprint in the same access
period. Resume text is sent only after explicit consent and is not persisted;
the fingerprint is a one-way SHA-256 digest. Generated questions and the
submitted job description are retained with the learner's preparation.

Provider token usage is recorded to help measure generation cost. Exact dollar
cost estimates are not made unless model pricing is configured and kept current.
The pipeline uses OpenAI or Groq Responses API configuration from `.env`.

## Current job-market research

Research is optional and no provider is enabled by default. With
`INTERVIEW_PREP_MARKET_RESEARCH_PROVIDER=none`, the saved result says that
current vacancy research was not performed. It never implies the model knew
current vacancies. A registered provider must return dated HTTPS source records;
records without official-employer evidence cannot be marked verified open.
Results are cached for `INTERVIEW_PREP_MARKET_RESEARCH_CACHE_HOURS`. No paid
search service is included or enabled.

## Key settings

- `INTERVIEW_PREP_AI_PROVIDER`: `openai` or `groq`.
- `INTERVIEW_PREP_OPENAI_API_KEY` / `INTERVIEW_PREP_GROQ_API_KEY`: selected-provider key.
- Provider-specific model settings: `INTERVIEW_PREP_OPENAI_MODEL` and
  `INTERVIEW_PREP_GROQ_MODEL`.
- `INTERVIEW_PREP_STANDARD_QUESTION_RATIO`: configured role-based share; the
  remainder is personalized.
- `INTERVIEW_PREP_MARKET_RESEARCH_PROVIDER`: `none` unless an approved adapter
  is installed and configured.

Payments remain closed unless the verified merchant details, QR asset, selected
AI provider, and `INTERVIEW_PREP_PAYMENTS_ENABLED=True` are all ready. Never
commit `.env` or a provider key. Coding and human Mock Interview features are
independent and unchanged.
