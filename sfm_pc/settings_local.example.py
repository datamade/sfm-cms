import raven


DATABASE_URL = 'postgis://postgres:postgres@postgres:5432/sfm'
GOOGLE_MAPS_KEY = 'key here'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'super duper secret'

IMPORTER_USER = {
    'username': 'importer',
    'password': 'super secret',
    'email': 'importer@importer.com',
    'first_name': 'Imp',
    'last_name': 'Orter',
    'is_staff': False,
}

DEBUG = True

ALLOWED_HOSTS = []

OSM_API_KEY = 'key here'

EXTRA_APPS = (
    'debug_toolbar',
    'raven.contrib.django.raven_compat',
)

EXTRA_MIDDLEWARE_CLASSES = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

INTERNAL_IPS = ['127.0.0.1']

SOLR_URL = 'http://solr:8983/solr/sfm'

RAVEN_CONFIG = {
    'dsn': 'https://<key>:<secret>@sentry.io/<project>',
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://solr:8983/solr/sfm_haystack',
        'SILENTLY_FAIL': False,
        'BATCH_SIZE': 100,
    },
}
