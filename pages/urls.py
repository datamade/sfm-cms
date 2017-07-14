from django.conf.urls import url

from pages.views import AboutPage, FAQPage, HelpPage, CountriesPage

urlpatterns = [
    url(r'^about/$', AboutPage.as_view(), name="about"),
    url(r'^faq/$', FAQPage.as_view(), name="faq"),
    url(r'^help/$', HelpPage.as_view(), name="help"),
    url(r'^countries/$', CountriesPage.as_view(), name="countries"),
]
