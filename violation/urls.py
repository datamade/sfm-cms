from django.conf.urls import patterns, url

from .views import (ViolationCreate, ViolationUpdate, ViolationView, violation_search,
                    violation_csv, ViolationDelete)

urlpatterns = [
    url(r'^create/$', ViolationCreate.as_view(), name="create-event"),
    url(r'search/', violation_search, name='violation_search'),
    url(r'csv/', violation_csv, name='violation_csv'),
    url(r'delete/(?P<pk>\d+)/$',
        ViolationDelete.as_view(success_url="/violation/"),
        name='delete_violation'),
    url(r'(?P<pk>\d+)/$', ViolationUpdate.as_view(), name='edit_violation'),
    url(r'^$', ViolationView.as_view(), name='violation'),
]
