# django-celery-transactions

django-celery-transactions holds on to Celery tasks until the current database
transaction is committed, avoiding potential race conditions as described in
the [Celery user guide][1]. This lets you focus on your app's structure—send
tasks from signal handlers without fear!

## Features

* If the transaction is rolled back, the tasks are discarded. Django's
  transaction middleware does this if your view raises an exception.
* If transactions aren't being managed, tasks are sent as normal. This means
  that sending tasks from Django's shell will work as expected, as will the
  transaction decorators `commit_on_success`, `commit_manually`, etc.

**Note:** As middleware is used to implement this functionality, it will only
work from within the request/response cycle.

## Installation/Use

1. Install django-celery-transactions from PyPI:

        $ pip install django-celery-transactions

2. Add `PostCommitTaskMiddleware` to `MIDDLEWARE_CLASSES` in `settings.py`
   (it must appear before Django's transaction middleware):

        MIDDLEWARE_CLASSES = (
            # ...
            "djcelery_transactions.PostCommitTaskMiddleware",
            "django.middleware.transaction.TransactionMiddleware",
            # ...
        )

3. Use the patched decorator to create your tasks:

        from djcelery_transaction import task


        @task
        def example():
            print "Hooray, the transaction has been committed!"

[1]: http://celery.readthedocs.org/en/latest/userguide/tasks.html#database-transactions
