# coding=utf-8
"""Adds signals to ``django.db.transaction``.

Signals are monkey patched into ``django.db.transaction``:

* ``post_commit``: sent after a transaction is committed. If no changes were
  made in the transaction block, nothing is committed and this won't be sent.
* ``post_rollback``: sent after a transaction is rolled back.
* ``post_transaction_management``: sent after leaving transaction management.
  This signal isn't  posted if a ``TransactionManagementError`` is raised.

.. code-block:: python

    import djcelery_transactions.transaction_signals


    def _post_commit(**kwargs):
        print "The transaction has been committed!"


    django.db.transaction.signals.post_commit.connect(_post_commit)

This code was inspired by Grégoire Cachet's implementation of similar
functionality, which can be found on GitHub: https://gist.github.com/247844

.. warning::

    This module must be imported before you attempt to use the signals.
"""
from django.db import transaction
from django.dispatch import Signal
from functools import partial


class TransactionSignals(object):
    """A container for the transaction signals."""

    def __init__(self):
        self.post_commit = Signal()
        self.post_rollback = Signal()
        self.post_transaction_management = Signal()


# Access as django.db.transaction.signals.
transaction.signals = TransactionSignals()


def commit(old_function, using=None):
    # This will raise an exception if the commit fails. django.db.transaction
    # decorators catch this and call rollback(), but the middleware doesn't.
    old_function(using)
    transaction.signals.post_commit.send(None)


def commit_unless_managed(old_function, using=None):
    old_function(using)
    if not transaction.is_managed():
        transaction.signals.post_commit.send(None)


# commit() isn't called at the end of a transaction management block if there
# were no changes. This function is always called so the signal is always sent.
def leave_transaction_management(old_function, using=None):
    # If the transaction is dirty, it is rolled back and an exception is
    # raised. We need to send the rollback signal before that happens.
    if transaction.is_dirty():
        transaction.signals.post_rollback.send(None)

    old_function(using)
    transaction.signals.post_transaction_management.send(None)


def managed(old_function, flag=True, using=None):
    # Turning transaction management off causes the current transaction to be
    # committed if it's dirty. We must send the signal after the actual commit.
    commit = not flag and transaction.is_dirty()
    old_function(flag, using)

    if commit:
        transaction.signals.post_commit.send(None)


def rollback(old_function, using=None):
    old_function(using)
    transaction.signals.post_rollback.send(None)


def rollback_unless_managed(old_function, using=None):
    old_function(using)
    if not transaction.is_managed():
        transaction.signals.post_rollback.send(None)


# Duck punching!
functions = (
    commit,
    commit_unless_managed,
    leave_transaction_management,
    managed,
    rollback,
    rollback_unless_managed,
)

for function in functions:
    name = function.__name__
    function = partial(function, getattr(transaction, name))
    setattr(transaction, name, function)
