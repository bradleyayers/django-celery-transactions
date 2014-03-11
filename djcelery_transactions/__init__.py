# coding=utf-8
from celery.task import task as base_task, Task
from celery import current_app
import djcelery_transactions.transaction_signals
from django.db import transaction
from functools import partial
import threading

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
    keyword argument is ``False``, the task will be sent immediately.

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
        if not getattr(current_app.conf, 'CELERY_ALWAYS_EAGER', False):
            _get_task_queue().append((cls, args, kwargs))
        else:
            return cls.original_apply_async(*args, **kwargs)


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
        cls.original_apply_async(*args, **kwargs)


# A replacement decorator.
task = partial(base_task, base=PostTransactionTask)

# Hook the signal handlers up.
transaction.signals.post_commit.connect(_send_tasks)
transaction.signals.post_rollback.connect(_discard_tasks)
