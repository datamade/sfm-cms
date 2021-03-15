from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import logout_then_login
from django.views.decorators.cache import cache_page
from django.core.urlresolvers import reverse_lazy

from sfm_pc.views import (Dashboard, osm_autocomplete, division_autocomplete,
                          command_chain, DownloadData, DumpChangeLog,
                          download_zip, About, about_redirect)

urlpatterns = i18n_patterns(
    url(r'^organization/', include('organization.urls')),
    url(r'^person/', include('person.urls')),
    url(r'^source/', include('source.urls')),
    url(r'^violation/', include('violation.urls')),
    url(r'^location/', include('location.urls')),
    url(r'^countries/(?P<country>[a-zA-Z-]+)/background/$', about_redirect, name="background"),
    url(r'^countries/', about_redirect, name="countries"),
    url(r'^help/', about_redirect, name="help"),
    url(r'^about/', About.as_view(), name="about"),
    url(r'^search/', include('search.urls')),
    url(r'^download/', DownloadData.as_view(), name="download"),
    url(r'^changelog/', DumpChangeLog.as_view(), name="changelog"),

    url(r'^osm-autocomplete/$', osm_autocomplete, name="osm-autocomplete"),
    url(r'^division-autocomplete/$', division_autocomplete, name="division-autocomplete"),
    url(r'^command-chain/(?P<org_id>[0-9a-f-]+)/$', cache_page(60 * 60 * 24)(command_chain), name="command-chain"),
    url(r'^command-chain/(?P<org_id>[0-9a-f-]+)/(?P<when>[0-9-]+)/$', cache_page(60 * 60 * 24)(command_chain), name="command-chain-bounded"),

    # Dashboard
    url(r'^$', cache_page(60 * 60 * 24)(Dashboard.as_view()), name='dashboard'),

    # Admin panel
    url(r'^admin/', include(admin.site.urls)),

    # Downloads
    url(r'^download/', cache_page(60 * 60 * 24)(download_zip), name='download'),

    # Authentication
    url(r'^logout/$', logout_then_login, {'login_url': reverse_lazy('login')}, name="logout"),

    # auth
    url('^', include('django.contrib.auth.urls')),

)

# Rosetta translation app
if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += (
        url(r'^rosetta/', include('rosetta.urls')),
    )

# Django debug toolbar (for local development only)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = i18n_patterns(
            # Django debug toolbar plugin
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ) + urlpatterns
    except ImportError:
        pass

# Custom 500 error handler
handler500 = 'sfm_pc.views.server_error'
