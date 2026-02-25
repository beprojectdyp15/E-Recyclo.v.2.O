"""
Settings package for E-RECYCLO
Automatically loads the correct settings based on ENVIRONMENT variable
"""

from decouple import config

ENVIRONMENT = config('ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .production import *
else:
    from .development import *