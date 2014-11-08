import django, os
from djcelery_transactions import task
from django.test import TransactionTestCase
if django.VERSION < (1,7):
    from django.core.cache import cache
else:
    from django.core.cache import caches
    cache = caches['default']

if django.VERSION > (1,6):
    from django.db.transaction import atomic
else:
    from django.db import transaction
    atomic = transaction.commit_on_success

@task
def my_task():
    cache.set('my_global', 42)


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
