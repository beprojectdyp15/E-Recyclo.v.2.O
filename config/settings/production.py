"""
Production settings for E-RECYCLO on Railway
This file OVERRIDES base.py settings for production
"""

from .base import *
import dj_database_url
import os

# ========================================
# DEBUG - Turn OFF in production
# ========================================

DEBUG = False

# ========================================
# ALLOWED HOSTS
# ========================================

ALLOWED_HOSTS = [
    '.railway.app',
    'localhost',
    '127.0.0.1',
]

# Add custom domain if you set one later
if os.environ.get('RAILWAY_PUBLIC_DOMAIN'):
    ALLOWED_HOSTS.append(os.environ.get('RAILWAY_PUBLIC_DOMAIN'))

# ========================================
# DATABASE - COMPLETELY OVERRIDE base.py
# ========================================

# This REPLACES the DATABASES setting from base.py
# Railway provides DATABASE_URL environment variable
# It looks like: postgresql://user:password@host:port/database

if 'DATABASE_URL' in os.environ:
    # Use Railway's PostgreSQL (PRODUCTION)
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=False,
        )
    }
else:
    # Fallback to base.py settings (should never happen in production)
    # But keeps local testing working if you run with production settings
    pass

# ========================================
# SECURITY SETTINGS
# ========================================

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Proxy headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
]

# ========================================
# EMAIL (Your Brevo SMTP)
# ========================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp-relay.brevo.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='E-RECYCLO <noreply@erecyclo.in>')

# ========================================
# STATIC FILES (WhiteNoise)
# ========================================

# Insert WhiteNoise middleware
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# WhiteNoise storage
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# ========================================
# MEDIA FILES
# ========================================

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ========================================
# REDIS CACHING
# ========================================

if 'REDIS_URL' in os.environ:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'RETRY_ON_TIMEOUT': True,
            },
            'KEY_PREFIX': 'erecyclo',
            'TIMEOUT': 300,
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Fallback to database sessions
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ========================================
# CELERY (if using)
# ========================================

if 'REDIS_URL' in os.environ:
    CELERY_BROKER_URL = os.environ.get('REDIS_URL')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL')

# ========================================
# LOGGING
# ========================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# ========================================
# ADMINS
# ========================================

ADMINS = [
    ('Admin', config('ADMIN_EMAIL', default='admin@erecyclo.com')),
]

MANAGERS = ADMINS