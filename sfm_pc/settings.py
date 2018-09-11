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
from django.contrib.messages import constants as messages

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from .settings_local import EXTRA_APPS
except ImportError:
    EXTRA_APPS = ()

try:
    from .settings_local import EXTRA_MIDDLEWARE_CLASSES
except ImportError:
    EXTRA_MIDDLEWARE_CLASSES = ()

try:
    from .settings_local import INTERNAL_IPS
except ImportError:
    INTERNAL_IPS = []

try:
    from .settings_local import RAVEN_CONFIG
except ImportError:
    RAVEN_CONFIG = {}

try:
    from .settings_local import EXTRA_DEBUG_TOOLBAR_PANELS
except ImportError:
    EXTRA_DEBUG_TOOLBAR_PANELS = []


try:
    from .settings_local import DATABASE_URL, GOOGLE_MAPS_KEY, \
        SECRET_KEY, DEBUG, ALLOWED_HOSTS, IMPORTER_USER, SOLR_URL, \
        CACHES, OSM_API_KEY
except ImportError as e:
    raise Exception('''DATABASE_URL,
                     GOOGLE_MAPS_KEY,
                     SECRET_KEY,
                     ALLOWED_HOSTS,
                     IMPORTER_USER,
                     SOLR_URL,
                     CACHES,
                     OSM_API_KEY,
                     and DEBUG must be defined in settings_local.py''')

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
    'django.contrib.humanize',
    'django_date_extensions',
    'rosetta',
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
    'search',
    'location'
)

INSTALLED_APPS += EXTRA_APPS

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'reversion.middleware.RevisionMiddleware',
)

# Debug toolbar middleware needs to be included as early as possible
MIDDLEWARE_CLASSES = EXTRA_MIDDLEWARE_CLASSES + MIDDLEWARE_CLASSES

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
] + EXTRA_DEBUG_TOOLBAR_PANELS


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

DATE_EXTENSIONS_OUTPUT_FORMAT_DAY_MONTH_YEAR = "j F Y"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

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
    'django.contrib.auth.backends.ModelBackend',
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

OSM_BASE_URL = 'https://wambachers-osm.website/boundaries/exportBoundaries'

OSM_DATA = [
    # {
    #     'country': 'Nigeria',
    #     'pbf_url': 'http://download.geofabrik.de/africa/nigeria-latest.osm.pbf',
    #     'relation_id': '192787',
    #     'country_code': 'ng',
    # },
    {
        'country': 'Mexico',
        'pbf_url': 'http://download.geofabrik.de/north-america/mexico-latest.osm.pbf',
        'relation_id': '114686',
        'country_code': 'mx',
    },
    # {
    #     'country': 'Sierra Leone',
    #     'pbf_url': 'http://download.geofabrik.de/africa/sierra-leone-latest.osm.pbf',
    #     'relation_id': '192777',
    #     'country_code': 'sl',
    # },
    # {
    #     'country': 'Democratic Republic of the Congo',
    #     'pbf_url': 'http://download.geofabrik.de/africa/congo-democratic-republic-latest.osm.pbf',
    #     'relation_id': '192795',
    #     'country_code': 'cd',
    # },
    # {
    #     'country': 'Liberia',
    #     'pbf_url': 'http://download.geofabrik.de/africa/liberia-latest.osm.pbf',
    #     'relation_id': '192780',
    #     'country_code': 'lr',
    # },
    # {
    #     'country': 'Sudan',
    #     'pbf_url': 'http://download.geofabrik.de/africa/sudan-latest.osm.pbf',
    #     'relation_id': '192789',
    #     'country_code': 'sd',
    # },
    # {
    #     'country': 'Egypt',
    #     'pbf_url': 'http://download.geofabrik.de/africa/egypt-latest.osm.pbf',
    #     'relation_id': '1473947',
    #     'country_code': 'eg',
    #
    # }
]

# Override built-in messages tags
MESSAGE_TAGS = {
    messages.SUCCESS: 'alert-success'
}

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

# Format this string with the user's language code
RESEARCH_HANDBOOK_URL = "https://help.securityforcemonitor.org"
