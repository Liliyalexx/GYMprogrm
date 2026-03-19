from pathlib import Path
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Force https in production so OAuth callbacks use https://
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

# Trust Railway / Render domains for CSRF
_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'students',
    'programs',
    'progress',
    'measurements',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'gymprogrm.middleware.TrainerEnglishMiddleware',
]

ROOT_URLCONF = 'gymprogrm.urls'

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
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'gymprogrm.wsgi.application'

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL:
    import dj_database_url
    DATABASES = {'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Русский')),
    ('es', _('Español')),
    ('fr', _('Français')),
    ('de', _('Deutsch')),
    ('it', _('Italiano')),
    ('pt', _('Português')),
    ('zh-hans', _('中文')),
    ('ar', _('العربية')),
    ('ja', _('日本語')),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary for persistent media on Railway
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '')
if CLOUDINARY_URL:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    cloudinary.config(cloudinary_url=CLOUDINARY_URL)
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.RawMediaCloudinaryStorage'
    INSTALLED_APPS += ['cloudinary_storage', 'cloudinary']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/auth/redirect/'
LOGOUT_REDIRECT_URL = '/login/'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# django-allauth
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        },
    }
}

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Email — use Resend SMTP when API key is set, otherwise console
if RESEND_API_KEY:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.resend.com'
    EMAIL_PORT = 465
    EMAIL_HOST_USER = 'resend'
    EMAIL_HOST_PASSWORD = RESEND_API_KEY
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'GYMprogrm <noreply@gymprogrm.org>'
EMAIL_TIMEOUT = 10
