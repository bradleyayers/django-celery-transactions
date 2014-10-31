from djcelery_transactions import task

from django.db import transaction
from django.test import TransactionTestCase

my_global = []

marker = object()

@task
def my_task():
    my_global.append(marker)

try:
    from celery.registry import tasks
    tasks.register(my_task)
except:
    from celery import task as base_task, current_app, Task
    current_app.registry.register(my_task)

class SpecificException(Exception):
    pass

class DjangoCeleryTestCase(TransactionTestCase):
    """Test djcelery transaction safe task manager
    """
    def tearDown(self):
        my_global[:] = []

    def test_commited_transaction_fire_task(self):
        """Check that task is consumed when no exception happens
        """

        @transaction.commit_on_success
        def do_something():
            my_task.delay()

        do_something()
        self.assertTrue(my_global[0] is marker)

    def test_rollbacked_transaction_discard_task(self):
        """Check that task is not consumed when exception happens
        """

        @transaction.commit_on_success
        def do_something():
            my_task.delay()
            raise SpecificException
        try:
            do_something()
        except SpecificException:
            self.assertFalse(my_global)
        else:
            self.fail('Exception not raised')
