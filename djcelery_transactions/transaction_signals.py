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

from django.db import transaction, connections, DEFAULT_DB_ALIAS, DatabaseError, ProgrammingError
from django.db.transaction import get_connection
from django.dispatch import Signal


class TransactionSignals(object):
    """A container for the transaction signals."""

    def __init__(self):
        self.post_commit = Signal()
        self.post_rollback = Signal()


# Access as django.db.transaction.signals.
transaction.signals = TransactionSignals()
__original__exit__ = transaction.Atomic.__exit__

def __patched__exit__(self, exc_type, exc_value, trackback):
    connection = get_connection(self.using)

    if connection.savepoint_ids:
        sid = connection.savepoint_ids.pop()
    else:
        # Prematurely unset this flag to allow using commit or rollback.
        connection.in_atomic_block = False

    try:
        if exc_type is None and not connection.needs_rollback:
            if connection.in_atomic_block:
                # Release savepoint if there is one
                if sid is not None:
                    try:
                        connection.savepoint_commit(sid)
                        transaction.signals.post_commit.send(None)
                    except DatabaseError:
                        connection.savepoint_rollback(sid)
                        transaction.signals.post_rollback.send(None)
                        raise
            else:
                # Commit transaction
                try:
                    connection.commit()
                    transaction.signals.post_commit.send(None)
                except DatabaseError:
                    connection.rollback()
                    transaction.signals.post_rollback.send(None)
                    raise
        else:
            # This flag will be set to True again if there isn't a savepoint
            # allowing to perform the rollback at this level.
            connection.needs_rollback = False
            if connection.in_atomic_block:
                # Roll back to savepoint if there is one, mark for rollback
                # otherwise.
                if sid is None:
                    connection.needs_rollback = True
                else:
                    connection.savepoint_rollback(sid)
                    transaction.signals.post_rollback.send(None)
            else:
                # Roll back transaction
                connection.rollback()
                transaction.signals.post_rollback.send(None)

    finally:
        # Outermost block exit when autocommit was enabled.
        if not connection.in_atomic_block:
            if connection.features.autocommits_when_autocommit_is_off:
                connection.autocommit = True
            else:
                connection.set_autocommit(True)
        # Outermost block exit when autocommit was disabled.
        elif not connection.savepoint_ids and not connection.commit_on_exit:
            connection.in_atomic_block = False


# Monkey patch that shit
transaction.Atomic.__exit__ = __patched__exit__
