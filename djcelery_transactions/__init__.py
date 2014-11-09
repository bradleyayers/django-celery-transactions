# coding=utf-8
from functools import partial
import threading
from celery import current_app

from celery import task as base_task, current_app, Task
from celery.contrib.batches import Batches
import django
from django.conf import settings
from django.db import transaction

if django.VERSION >= (1, 6):
    from django.db.transaction import get_connection, atomic

import djcelery_transactions.transaction_signals

# Thread-local data (task queue).
_thread_data = threading.local()

def _get_task_queue():
    """Returns the calling thread's task queue."""
    return _thread_data.__dict__.setdefault("task_queue", [])


class PostTransactionTask(Task):
    """A task whose execution is delayed until after the current transaction.

    The task's fate depends on the outcome of the current transaction. If it's
    committed or no changes are made in the transaction block, the task is sent
    as normal. If it's rolled back, the task is discarded.

    If transactions aren't being managed when ``apply_asyc()`` is called (if
    you're in the Django shell, for example) or the ``after_transaction``
    keyword argument is ``False``, the task will
    A replacement decorator is provided:

    .. code-block:: python

        from djcelery_transactions import task

        @task
        def example(pk):
            print "Hooray, the transaction has been committed!"
    """

    abstract = True

    def original_apply_async(self, *args, **kwargs):
        """Shortcut method to reach real implementation
        of celery.Task.apply_sync
        """
        return super(PostTransactionTask, self).apply_async(*args, **kwargs)

    def apply_async(self, *args, **kwargs):
        # Delay the task unless the client requested otherwise or transactions
        # aren't being managed (i.e. the signal handlers won't send the task).

        celery_eager = _get_celery_settings('CELERY_ALWAYS_EAGER')

        # New setting to run eager task post transaction
        # defaults to `not CELERY_ALWAYS_EAGER`
        eager_transaction = _get_celery_settings('CELERY_EAGER_TRANSACTION',
                                                 not celery_eager)

        if django.VERSION < (1, 6):

            if transaction.is_managed() and eager_transaction:
                if not transaction.is_dirty():
                    # Always mark the transaction as dirty
                    # because we push task in queue that must be fired or discarded
                    if 'using' in kwargs:
                        transaction.set_dirty(using=kwargs['using'])
                    else:
                        transaction.set_dirty()
                _get_task_queue().append((self, args, kwargs))
            else:
                apply_async_orig = super(PostTransactionTask, self).apply_async
                return apply_async_orig(*args, **kwargs)

        else:

            connection = get_connection()
            if connection.in_atomic_block and eager_transaction:
                _get_task_queue().append((self, args, kwargs))
            else:
                return self.original_apply_async(*args, **kwargs)


class PostTransactionBatches(Batches):
    """A batch of tasks whose queuing is delayed until after the current
        transaction.
    """

    abstract = True

    def original_apply_async(self, *args, **kwargs):
        """Shortcut method to reach real implementation
        of celery.Task.apply_sync
        """
        return super(PostTransactionBatches, self).apply_async(*args, **kwargs)

    def apply_async(self, *args, **kwargs):
        # Delay the task unless the client requested otherwise or transactions
        # aren't being managed (i.e. the signal handlers won't send the task).

        celery_eager = _get_celery_settings('CELERY_ALWAYS_EAGER')

        # New setting to run eager task post transaction
        # defaults to `not CELERY_ALWAYS_EAGER`
        eager_transaction = _get_celery_settings('CELERY_EAGER_TRANSACTION',
                                                 not celery_eager)

        if django.VERSION < (1, 6):

            if transaction.is_managed() and eager_transaction:
                if not transaction.is_dirty():
                    # Always mark the transaction as dirty
                    # because we push task in queue that must be fired or discarded
                    if 'using' in kwargs:
                        transaction.set_dirty(using=kwargs['using'])
                    else:
                        transaction.set_dirty()
                _get_task_queue().append((self, args, kwargs))
            else:
                apply_async_orig = super(PostTransactionTask, self).apply_async
                return apply_async_orig(*args, **kwargs)

        else:

            connection = get_connection()
            if connection.in_atomic_block and eager_transaction:
                _get_task_queue().append((self, args, kwargs))
            else:
                return self.original_apply_async(*args, **kwargs)

def _discard_tasks(**kwargs):
    """Discards all delayed Celery tasks.

    Called after a transaction is rolled back."""
    _get_task_queue()[:] = []


def _send_tasks(**kwargs):
    """Sends all delayed Celery tasks.

    Called after a transaction is committed or we leave a transaction
    management block in which no changes were made (effectively a commit).
    """

    celery_eager = _get_celery_settings('CELERY_ALWAYS_EAGER')


    queue = _get_task_queue()
    while queue:
        tsk, args, kwargs = queue.pop(0)
        if django.VERSION < (1, 6):
            apply_async_orig = tsk.original_apply_async
            if celery_eager:
                apply_async_orig = transaction.autocommit()(apply_async_orig)
            apply_async_orig(*args, **kwargs)
        else:
            tsk.original_apply_async(*args, **kwargs)


# A replacement decorator.
task = partial(base_task, base=PostTransactionTask)

# Hook the signal handlers up.
transaction.signals.post_commit.connect(_send_tasks)
transaction.signals.post_rollback.connect(_discard_tasks)

def _get_celery_settings(setting, default=False):
    """ Returns CELERY setting
    :param setting:
    :param default:
    :return:
    """
    return any(getattr(obj, setting, default)
               for obj in (current_app.conf, settings))
