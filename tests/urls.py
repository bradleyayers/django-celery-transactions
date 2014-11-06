from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'^test_api', 'test.views.test_api')
)