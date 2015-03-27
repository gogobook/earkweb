"""
Django settings for access_dipcreator project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# server settings

SERVER_PROTOCOL_PREFIX = "http://"

SERVER_IP = "81.189.135.189"

# repository

SERVER_REPO_PORT = "12060"

SERVER_REPO = SERVER_PROTOCOL_PREFIX + SERVER_IP + ":" + SERVER_REPO_PORT

SERVER_REPO_RECORD_PATH = "/repository/record"

SERVER_REPO_RECORD_CONTENT_QUERY = SERVER_REPO + SERVER_REPO_RECORD_PATH + "/{0}/field/n$content/data?ns.n=org.eu.eark"

# solr

SERVER_SOLR_PORT = "8983"

SERVER_SOLR_PATH = "/solr"

SERVER_SOLR = SERVER_PROTOCOL_PREFIX + SERVER_IP + ":" + SERVER_SOLR_PORT

#SOLR_QUERY_URL = "http://172.20.30.219:8983/solr/collection1/select?q=body%3A{0}%20AND%20(url%3A*derstandard.at)&sort=postings%20desc&start=0&rows=10&wt=json" 
SERVER_SOLR_QUERY_URL = SERVER_SOLR + SERVER_SOLR_PATH + "/collection1/select?q=content%3A{0}&start=0&rows=20&wt=json" 
#"http://172.20.30.219:8983/solr/collection1/select?q=body%3A{0}%20AND%20(url%3A*derstandard.at)&sort=postings%20desc&start=0&rows=10&wt=json"

RECORD_URL = "http://81.189.135.189:12060/repository/record/"

LILY_CONTENT_URL = "http://81.189.135.189:12060/repository/record/USER.DNA_AVID%5C.SA%5C.18001%5C.01_141104%2FMetadata%2FA0072716_PREMIS%5C.xml/field/n$content/data?ns.n=org.eu.eark"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 's!!9@ii^idp7n+2y=r8%l$y^i#dm-!yx57b+*@aa=$+@3kj=(&'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]

ALLOWED_HOSTS = []

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)



# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'search',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'access_dipcreator.urls'

WSGI_APPLICATION = 'access_dipcreator.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/tmp/access_dipcreator.log',
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
    'loggers': {
        'search.views': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}