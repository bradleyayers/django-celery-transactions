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


        @task
        def example():
            print "Hooray, the transaction has been committed!"

[1]: http://celery.readthedocs.org/en/latest/userguide/tasks.html#database-transactions
