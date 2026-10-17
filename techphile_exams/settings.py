"""
Django settings for Techphile Educational Platform.
"""

import os
from pathlib import Path

from decouple import config

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security (secrets are read from the environment or a local .env file)
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'jazzmin',
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
    'core'
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'exams.middleware.URLDebugMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]


INTERNAL_IPS = [
    '127.0.0.1',
]
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
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'exams:student_dashboard'
LOGOUT_REDIRECT_URL = 'home'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='techphile.ai@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = 'techphile@techphile.in'
CONTACT_EMAIL = 'ravisoftech150@gmail.com'
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

# Jazzmin Admin UI Settings
JAZZMIN_SETTINGS = {
    "site_title": "Techphile Admin",
    "site_header": "Techphile Administration",
    "site_brand": "Techphile",
    "site_logo": "images/logo.png",
    "site_icon": "images/favicon.ico",
    "login_logo": "images/logo-nav.png",
    "login_logo_dark": "images/logo.png",
    "welcome_sign": "Welcome to Techphile Administration",
    "copyright": "Techphile © 2025",
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Support", "url": "https://support.techphile.com", "new_window": True},
        {"name": "Live Site", "url": "/", "new_window": True},
        {"app": "exams"},
        {"model": "auth.User"},
        {"model": "exams.Interviewer"},
    ],
    "usermenu_links": [
        {"name": "Analytics", "url": "/admin/analytics", "icon": "fas fa-chart-line"},
        {"name": "Documentation", "url": "/admin/docs", "icon": "fas fa-book"},
        {"name": "Support", "url": "https://support.techphile.com", "new_window": True, "icon": "fas fa-life-ring"},
    ],
    "theme": "litera",
    "dark_mode_theme": "darkly",
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user-tie",
        "auth.Group": "fas fa-users",
        "exams.Applicant": "fas fa-user-graduate",
        "exams.Interviewer": "fas fa-chalkboard-teacher",
        "exams.Exam": "fas fa-file-alt",
        "exams.Question": "fas fa-question-circle",
        "exams.Answer": "fas fa-check-circle",
        "exams.ExamAttempt": "fas fa-clipboard-check",
        "exams.UserAnswer": "fas fa-pencil-alt",
        "exams.Category": "fas fa-folder",
        "exams.Profile": "fas fa-id-card",
    },
    "custom_css": "css/admin_custom.css",
    "custom_js": "js/admin_custom.js",
}

# Judge0 API Settings
JUDGE0_API_URL = "https://judge0-ce.p.rapidapi.com"
JUDGE0_API_KEY = config('JUDGE0_API_KEY', default='')
JUDGE0_HEADERS = {
    "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
    "X-RapidAPI-Key": JUDGE0_API_KEY,
    "Content-Type": "application/json"
}
