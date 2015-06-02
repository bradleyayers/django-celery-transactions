import django, os
from djcelery_transactions import task
from django.test import TransactionTestCase
from models import Trees, Plants
if django.VERSION < (1,7):
    from django.core.cache import cache
else:
    from django.core.cache import caches
    cache = caches['default']

if django.VERSION >= (1,6):
    from django.db.transaction import atomic
else:
    from django.db import transaction
    atomic = transaction.commit_on_success

@task
def my_task():
    cache.set('my_global', 42)

@task
def my_model_task():
    Plants.objects.create(name='Oak')


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
        cache.delete('my_global')

    def test_commited_transaction_fire_task(self):
        """Check that task is consumed when no exception happens
        """

        @atomic
        def do_something():
            my_task.delay()

        do_something()
        self.assertEqual(cache.get('my_global'), 42)

    def test_rollbacked_transaction_discard_task(self):
        """Check that task is not consumed when exception happens
        """

        @atomic
        def do_something():
            my_task.delay()
            raise SpecificException
        try:
            do_something()
        except SpecificException:
            self.assertIsNone(cache.get('my_global'))
        else:
            self.fail('Exception not raised')

    def test_via_api(self):

        r = self.client.get('/test_api/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(cache.get('my_global'), 42)


    def test_django_db_transaction_managed(self):
        """
        Check that django.db.transaction.managed is not affected
        by monkey-patching
        """

        if django.VERSION >= (1,6):
            self.skipTest('Django 1.6 does not need this test')

        from django.db import transaction
        self.assertFalse(transaction.is_managed())
        transaction.enter_transaction_management()
        try:
            transaction.managed()
            self.assertTrue(transaction.is_managed())
        finally:
            transaction.leave_transaction_management()


    def test_multiple_models(self):
        """Check that task is consumed when no exception happens
        """

        @atomic
        def do_something():
            my_model_task.delay()

        do_something()
        Trees.objects.create(name='Grey Oak', plant=Plants.objects.get(name='Oak'))
