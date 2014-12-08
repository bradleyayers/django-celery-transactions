# django-celery-transactions


[![Travis](https://img.shields.io/travis/fellowshipofone/django-celery-transactions.svg?style=flat)][2]
[![Version](https://img.shields.io/pypi/v/django-celery-transactions.svg?style=flat)][3]
[![Downloads](https://img.shields.io/pypi/dm/django-celery-transactions.svg?style=flat)][4]
[![Coverage Status](https://coveralls.io/repos/fellowshipofone/django-celery-transactions/badge.png?branch=master)][5]

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

```sh
$ pip install django-celery-transactions
```

2. Use the patched decorator to create your tasks:

```python
from djcelery_transactions import task
from models import Model


@task
def print_model(model_pk):
    print Model.objects.get(pk=model_pk)
```

3. Then use them as normal:

```python
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
```

## Caveats

Due to the task being sent after the current transaction has been commited, the
`PostTransactionTask` provided in this package does not return an
`celery.result.AsyncResult` as the original celery `Task` does.

Thus, `print_model.delay(model_pk)` simply returns `None`. In order to track
the task later on, the `task_id` can be predefined in the `apply_async` method:

        from celery.utils import uuid

        u = uuid()
        print_model.apply_async((model_pk), {}, task_id=u)
        
## Compatibility with CELERY_ALWAYS_EAGER

There are 2 main reasons for `CELERY_ALWAYS_EAGER`:

   1. Running task synchronously and returning `EagerResult`, Celery's 
   [user guide][1]
   
   2. Being able to run code (often tests) without a celery broker.
   
For this second reason, the intended behavior will often conflict with 
transactions handling, which is why you should then also use 
`CELERY_EAGER_TRANSACTION`

        CELERY_ALWAYS_EAGER = True
        CELERY_EAGER_TRANSACTION = True

## Run test suite

```sh
$ python setup.py test
```

[1]: http://celery.readthedocs.org/en/latest/userguide/tasks.html#database-transactions
[2]: https://travis-ci.org/fellowshipofone/django-celery-transactions
[3]: https://pypi.python.org/pypi/django-celery-transactions
[4]: https://pypi.python.org/pypi/django-celery-transactions
[5]: https://coveralls.io/r/fellowshipofone/django-celery-transactions?branch=master
