# TechPhile Exams

TechPhile.ai is a Django-based learning and assessment platform. It combines **mock exams**, **mock interviews**, an **online coding practice judge**, and **AI/ML course exploration** with datasets, plus a REST API for each major feature.

## Features

| Area | What it provides |
|------|------------------|
| **Accounts** | Sign-up with email verification, login/logout (safe `next` redirect, "remember me"), password reset, terms of service and privacy policy pages |
| **Mock exams** (`exams`) | Categories, exams with levels/sets, multiple question types, timed attempts, results with per-type performance, bookmarks, retakes, study guide, sample questions, user analytics |
| **Mock interviews** (`exams`) | Schedule, edit, cancel, reschedule and join interviews; interviewer dashboard; interviewer assignment (admin); post-interview feedback |
| **User settings** (`exams`) | Profile, photo, password change, notifications, preferences, session management |
| **Coding practice** (`coding`) | Problem list and detail pages, in-browser code editor, code submission and execution API, solutions, personal dashboard, leaderboard |
| **Explore courses** (`core`) | Topics (AI, ML, DL, NLP, CV, GenAI, NumPy, Pandas, ...), practice problems, submissions, progress tracking, leaderboard, downloadable datasets |
| **Site pages** (`tech`) | Home, about, services, contact form |
| **REST API** | DRF + JWT (`simplejwt`) + token auth, CORS enabled |
| **Admin** | Django admin themed with Jazzmin |

## Tech stack

- Python 3.12, Django 4.2, Django REST Framework, SimpleJWT, django-cors-headers
- MySQL (via `mysqlclient`)
- Jazzmin admin theme, Django Debug Toolbar, django-extensions, WhiteNoise
- pandas, numpy, openpyxl, OpenCV, Pillow (data import and dataset/CV exercises)
- Bootstrap 5, jQuery, Owl Carousel, Font Awesome (frontend via CDN)

## Project structure

```
techphile_exams/
├── manage.py
├── requirements.txt
├── techphile_exams/        # Project config: settings, root urls, wsgi/asgi
├── accounts/               # Signup, login, logout, email verification, password reset
├── exams/                  # Exams, questions, attempts, interviews, profiles, dashboards, REST API
├── coding/                 # Coding problems, submissions, code execution API, leaderboard
├── core/                   # Explore-courses topics, problems, datasets, progress, leaderboard
├── tech/                   # Public site pages (home/about/services/contact)
├── api/                    # Additional API endpoints
├── management/             # Custom management commands
├── explore_courses/        # Population scripts for course topics (AI, ML, DL, NLP, CV, ...)
├── tech_coding_questions/  # Sample data scripts for coding questions
├── tech_bits/              # Question banks in .xlsx (Python, SQL, DSA, React, Git, ML, ...)
├── datasets/               # CSVs and images used by exercises (iris, houses, sales, ...)
├── templates/              # Shared templates (base, home, about, contact, coding_temp, registration)
├── static/                 # CSS, JS, images, fonts
├── staticfiles/            # collectstatic output
├── media/                  # User uploads
├── populate_*.py           # Seed scripts (ML, DL, NLP, CV, GenAI, creativity, all)
└── .venv/                  # Local virtual environment (not committed)
```

Each Django app follows the usual layout: `models.py`, `views.py`, `urls.py`, `admin.py`, `forms.py`/`serializers.py`, `migrations/`, `templates/`.

### Main data models

- **exams**: `Category`, `Exam`, `Question`, `Answer`, `ExamAttempt`, `UserAnswer`, `Interviewer`, `Applicant`, `Bookmark`, `Profile`, `InterviewFeedback`
- **coding**: `Problem`, `Submission`, `UserProfile`
- **core**: `Topic`, `Dataset`, `Problem`, `Submissions`, `UserProgress`, `Leaderboard`
- **tech**: `Contact`

## URL map

| Prefix | App | Notable routes |
|--------|-----|----------------|
| `/` | tech | Home, about, services, contact |
| `/accounts/` | accounts | `signup/`, `login/`, `logout/`, `verify-email/<uid>/<token>/`, `password-reset/`, `terms-of-service/`, `privacy-policy/` |
| `/exams/` | exams | `dashboard/`, `mock-exams/`, `<exam_slug>/`, `result/<id>/`, `mock-interview/`, `interview/<id>/...`, `study-guide/`, `user-analytics/`, `settings/...`, plus `api/...` |
| `/coding/` | coding | `problems/`, `problems/<slug>/`, `submit/`, `dashboard/`, `leaderboard/`, `api/execute/` |
| `/explore_courses` | core | `creativity-intelligence/`, `topic/<id>/`, `datasets/`, `leaderboard/` |
| `/api/` | api | REST endpoints |
| `/admin/` | admin | Django admin (Jazzmin) |

REST auth endpoints live under `/exams/api/auth/` (`login`, `signup`, `logout`, `token`, `token/refresh`). Exam, interview, profile, dashboard and study-guide APIs are under `/exams/api/`.

## Authentication flow

- Anonymous users are sent to `/accounts/login/`; after login they go to the `next` URL if it is a safe internal URL, otherwise to the student dashboard (`exams:student_dashboard`).
- Already logged-in users visiting the login page are redirected to the dashboard (so the browser Back button does not re-show the login form).
- External or malicious `next` values are ignored.
- "Remember me" keeps a long session; otherwise the session ends when the browser closes.
- New accounts are inactive until they click the emailed verification link.

## Getting started

### Prerequisites

- Python 3.12
- MySQL 8 running locally
- Build tools/libraries needed by `mysqlclient` (on Windows, a prebuilt wheel is normally installed automatically)

### Setup

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the MySQL database
#    CREATE DATABASE Tech CHARACTER SET utf8mb4;

# 4. Apply migrations
python manage.py migrate

# 5. Create an admin user
python manage.py createsuperuser

# 6. (Optional) Load seed data
python populate_all.py

# 7. Run the development server
python manage.py runserver
```

Open <http://127.0.0.1:8000/> (use another port, e.g. `runserver 8765`, if 8000 is busy).

### Configuration

Settings are in [techphile_exams/settings.py](techphile_exams/settings.py). Secrets are read from environment variables or a local `.env` file (git-ignored). Copy the template and fill in your values:

```powershell
Copy-Item .env.example .env
```

| Variable | Notes |
|----------|-------|
| `SECRET_KEY`, `DEBUG` | Django secret key and debug flag |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | MySQL connection (default database `Tech` on `localhost:3306`) |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP (Gmail) account for verification and password-reset emails |
| `JUDGE0_API_KEY` | RapidAPI key for the Judge0 code-execution service |

`LOGIN_REDIRECT_URL` is `exams:student_dashboard`.

> **Security:** never commit `.env`. For production set `DEBUG=False` and a strong `SECRET_KEY`.

## Testing and checks

```powershell
python manage.py check
python manage.py test accounts --keepdb
```

The `accounts` tests cover login/signup page links, safe `next` redirects, external redirect blocking, remember-me session expiry, authenticated-user redirect, and the verification email flow. They need a MySQL user allowed to create a `test_Tech` database.

## Troubleshooting

- **`Can't create database 'test_tech'; database exists`** – run tests with `--keepdb`, or drop the leftover test database.
- **Port 8000 already in use** – start the server on another port.
- **`mysqlclient` fails to install** – install a matching wheel or the MySQL C connector/build tools.
- **Missing column errors (e.g. `expected_output`)** – run `python manage.py migrate`; migration `coding/0008_restore_expected_output` repairs databases that drifted from the models.
- **Static files not loading in production** – run `python manage.py collectstatic`.
