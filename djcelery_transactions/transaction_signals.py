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
from functools import partial
import thread

from django.db import transaction
try:
    # Prior versions of Django 1.3
    from django.db.transaction import state
except ImportError:
    state = None
from django.dispatch import Signal


class TransactionSignals(object):
    """A container for the transaction signals."""

    def __init__(self):
        self.post_commit = Signal()
        self.post_rollback = Signal()
        self.post_transaction_management = Signal()


# Access as django.db.transaction.signals.
transaction.signals = TransactionSignals()


def commit(old_function, *args, **kwargs):
    # This will raise an exception if the commit fails. django.db.transaction
    # decorators catch this and call rollback(), but the middleware doesn't.
    old_function(*args, **kwargs)
    transaction.signals.post_commit.send(None)


def commit_unless_managed(old_function, *args, **kwargs):
    old_function(*args, **kwargs)
    if not transaction.is_managed():
        transaction.signals.post_commit.send(None)


# commit() isn't called at the end of a transaction management block if there
# were no changes. This function is always called so the signal is always sent.
def leave_transaction_management(old_function, *args, **kwargs):
    # If the transaction is dirty, it is rolled back and an exception is
    # raised. We need to send the rollback signal before that happens.
    if transaction.is_dirty():
        transaction.signals.post_rollback.send(None)

    old_function(*args, **kwargs)
    transaction.signals.post_transaction_management.send(None)


def managed(old_function, *args, **kwargs):
    # Turning transaction management off causes the current transaction to be
    # committed if it's dirty. We must send the signal after the actual commit.
    flag = kwargs.get('flag', args[0])
    if state is not None:
        using = kwargs.get('using', args[1] if len(args) > 1 else None)
        # Do not commit too early for prior versions of Django 1.3
        thread_ident = thread.get_ident()
        top = state.get(thread_ident, {}).get(using, None)
        commit = top and not flag and transaction.is_dirty()
    else:
        commit = not flag and transaction.is_dirty()
    old_function(*args, **kwargs)

    if commit:
        transaction.signals.post_commit.send(None)


def rollback(old_function, *args, **kwargs):
    old_function(*args, **kwargs)
    transaction.signals.post_rollback.send(None)


def rollback_unless_managed(old_function, *args, **kwargs):
    old_function(*args, **kwargs)
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
