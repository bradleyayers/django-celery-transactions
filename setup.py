# coding=utf-8
import os
import sys

from setuptools import setup, Command, find_packages


setup(
    name="django-celery-transactions",
    version="0.3.1",
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
)
