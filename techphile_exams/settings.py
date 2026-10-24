"""
Django settings for Techphile Educational Platform.
"""

import os
from pathlib import Path
from decimal import Decimal

from decouple import config

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security (secrets are read from the environment or a local .env file)
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')
DEBUG = config(
    'DEBUG',
    default=True,
    cast=lambda value: str(value).strip().lower() in {'1', 'true', 'yes', 'on'},
)
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
DJANGO_APPS = [
    'unfold',
    'techphile_exams.apps.TechPhileAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_extensions',
    'debug_toolbar',
    
]

LOCAL_APPS = [
    'accounts',
    'exams',
    'tech',
    'api',
    'coding',
    'core',
    'careers',
    'interview_prep',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'exams.middleware.ProfilePreferencesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'exams.middleware.URLDebugMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
]


INTERNAL_IPS = [
    '127.0.0.1',
]


def show_debug_toolbar(request):
    """Keep development diagnostics off the admin workspace UI."""
    from debug_toolbar.middleware import show_toolbar

    is_admin_request = request.path_info == '/admin' or request.path_info.startswith('/admin/')
    return not is_admin_request and show_toolbar(request)

# Let the browser follow normal form redirects while developing. The toolbar
# otherwise pauses the user at the 302 response instead of showing saved state.
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TOOLBAR_CALLBACK': 'techphile_exams.settings.show_debug_toolbar',
}

ROOT_URLCONF = 'techphile_exams.urls'

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

WSGI_APPLICATION = 'techphile_exams.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='Tech'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('username', 'email'),
            'max_similarity': 1.5,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static and Media
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if not DEBUG
    else 'django.contrib.staticfiles.storage.StaticFilesStorage'
)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
PRIVATE_UPLOAD_ROOT = Path(config('PRIVATE_UPLOAD_ROOT', default=str(BASE_DIR / 'private_uploads')))

# Premium billing is a manual, account-level monthly plan. Order amounts are
# copied from these server settings when an order is created.
INTERVIEW_PREP_MONTHLY_PRICE = Decimal(config('INTERVIEW_PREP_MONTHLY_PRICE', default='49.00'))
INTERVIEW_PREP_CURRENCY = config('INTERVIEW_PREP_CURRENCY', default='INR')
INTERVIEW_PREP_UPI_QR_IMAGE = config('INTERVIEW_PREP_UPI_QR_IMAGE', default='').strip()
INTERVIEW_PREP_MERCHANT_NAME = config('INTERVIEW_PREP_MERCHANT_NAME', default='').strip()
INTERVIEW_PREP_UPI_ID = config('INTERVIEW_PREP_UPI_ID', default='').strip()
INTERVIEW_PREP_PAYMENTS_ENABLED = config('INTERVIEW_PREP_PAYMENTS_ENABLED', default=False, cast=bool)
INTERVIEW_PREP_AI_PROVIDER = config('INTERVIEW_PREP_AI_PROVIDER', default='groq').strip().lower()
INTERVIEW_PREP_OPENAI_API_KEY = config('INTERVIEW_PREP_OPENAI_API_KEY', default='').strip()
INTERVIEW_PREP_OPENAI_MODEL = config('INTERVIEW_PREP_OPENAI_MODEL', default='gpt-4o-mini').strip()
INTERVIEW_PREP_GROQ_API_KEY = config('INTERVIEW_PREP_GROQ_API_KEY', default='').strip()
INTERVIEW_PREP_GROQ_MODEL = config('INTERVIEW_PREP_GROQ_MODEL', default='openai/gpt-oss-20b').strip()
INTERVIEW_PREP_MARKET_RESEARCH_PROVIDER = config('INTERVIEW_PREP_MARKET_RESEARCH_PROVIDER', default='none').strip().lower()
INTERVIEW_PREP_MARKET_RESEARCH_CACHE_HOURS = config('INTERVIEW_PREP_MARKET_RESEARCH_CACHE_HOURS', default=24, cast=int)
INTERVIEW_PREP_STANDARD_QUESTION_RATIO = config('INTERVIEW_PREP_STANDARD_QUESTION_RATIO', default=0.70, cast=float)
INTERVIEW_PREP_FOUNDATION_MATCH_SCORE = config('INTERVIEW_PREP_FOUNDATION_MATCH_SCORE', default=50, cast=int)
INTERVIEW_PREP_MINIMUM_JD_MATCH_SCORE = config('INTERVIEW_PREP_MINIMUM_JD_MATCH_SCORE', default=75, cast=int)
INTERVIEW_PREP_INPUT_USD_PER_MILLION_TOKENS = config('INTERVIEW_PREP_INPUT_USD_PER_MILLION_TOKENS', default=0.0, cast=float)
INTERVIEW_PREP_OUTPUT_USD_PER_MILLION_TOKENS = config('INTERVIEW_PREP_OUTPUT_USD_PER_MILLION_TOKENS', default=0.0, cast=float)
# This switch can grant a clearly marked local test entitlement without a
# payment. It is forcibly unavailable whenever DEBUG is disabled.
INTERVIEW_PREP_TEST_ACCESS = DEBUG and config('INTERVIEW_PREP_TEST_ACCESS', default=False, cast=bool)

# Default primary key field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_URL = 'login'

# Student-facing navigation visibility. The coding and mock interview features
# stay installed and routable; these flags only show or hide their entry points.
# Set FEATURE_CODING=True / FEATURE_MOCK_INTERVIEWS=True in .env to show them again.
FEATURE_FLAGS = {
    'coding': config('FEATURE_CODING', default=False, cast=bool),
    'mock_interviews': config('FEATURE_MOCK_INTERVIEWS', default=False, cast=bool),
}
LOGIN_REDIRECT_URL = 'exams:student_dashboard'
LOGOUT_REDIRECT_URL = 'home'
GOOGLE_OAUTH_CLIENT_ID = config('GOOGLE_OAUTH_CLIENT_ID', default='')

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='techphile.ai@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = 'techphile@techphile.in'
CONTACT_EMAIL = 'techphile@techphile.in'
LOGIN_EMAIL = 'Activate@techphile.in'

# Site ID
SITE_ID = 1

# Base URL for email verification
BASE_URL = 'http://localhost:8000'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}


# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024

# Custom paths
DATASET_UPLOAD_PATH = 'datasets/'
CODE_EXECUTION_TIMEOUT = 60  # seconds

# Django Unfold Admin UI Settings
UNFOLD = {
    "SITE_TITLE": "TechPhile Admin",
    "SITE_HEADER": "TechPhile.ai",
    "SITE_SUBHEADER": "Analytics Control Center",
    "SITE_URL": "/",
    "SITE_ICON": "/static/images/logo-tp.png",
    "THEME": "light",
    "STYLES": ["css/techphile-admin-models.css"],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": "techphile_exams.admin_navigation.sidebar_navigation",
    },
    "COMMAND": {
        "search_models": True,
    },
    "COLORS": {
        "primary": {
            "50": "oklch(97% .014 250)",
            "100": "oklch(93% .03 250)",
            "200": "oklch(87% .06 250)",
            "300": "oklch(78% .10 250)",
            "400": "oklch(68% .14 250)",
            "500": "oklch(58% .16 250)",
            "600": "oklch(49% .15 250)",
            "700": "oklch(41% .13 250)",
            "800": "oklch(34% .10 250)",
            "900": "oklch(28% .07 250)",
            "950": "oklch(21% .05 250)",
        },
    },
}

# Judge0 API Settings
JUDGE0_API_URL = "https://judge0-ce.p.rapidapi.com"
JUDGE0_API_KEY = config('JUDGE0_API_KEY', default='')
JUDGE0_HEADERS = {
    "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
    "X-RapidAPI-Key": JUDGE0_API_KEY,
    "Content-Type": "application/json"
}
