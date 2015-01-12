import os


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEBUG = True

MEDIA_ROOT = PROJECT_ROOT
INSTALLED_APPS = ( 'lazythumbs', )
MEDIA_URL = 'http://media.example.com/media/'

LAZYTHUMBS_EXTRA_URLS = {
   'http://example.com/media/': 'http://example.com/media/lt/',
}
LAZYTHUMBS_URL = MEDIA_URL + 'lt/'

LAZYTHUMBS_CACHE_TIMEOUT = 60
LAZYTHUMBS_404_CACHE_TIMEOUT = 60

LAZYTHUMBS_USE_X_FOR_DIMENSIONS = True

CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        },
}


TEMPLATE_DEBUG = DEBUG
DATABASES = {'default': {'ENGINE': 'django.db.backends.dummy'}}
SECRET_KEY = "foobar"
ADMINS = ( )
MANAGERS = ADMINS
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = False
USE_L10N = True
ADMIN_MEDIA_PREFIX = '/media/'
TEMPLATE_LOADERS = ()
TEMPLATE_DIRS = ( os.path.join(PROJECT_ROOT, 'templates'),)
MIDDLEWARE_CLASSES = ()
