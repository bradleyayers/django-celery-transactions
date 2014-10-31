__doc__ = """Minimal django settings to run manage.py test command"""

import os
import sys
# import source code dir
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), os.pardir))

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

INSTALLED_APPS = ('djcelery_transactions',
                  'djcelery',
                  )

SECRET_KEY = 'not-empty-for-tests'
