import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    'http://localhost:8000',
    'http://127.0.0.1:8000',
])

SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=False)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)


# ── AWS Configuration (static/media — images, PDFs, docs, profile photos) ──
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default=None)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default=None)
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="ap-south-1")
USE_S3 = env.bool("USE_S3", default=False)

AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_VERIFY = True
AWS_DEFAULT_ACL = None
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_S3_CORS_RULES = [
    {
        'AllowedHeaders': ['*'],
        'AllowedMethods': ['GET', 'HEAD'],
        'AllowedOrigins': env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:8000']),
        'MaxAgeSeconds': 3000,
    }
]

if USE_S3:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": AWS_ACCESS_KEY_ID,
                "secret_key": AWS_SECRET_ACCESS_KEY,
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "region_name": AWS_S3_REGION_NAME,
                "querystring_auth": False,
                "signature_version": AWS_S3_SIGNATURE_VERSION,
                "file_overwrite": False,
                "verify": AWS_S3_VERIFY,
                "location": "media",
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/"
    STATIC_URL = '/static/'
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    STATIC_URL = '/static/'
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ── Video pipeline — separate buckets from static/media, never through django-storages ──
# These are accessed directly via boto3 in the `stream` app (presigned uploads, CloudFront signing),
# not through Django's default file storage.
AWS_RAW_VIDEO_BUCKET = env("AWS_RAW_VIDEO_BUCKET", default=None)
AWS_PROCESSED_VIDEO_BUCKET = env("AWS_PROCESSED_VIDEO_BUCKET", default=None)
MEDIACONVERT_ENDPOINT = env("MEDIACONVERT_ENDPOINT", default=None)
MEDIACONVERT_ROLE_ARN = env("MEDIACONVERT_ROLE_ARN", default=None)
MEDIACONVERT_JOB_TEMPLATE = env("MEDIACONVERT_JOB_TEMPLATE", default=None)

# CloudFront signed cookies for lesson playback
CLOUDFRONT_DOMAIN = env("CLOUDFRONT_DOMAIN", default=None)                     # e.g. d123abc.cloudfront.net
CLOUDFRONT_KEY_PAIR_ID = env("CLOUDFRONT_KEY_PAIR_ID", default=None)
CLOUDFRONT_PRIVATE_KEY = env("CLOUDFRONT_PRIVATE_KEY", default=None)           # loaded from Secrets Manager at deploy time
CLOUDFRONT_SIGNED_URL_EXPIRY_SECONDS = env.int("CLOUDFRONT_SIGNED_URL_EXPIRY_SECONDS", default=14400)  # 4 hours

# ── Application definition ──
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Created apps
    'accounts',
    'admin_dashboard',
    'user',
    'user_dashboard',
    'course',
    'public',
    'stream',

    # Third-party
    'storages',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Production/CI-CD
    'whitenoise.middleware.WhiteNoiseMiddleware',

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Custom — enforces profile completion before learners can access course content
    "user.middleware.ProfileCompletionMiddleware",
]

ROOT_URLCONF = "main.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "main.wsgi.application"

# ── Database — RDS PostgreSQL in production, sqlite fallback for local dev ──
# if env.bool("USE_RDS", default=False):
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.postgresql",
#             "NAME": env("DB_NAME"),
#             "USER": env("DB_USER"),
#             "PASSWORD": env("DB_PASSWORD"),
#             "HOST": env("DB_HOST"),
#             "PORT": env("DB_PORT", default="5432"),
#             "CONN_MAX_AGE": 60,
#         }
#     }
# else:
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.sqlite3",
#             "NAME": BASE_DIR / "db.sqlite3",
#         }
#     }

# ── Database — SQLite everywhere (local dev and production) ──
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ── Custom user model ──
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrPhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Learner-side login/logout. Admin views use @admin_required / @superadmin_required
# (accounts/decorators.py) and never rely on these — they redirect to accounts:admin_login directly.
LOGIN_URL = 'user:login'
LOGIN_REDIRECT_URL = 'user_dashboard:home'
LOGOUT_REDIRECT_URL = 'public:home'

# ── Celery — background jobs (certificate generation, notifications) ──
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default=None)   # SQS queue URL, or redis:// if using ElastiCache
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'region': AWS_S3_REGION_NAME,
    'polling_interval': 5,
}
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'Asia/Kolkata'

# ── Email — via Amazon SES ──
# ── Email — plain SMTP (Gmail, or any SMTP provider) ──
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default=None)
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default=None)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='no-reply@example.com')

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Whitenoise settings
WHITENOISE_AUTOREFRESH = True
WHITENOISE_ROOT = None
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = []

# File upload limits — course docs/assignments can be sizeable PDFs
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024   # 20MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# Session
# SESSION_COOKIE_AGE = 60 * 60 * 24 * 7   # 7 days
# SESSION_EXPIRE_AT_BROWSER_CLOSE = False

