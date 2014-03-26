# coding=utf-8
from celery.task import task as base_task, Task
import djcelery_transactions.transaction_signals
from django.db import transaction
from functools import partial
import threading
from celery import current_app


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

    @classmethod
    def original_apply_async(cls, *args, **kwargs):
        """Shortcut method to reach real implementation
        of celery.Task.apply_sync
        """
        return super(PostTransactionTask, cls).apply_async(*args, **kwargs)

    @classmethod
    def apply_async(cls, *args, **kwargs):
        # Delay the task unless the client requested otherwise or transactions
        # aren't being managed (i.e. the signal handlers won't send the task).

        # A rather roundabout way of allowing control of transaction behaviour from source. I'm sure there's a better way.
        after_transaction = True
        if len(args) > 1:
            if isinstance(args[1], dict):
                after_transaction = args[1].pop('after_transaction', True)
        if 'after_transaction' in kwargs:
            after_transaction = kwargs.pop('after_transaction')

        if transaction.is_managed() and after_transaction:
            if not transaction.is_dirty():
                # Always mark the transaction as dirty
                # because we push task in queue that must be fired or discarded
                if 'using' in kwargs:
                    transaction.set_dirty(using=kwargs['using'])
                else:
                    transaction.set_dirty()
            _get_task_queue().append((cls, args, kwargs))
        else:
            apply_async_orig = cls.original_apply_async
            if current_app.conf.CELERY_ALWAYS_EAGER:
                apply_async_orig =  transaction.autocommit()(apply_async_orig)
            return apply_async_orig(*args, **kwargs)


def _discard_tasks(**kwargs):
    """Discards all delayed Celery tasks.

    Called after a transaction is rolled back."""
    _get_task_queue()[:] = []


def _send_tasks(**kwargs):
    """Sends all delayed Celery tasks.

    Called after a transaction is committed or we leave a transaction
    management block in which no changes were made (effectively a commit).
    """
    queue = _get_task_queue()
    while queue:
        cls, args, kwargs = queue.pop(0)
        apply_async_orig = cls.original_apply_async
        if current_app.conf.CELERY_ALWAYS_EAGER:
            apply_async_orig = transaction.autocommit()(apply_async_orig)
        apply_async_orig(*args, **kwargs)


# A replacement decorator.
task = partial(base_task, base=PostTransactionTask)

# Hook the signal handlers up.
transaction.signals.post_commit.connect(_send_tasks)
transaction.signals.post_rollback.connect(_discard_tasks)
transaction.signals.post_transaction_management.connect(_send_tasks)
