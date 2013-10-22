# django-celery-transactions

django-celery-transactions holds on to Celery tasks until the current database
transaction is committed, avoiding potential race conditions as described in
Celery's [user guide][1]. Send tasks from signal handlers without fear!

## Features

* If the transaction is rolled back, the tasks are discarded. Django's
  transaction middleware does this if an exception is raised.
* If transactions aren't being managed, tasks are sent as normal. This means
  that sending tasks from within Django's shell will work as expected, as will
  the various transaction decorators `commit_manually`, `commit_on_success`, etc.

## Installation & Use

1. Install django-celery-transactions from PyPI:

        $ pip install django-celery-transactions

2. Use the patched decorator to create your tasks:

        from djcelery_transactions import task
        from models import Model


        @task
        def print_model(model_pk):
            print Model.objects.get(pk=model_pk)

3. Then use them as normal:

        from django.db import transaction
        from models import Model
        from tasks import print_model


        # This task will be sent after the transaction is committed. This works
        # from anywhere in the managed transaction block (e.g. signal handlers).
        def view(request):
            model = Model.objects.create(...)
            print_model.delay(model.pk)


        # This task will not be sent (it is discarded) as the transaction
        # middleware rolls the transaction back when it catches the exception.
        def failing_view(request, model_pk):
            print_model.delay(model_pk)
            raise Exception()


        # This task will be sent immediately as transactions aren't being
        # managed and it is assumed that the author knows what they're doing.
        @transaction.commit_manually
        def manual_view(request, model_pk):
            print_model.delay(model_pk)
            transaction.commit()

## Caveats

Due to the task being sent after the current transaction has been commited, the
`PostTransactionTask` provided in this package does not return an
`celery.result.AsyncResult` as the original celery `Task` does.

Thus, `print_model.delay(model_pk)` simply returns `None`. In order to track
the task later on, the `task_id` can be predefined in the `apply_async` method:

        from celery.utils import uuid

        u = uuid()
        print_model.apply_async((model_pk), {}, task_id=u)

## Run test suite

        $ python setup.py test

[1]: http://celery.readthedocs.org/en/latest/userguide/tasks.html#database-transactions
