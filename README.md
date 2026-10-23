# TechPhile.ai

TechPhile.ai is a Django web application for learning technical skills, practising coding and exams, and preparing for job interviews. Its main goal is to give learners one place to study role-related material, check their understanding, practise realistic problems, and track progress over time.

The project includes public website pages, account management, timed mock exams, coding exercises, structured career learning paths, and a role-aware AI interview-preparation workflow.

## What learners can do

- Create and manage an account, verify an email address, reset a password, and update profile settings.
- Take timed mock exams, review results, bookmark questions, and track performance.
- Practise coding problems, submit code for execution through Judge0, and review scores and progress.
- Explore AI and software topics, work through learning problems and datasets, and track submissions.
- Follow career paths with day-by-day lessons, scenario questions, recommendations, and milestone assessments.
- Prepare for an interview using a job description and resume evidence. The interview workflow maps requirements to role competencies, creates question plans, validates question quality, and saves progress so an interrupted draft can be resumed.
- Use REST API endpoints for supported application features.

## Technology and skills

### Backend

- **Python 3.12** and **Django 4.2** for application logic, routing, forms, templates, authentication, and persistence.
- **Django REST Framework** for APIs; SimpleJWT and DRF token authentication are installed for API authentication.
- **MySQL** with `mysqlclient` as the configured database backend.
- Django ORM and migrations for relational data; JSON fields are used for structured interview-preparation output and learning content.
- **Pandas, NumPy, OpenCV, Pillow, and OpenPyXL** support data, image, spreadsheet, and learning exercises.
- **Requests** is used for external HTTP integrations, including configured AI providers and Judge0.

### Frontend

- Django-rendered HTML templates power the pages and forms.
- CSS and JavaScript provide layout, styling, and interactive behavior.
- The shared site uses Bootstrap, jQuery, Owl Carousel, and Font Awesome assets (including CDN-loaded assets where configured).
- Static styles, scripts, images, and fonts are under `static/` and app-specific static directories.

This repository does not use a separate React/Vite frontend build. React and related tools appear among the technical learning and interview topics.

### Technical learning topics

The supplied learning and question material covers Python, Java, C/C++, JavaScript, HTML/CSS, SQL, Git, data structures and algorithms, object-oriented programming, React, NumPy, Pandas, data analytics, data science, machine learning, deep learning, computer vision, and generative AI. Topic availability depends on the data loaded into the database.

## Application areas

| URL | Django app | Purpose |
| --- | --- | --- |
| `/` | `tech` | Public home, about, services, and contact pages |
| `/accounts/` | `accounts` | Registration, login, logout, email verification, and password recovery |
| `/exams/` | `exams` | Mock exams, results, profiles/settings, analytics, and human mock-interview features |
| `/coding/` | `coding` | Coding problem pages, submissions, Judge0 execution, dashboard, and leaderboard |
| `/explore_courses` | `core` | Technical topics, problems, datasets, progress, and leaderboard |
| `/careers/` | `careers` | Role-based learning paths, daily lessons and questions, recommendations, and milestones |
| `/interview-prep/` | `interview_prep` | Premium interview preparation, saved question sets, practice, and payment review |
| `/api/` | `api` | Additional REST API endpoints |
| `/admin/` | Django admin | Administrative data and configuration |

The root URL configuration is in `techphile_exams/urls.py`; app URL patterns live in each app's `urls.py`.

## Interview-preparation workflow

The interview-preparation feature accepts a job description and resume information after consent. It extracts resume facts and job requirements, maps requirements to canonical competencies, plans the selected 30-, 45-, or 60-question target, then generates and validates questions in saved batches. The workflow supports technical and role-specific questions, scenarios, coding/SQL exercises, projects, and evidence-based personalized questions. Questions and draft checkpoints are stored with the preparation; original resume text is not saved by the generation flow.

Generation uses the configured OpenAI or Groq Responses API provider. It is intentionally incremental: each validated batch is checkpointed so a provider or validation failure does not discard questions already saved. The learner can resume an unfinished draft. Current market research is optional and disabled by default. Paid access is governed by the server-side monthly plan settings and administrator payment review; development-only test access is separate.

Implementation landmarks:

- `interview_prep/openai_generator.py` — extraction, competency planning, provider calls, generation, and validation.
- `interview_prep/blueprint.py` — role competency mapping and question allocation.
- `interview_prep/intelligence_schema.py` — structured data and question validation.
- `interview_prep/role_profiles.py` — role families, categories, competencies, and seniority expectations.
- `interview_prep/candidate_profile.py` — candidate profile extraction and confirmation helpers.
- `interview_prep/services.py` — access checks, draft checkpoints, and preparation persistence.
- `interview_prep/views.py`, `forms.py`, and `urls.py` — web request handling and forms.
- `interview_prep/prompts.py` — stable interviewer instructions.
- `interview_prep/templates/interview_prep/` and `static/css/interview-prep.css` — interview-preparation pages and styling.
- `interview_prep/tests.py` and `test_intelligence.py` — application and generation/intelligence tests.

More feature-specific configuration notes are in [`interview_prep/README.md`](interview_prep/README.md).

## Repository guide

```text
manage.py                       Django command-line entry point
requirements.txt                Python dependencies
techphile_exams/                Project settings, root URLs, ASGI and WSGI
accounts/                       Account forms, views, models, templates and tests
exams/                          Exams, questions, attempts, profiles and interview features
coding/                         Coding problems, submissions and execution integration
core/                           Topic learning, datasets, exercises and learner progress
careers/                        Career paths, lessons, recommendations and milestones
interview_prep/                 AI interview preparation and premium-access workflow
api/                            Additional API views, serializers and models
tech/                           Public website pages and contact functionality
management/                     Project management commands
explore_courses/                Course/topic data population scripts
tech_coding_questions/          Sample coding-question population scripts
tech_bits/                      Spreadsheet question banks for technical topics
datasets/                       Exercise datasets and related assets (when present)
templates/                      Shared site and registration templates
static/                         Shared CSS, JavaScript, images and fonts
media/                          User-uploaded files at runtime
```

Most Django apps use the standard Django layout: `models.py` for data models, `views.py` for request handling, `urls.py` for routes, `forms.py` for forms, `serializers.py` for API representations, `admin.py` for administration, `templates/` and `static/` for UI assets, and `migrations/` for schema history. Some apps omit files they do not need.

Important project files:

- `techphile_exams/settings.py` — installed apps, database, templates, static files, email, integrations, and feature settings.
- `techphile_exams/urls.py` — root route table.
- `techphile_exams/wsgi.py` and `asgi.py` — deployment entry points.
- `.env.example` — names and local defaults for environment configuration; copy it to `.env` and set local values.
- `populate_*.py`, `populate_all.py`, and app management commands — optional content-loading utilities. Review a script before running it because it can write to the configured database.

## Run locally

### Requirements

- Python 3.12 (the project dependencies target the Django 4.2 series).
- MySQL available locally, unless you deliberately configure a separate test/development settings module.
- A Judge0 API key for remote coding execution.
- An OpenAI or Groq API key to generate AI interview questions.

### Windows PowerShell setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with local database credentials and any provider credentials you intend to use. Create the configured MySQL database (the sample database name is `Tech`) before running migrations:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. To load optional course content, review the relevant `populate_*.py` script or management command first, then run only the content loader you need.

### Environment configuration

`settings.py` reads configuration from environment variables and `.env` through `python-decouple`. Main settings include:

- `SECRET_KEY`, `DEBUG`, and database values `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
- `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` for SMTP account email.
- `JUDGE0_API_KEY` for remote code execution.
- `INTERVIEW_PREP_AI_PROVIDER` (`openai` or `groq`), the corresponding provider API key, and model name for AI question generation.
- `INTERVIEW_PREP_MARKET_RESEARCH_PROVIDER`, which defaults to `none`.
- `INTERVIEW_PREP_PAYMENTS_ENABLED` and merchant/payment settings. Keep payments disabled until the merchant details and payment-verification process are configured.
- `FEATURE_CODING` and `FEATURE_MOCK_INTERVIEWS` control navigation visibility; hiding a navigation entry does not remove its route.

Never commit `.env`, API keys, database passwords, or private user data. Set `DEBUG=False` and configure an appropriate secret key, allowed hosts, HTTPS, email, static files, and production database before deployment. The sample `ALLOWED_HOSTS` in settings is for local development.

## Tests and checks

Run targeted Django tests for the area you change. Common commands are:

```powershell
python manage.py check
python manage.py test accounts
python manage.py test interview_prep.tests interview_prep.test_intelligence
python manage.py test careers
```

The project test runner uses the configured database settings and may create a test database. Confirm the active settings and database permissions before running tests against a local MySQL setup. Do not point destructive test or seed operations at data you need to preserve.

## Notes

- Admin customizations are configured through `techphile_exams/admin_site.py` and the Django admin app configuration.
- Uploaded media and collected static files are runtime/deployment concerns; `media/` and `staticfiles/` may be generated locally.
- AI output and external code execution depend on provider availability, configuration, rate limits, and network access.
- This README describes the repository structure and configured features. Some routes or integrations may require credentials, database content, feature flags, or approved paid access before they are usable.
