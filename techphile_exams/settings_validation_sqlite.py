"""Isolated settings for validation against a fresh in-memory SQLite database."""

import secrets
from decimal import Decimal
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# A process-local key is sufficient for Django's test client and avoids storing
# or reusing any production secret.
SECRET_KEY = secrets.token_urlsafe(50)
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

INSTALLED_APPS = [
    'unfold',
    'techphile_exams.apps.TechPhileAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'rest_framework',
    'rest_framework.authtoken',
    'accounts',
    'exams',
    'tech',
    'api',
    'coding',
    'core',
    'careers',
    'interview_prep',
]

UNFOLD = {
    'SITE_TITLE': 'TechPhile Admin',
    'SITE_HEADER': 'TechPhile.ai',
    'SITE_SUBHEADER': 'Analytics Control Center',
    'SITE_URL': '/',
    'SITE_ICON': '/static/images/logo-tp.png',
    'THEME': 'light',
    'STYLES': ['css/techphile-admin-models.css'],
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': 'techphile_exams.admin_navigation.sidebar_navigation',
    },
    'COMMAND': {'search_models': True},
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'techphile_exams.urls'
WSGI_APPLICATION = 'techphile_exams.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'careers.context_processors.features',
            ],
        },
    },
]

# This is deliberately the only configured database alias. Django's test
# runner creates and destroys the test schema in this process-local database.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {'user_attributes': ('username', 'email'), 'max_similarity': 1.5},
    },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
PRIVATE_UPLOAD_ROOT = BASE_DIR / 'private_uploads_validation'
INTERVIEW_PREP_MONTHLY_PRICE = Decimal('29.00')
INTERVIEW_PREP_CURRENCY = 'INR'
INTERVIEW_PREP_UPI_QR_IMAGE = ''
INTERVIEW_PREP_MERCHANT_NAME = ''
INTERVIEW_PREP_UPI_ID = ''
INTERVIEW_PREP_PAYMENTS_ENABLED = False
INTERVIEW_PREP_OPENAI_API_KEY = ''
INTERVIEW_PREP_OPENAI_MODEL = 'gpt-4o-mini'
INTERVIEW_PREP_AI_PROVIDER = 'openai'
INTERVIEW_PREP_GROQ_API_KEY = ''
INTERVIEW_PREP_GROQ_MODEL = 'openai/gpt-oss-20b'
INTERVIEW_PREP_MARKET_RESEARCH_PROVIDER = 'none'
INTERVIEW_PREP_MARKET_RESEARCH_CACHE_HOURS = 24
INTERVIEW_PREP_STANDARD_QUESTION_RATIO = 0.70
INTERVIEW_PREP_FOUNDATION_MATCH_SCORE = 50
INTERVIEW_PREP_MINIMUM_JD_MATCH_SCORE = 75
INTERVIEW_PREP_INPUT_USD_PER_MILLION_TOKENS = 0.0
INTERVIEW_PREP_OUTPUT_USD_PER_MILLION_TOKENS = 0.0
INTERVIEW_PREP_TEST_ACCESS = False
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'exams:student_dashboard'
LOGOUT_REDIRECT_URL = 'home'
BASE_URL = 'http://testserver'
GOOGLE_OAUTH_CLIENT_ID = ''
COMPANY_NAME = 'TechPhile.ai'
CONTACT_EMAIL = 'techphile@techphile.in'
SITE_ID = 1
FEATURE_FLAGS = {'coding': False, 'mock_interviews': False}

DEFAULT_FROM_EMAIL = 'validation@localhost'
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}
