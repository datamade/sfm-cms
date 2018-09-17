"""
Django settings for sfm_pc project.

Generated by 'django-admin startproject' using Django 1.8.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import dj_database_url
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_URL='postgis://postgres:@127.0.0.1:5432/sfm'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY='super duper secret'

DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django_date_extensions',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'languages_plus',
    'countries_plus',
    'reversion',
    'leaflet',
    'bootstrap_pagination',
    'complex_fields',
    'sfm_pc',
    'organization',
    'person',
    'membershiporganization',
    'membershipperson',
    'composition',
    'source',
    'area',
    'association',
    'geosite',
    'emplacement',
    'violation',
    'location'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'reversion.middleware.RevisionMiddleware',
)

ROOT_URLCONF = 'sfm_pc.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sfm_pc.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

# Parse database configuration from $DATABASE_URL
DATABASES = {'default': dj_database_url.parse(DATABASE_URL)}
DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

FIXTURES_DIRS = (
    BASE_DIR + "/fixtures",
)

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGES = (
    ('fr', _('French')),
    ('en', _('English')),
    ('es', _('Spanish')),
)
LOCALE_PATHS = (
    BASE_DIR + '/locale',
)

LANGUAGE_CODE = 'en'


TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = 'staticfiles'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)


# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

LOGIN_URL = reverse_lazy('account_login')
LOGIN_REDIRECT_URL = '/'

AUTHENTICATION_BACKENDS = (
    'allauth.account.auth_backends.AuthenticationBackend',
)

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "email"

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

SITE_ID = 1

ALLOWED_CLASS_FOR_NAME = [
    'Person', 'Organization', 'Membership', 'Composition', 'Association', 'Area',
    'Emplacement', 'Geosite', 'Violation'
]

OSM_DATA = [
    {
        'country': 'Nigeria',
        'pbf_url': 'http://download.geofabrik.de/africa/nigeria-latest.osm.pbf',
        'osm_id': '192787',
        'boundary_url': 'https://osm.wno-edv-service.de/boundaries/exportBoundaries',
        'country_code': 'ng',
    },
    # {
    #     'country': 'Mexico',
    #     'pbf_url': 'http://download.geofabrik.de/north-america/mexico-latest.osm.pbf',
    #     'osm_id': '114686',
    #     'boundary_url': 'https://osm.wno-edv-service.de/boundaries/exportBoundaries',
    #     'country_code': 'mx',
    # },
]

SOLR_URL = ''

CONFIDENCE_LEVELS = (
    ('1', _('Low')),
    ('2', _('Medium')),
    ('3', _('High')),
)

OPEN_ENDED_CHOICES = (
    ('Y', _('Yes')),
    ('N', _('No')),
    ('E', _('Exact'))
)

RESEARCH_HANDBOOK_URL = "https://help.securityforcemonitor.org"
