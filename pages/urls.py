from django.conf.urls import url

from pages.views import About, FAQ, Help, Countries

urlpatterns = [
    url(r'^about/$', About.as_view(), name="about"),
    url(r'^faq/$', FAQ.as_view(), name="faq"),
    url(r'^help/$', Help.as_view(), name="help"),
    url(r'^countries/$', Countries.as_view(), name="countries"),
]
