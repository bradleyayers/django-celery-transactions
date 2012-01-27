# coding=utf-8
from setuptools import setup, find_packages


setup(
    name="django-celery-transactions",
    version="0.1.0",
    description="Django transaction support for Celery tasks.",
    long_description="See https://github.com/chrisdoble/django-celery-transactions",
    author="Chris Doble",
    author_email="chris@chrisdoble.com",
    url="https://github.com/chrisdoble/django-celery-transactions",
    license="Simplified BSD",
    py_modules=["djcelery_transactions"],
    install_requires=[
        "celery",
        "Django>=1.3",
    ],
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Database",
    ],
)
