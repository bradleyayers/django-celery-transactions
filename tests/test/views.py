from django.http import HttpResponse
from .tests import my_task
import django

if django.VERSION > (1,6):
    from django.db.transaction import atomic
else:
    from django.db import transaction
    atomic = transaction.commit_on_success

@atomic
def test_api(request):
    my_task.delay()
    return HttpResponse('ok')