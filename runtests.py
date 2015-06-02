# -*- coding: utf-8 -*-
import django
from django.conf import settings
from django.core.management import call_command

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
sys.path.insert(0, 'tests')


def runtests():
    if not settings.configured:
        # Choose database for settings
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            }
        }
        test_db = os.environ.get('DB', 'sqlite')
        if test_db == 'mysql':
            DATABASES['default'].update({
                'ENGINE': 'django.db.backends.mysql',
                'NAME': 'testdb',
                'USER': 'root',
            })

        # Configure test environment
        settings.configure(
            DATABASES=DATABASES,
            INSTALLED_APPS=(
                'tests',
            ),
            ROOT_URLCONF=None,  # tests override urlconf, but it still needs to be defined
            LANGUAGES=(
                ('en', 'English'),
            ),
            MIDDLEWARE_CLASSES=(),
        )

    if django.VERSION >= (1, 7):
        django.setup()
    failures = call_command(
        'test', 'tests', interactive=False, failfast=False, verbosity=2)

    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()
