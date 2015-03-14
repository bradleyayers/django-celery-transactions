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
import django

from django.db import connections, DEFAULT_DB_ALIAS, DatabaseError

from django.dispatch import Signal

if django.VERSION >= (1,6):
    from django.db import ProgrammingError
    from django.db.transaction import get_connection

from django.db import transaction

class TransactionSignals(object):
    """A container for the transaction signals."""

    def __init__(self):
        self.post_commit = Signal()
        self.post_rollback = Signal()

        if django.VERSION < (1,6):
            self.post_transaction_management = Signal()

# Access as django.db.transaction.signals.
transaction.signals = TransactionSignals()

if django.VERSION < (1,6):
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
        flag = kwargs.get('flag', args[0] if args else None)
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


else:

    __original__exit__ = transaction.Atomic.__exit__

    def __patched__exit__(self, exc_type, exc_value, traceback):
        connection = get_connection(self.using)

        if connection.savepoint_ids:
            sid = connection.savepoint_ids.pop()
        else:
            # Prematurely unset this flag to allow using commit or rollback.
            connection.in_atomic_block = False

        try:
            if connection.closed_in_transaction:
                # The database will perform a rollback by itself.
                # Wait until we exit the outermost block.
                pass

            elif exc_type is None and not connection.needs_rollback:
                if connection.in_atomic_block:
                    # Release savepoint if there is one
                    if sid is not None:
                        try:
                            connection.savepoint_commit(sid)
                            #transaction.signals.post_commit.send(None)
                        except DatabaseError:
                            try:
                                connection.savepoint_rollback(sid)
                                transaction.signals.post_rollback.send(None)
                            except Exception:
                                # If rolling back to a savepoint fails, mark for
                                # rollback at a higher level and avoid shadowing
                                # the original exception.
                                connection.needs_rollback = True
                            raise
                else:
                    # Commit transaction
                    try:
                        connection.commit()
                        transaction.signals.post_commit.send(None)
                    except DatabaseError:
                        try:
                            connection.rollback()
                            transaction.signals.post_rollback.send(None)
                        except Exception:
                            # An error during rollback means that something
                            # went wrong with the connection. Drop it.
                            connection.close()
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
                        try:
                            connection.savepoint_rollback(sid)
                            transaction.signals.post_rollback.send(None)
                        except Exception:
                            # If rolling back to a savepoint fails, mark for
                            # rollback at a higher level and avoid shadowing
                            # the original exception.
                            connection.needs_rollback = True
                else:
                    # Roll back transaction
                    try:
                        connection.rollback()
                        transaction.signals.post_rollback.send(None)
                    except Exception:
                        # An error during rollback means that something
                        # went wrong with the connection. Drop it.
                        connection.close()

        finally:
            # Outermost block exit when autocommit was enabled.
            if not connection.in_atomic_block:
                if connection.closed_in_transaction:
                    connection.connection = None
                elif connection.features.autocommits_when_autocommit_is_off:
                    connection.autocommit = True
                else:
                    connection.set_autocommit(True)
            # Outermost block exit when autocommit was disabled.
            elif not connection.savepoint_ids and not connection.commit_on_exit:
                if connection.closed_in_transaction:
                    connection.connection = None
                else:
                    connection.in_atomic_block = False


    # Monkey patch that shit
    transaction.Atomic.__exit__ = __patched__exit__