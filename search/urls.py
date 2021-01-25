from django.conf.urls import url

from search.views import HaystackSearchView

urlpatterns = [
    url(r'^$', HaystackSearchView.as_view(), name='search'),
]
