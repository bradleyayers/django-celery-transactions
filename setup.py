# coding=utf-8
import os
import sys

from setuptools import setup, Command, find_packages


class RunTests(Command):
    """RunTests class borrowed from django-celery project
    """
    description = 'Run the django test suite from the tests dir.'
    user_options = []
    extra_args = []

    def run(self):
        from django.core.management import execute_from_command_line
        settings_module_name = 'tests.settings'
        os.environ['DJANGO_SETTINGS_MODULE'] = os.environ.get(
                                                    'DJANGO_SETTINGS_MODULE',
                                                    settings_module_name)
        prev_argv = sys.argv[:]

        this_dir = os.getcwd()
        testproj_dir = os.path.join(this_dir, 'tests')
        os.chdir(testproj_dir)
        sys.path.append(testproj_dir)

        try:
            sys.argv = [__file__, 'test'] + self.extra_args
            execute_from_command_line(argv=sys.argv)
        finally:
            sys.argv[:] = prev_argv

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

setup(
    name="django-celery-transactions",
    version="0.3.0",
    description="Django transaction support for Celery tasks.",
    long_description="See https://github.com/fellowshipofone/django-celery-transactions",
    author="Nicolas Grasset",
    author_email="nicolas.grasset@gmail.com",
    url="https://github.com/fellowshipofone/django-celery-transactions",
    license="Simplified BSD",
    packages=["djcelery_transactions"],
    install_requires=[
        "celery>=2.2.7",
        "Django>=1.2.4",
    ],
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Database",
    ],
    cmdclass={'test': RunTests},
)
