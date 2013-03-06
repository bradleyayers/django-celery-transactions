from djcelery_transactions import task
from celery.registry import tasks
from django.db import transaction
from django.test import TransactionTestCase

my_global = []

marker = object()

@task
def my_task():
    my_global.append(marker)

tasks.register(my_task)

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

    def test_django_db_transaction_managed(self):
        """
        Check that django.db.transaction.managed is not affected
        by monkey-patching
        """
        from django.db import transaction
        self.assertFalse(transaction.is_managed())
        transaction.enter_transaction_management()
        try:
            transaction.managed()
            self.assertTrue(transaction.is_managed())
        finally:
            transaction.leave_transaction_management()
