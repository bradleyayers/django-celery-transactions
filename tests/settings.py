__doc__ = """Minimal django settings to run manage.py test command"""

import djcelery
djcelery.setup_loader()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': __name__,
    }
}

CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

INSTALLED_APPS = ('tests',
                  'djcelery',
                  )
