from django.conf.urls import url
from django.views.decorators.cache import cache_page

from organization.views import organization_autocomplete, OrganizationDetail, \
    OrganizationEditBasicsView, OrganizationEditCompositionView, \
    OrganizationEditPersonnelView, OrganizationEditEmplacementView, \
    OrganizationEditAssociationView, OrganizationCreateBasicsView, \
    OrganizationCreateCompositionView, OrganizationCreatePersonnelView, \
    OrganizationCreateEmplacementView, \
    OrganizationCreateAssociationView


urlpatterns = [
    url(r'^view/(?P<slug>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$',
        OrganizationDetail.as_view(),
        name="view-organization"),
    url(r'name/autocomplete',
        organization_autocomplete,
        name="organization-autocomplete"),
    url(r'edit/(?P<slug>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$',
        OrganizationEditBasicsView.as_view(),
        name='edit-organization'),
    url(r'create/$',
        OrganizationCreateBasicsView.as_view(),
        name='create-organization'),
    url(r'edit/compositions/(?P<organization_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/(?P<pk>\d+)/$',
        OrganizationEditCompositionView.as_view(),
        name='edit-organization-composition'),
    url(r'create/compositions/(?P<organization_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$',
        OrganizationCreateCompositionView.as_view(),
        name='create-organization-composition'),
    url(r'edit/personnel/(?P<organization_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/(?P<pk>\d+)/$',
        OrganizationEditPersonnelView.as_view(),
        name='edit-organization-personnel'),
    url(r'create/personnel/(?P<organization_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$',
        OrganizationCreatePersonnelView.as_view(),
        name='create-organization-personnel'),
    url(r'edit/emplacement/(?P<organization_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/(?P<pk>\d+)/$',
        OrganizationEditEmplacementView.as_view(),
        name='edit-organization-emplacement'),
    url(r'create/emplacement/(?P<organization_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$',
        OrganizationCreateEmplacementView.as_view(),
        name='create-organization-emplacement'),
    url(r'edit/association/(?P<organization_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/(?P<pk>\d+)/$',
        OrganizationEditAssociationView.as_view(),
        name='edit-organization-association'),
    url(r'create/association/(?P<organization_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$',
        OrganizationCreateAssociationView.as_view(),
        name='create-organization-association'),
]
