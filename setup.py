# coding=utf-8
from setuptools import setup, find_packages


setup(
    name="django-celery-transactions",
    version="0.1.2",
    description="Django transaction support for Celery tasks.",
    long_description="See https://github.com/chrisdoble/django-celery-transactions",
    author="Chris Doble",
    author_email="chris@chrisdoble.com",
    url="https://github.com/chrisdoble/django-celery-transactions",
    license="Simplified BSD",
    packages=["djcelery_transactions"],
    install_requires=[
        "celery>=2.4.2",
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
