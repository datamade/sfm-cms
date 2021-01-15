from django.conf.urls import url

from search.views import search, HaystackSearchView

urlpatterns = [
    url(r'^$', search, name="search"),
    url(r'^haystack/$', HaystackSearchView.as_view(), name='haystack_search'),
]
