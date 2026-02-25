"""
Development settings for E-RECYCLO
"""

from .base import *

# ========================================
# DEBUG SETTINGS
# ========================================

DEBUG = True

# ========================================
# ALLOWED HOSTS
# ========================================

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# ========================================
# DATABASES
# ========================================

# Database settings are inherited from base.py
# No changes needed for development

# ========================================
# EMAIL (Console backend for development)
# ========================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# ========================================
# STATIC FILES
# ========================================

# Static files served by Django in development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# ========================================
# SECURITY (Disabled for development)
# ========================================

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# ========================================
# CORS (Allow all for development)
# ========================================

CORS_ALLOW_ALL_ORIGINS = True

# ========================================
# LOGGING (More verbose for development)
# ========================================

LOGGING['handlers']['console']['level'] = 'WARNING'
LOGGING['root']['level'] = 'WARNING'
LOGGING['loggers']['django']['level'] = 'WARNING'

# ========================================
# DEBUG TOOLBAR (Optional - install if needed)
# ========================================

# Uncomment if you install django-debug-toolbar
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
# INTERNAL_IPS = ['127.0.0.1']