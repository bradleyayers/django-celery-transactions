# coding=utf-8
from celery.task import task as base_task, Task
import django.core.signals
from django.db import transaction
from functools import partial
import threading


# Used to store deferred tasks.
_thread_data = threading.local()
_thread_data.task_queue = []


class PostCommitTask(Task):
    """A task whose execution is deferred until after the current transaction.

    The task's fate depends on the success or failure of the current view. If
    it raises an exception, the task is cancelled as the transaction would've
    been rolled back. If no errors occur, the task is dispatched as normal as
    the transaction would have been committed.

    If transactions aren't being managed when ``apply_async()`` is called (if
    you're in the Django shell, for example) or the ``after_transaction``
    keyword argument is ``False``, the task will be dispatched as normal.

    Usage:

    .. code-block:: python

        from djcelery_transactions import task

        @task
        def example(pk):
            print "Hooray, the transaction has been committed!"
    """

    abstract = True

    @classmethod
    def apply_async(cls, *args, **kwargs):
        # Defer the task unless the client requested otherwise or transactions
        # aren't being managed (i.e. the signal handlers won't send the task).
        after_transaction = kwargs.pop("after_transaction", True)
        defer_task = after_transaction and transaction.is_managed()

        if defer_task:
            _thread_data.task_queue.append((cls, args, kwargs))
        else:
            return super(PostCommitTask, cls).apply_async(*args, **kwargs)


def _request_finished(*args, **kwargs):
    """Dispatches all delayed Celery tasks.

    Called when a request finishes successfully (at which point Django's
    transaction middleware would have committed the transaction).
    """
    while len(_thread_data.task_queue) > 0:
        cls, args, kwargs = _thread_data.task_queue.pop()
        cls.apply_async(*args, after_transaction=False, **kwargs)


def _got_request_exception(*args, **kwargs):
    """Discards all delayed Celery tasks.

    Called when a request fails from an exception being raised (at which point
    Django's transaction middleware would have rolled the transaction back).
    """
    _thread_data.task_queue = []


# A replacement decorator.
task = partial(base_task, base=PostCommitTask)

# Hook the signal handlers up.
django.core.signals.request_finished.connect(_request_finished)
django.core.signals.got_request_exception.connect(_got_request_exception)
