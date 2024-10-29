import os

from .settings import *


DEBUG = False

ALLOWED_HOSTS = os.environ["ALLOWED_HOSTS"].split(",")

STATIC_ROOT = os.environ["STATIC_ROOT"]

DATABASES = DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ["DATABASE_NAME"],
        'USER': os.environ["DATABASE_USER"],
        'PASSWORD': os.environ["DATABASE_PASSWORD"],
        'HOST': os.environ["DATABASE_HOST"],
        'PORT': os.environ["DATABASE_PORT"],
    }
}

ADMIN_URL = os.environ["ADMIN_URL"]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = os.environ["EMAIL_PORT"]
EMAIL_USE_TLS = os.environ["EMAIL_USE_TLS"].lower() == "true" 
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
EMAIL_USE_SSL = os.environ["EMAIL_USE_SSL"].lower() == "true"
# Adresse affichée dans l'entête du mail
DEFAULT_FROM_EMAIL = os.environ["DEFAULT_FROM_EMAIL"]
