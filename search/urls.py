from django.conf.urls import url

from search.views import search, HaystackSearchView

urlpatterns = [
    url(r'^$', HaystackSearchView.as_view(), name='search'),
]
