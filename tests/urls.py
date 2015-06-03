from django.conf.urls import patterns
from tests.test import views

urlpatterns = patterns('',
    (r'^test_api', views.test_api)
)