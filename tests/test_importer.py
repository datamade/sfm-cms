import os
import csv
import io
import collections

import pytest
from django.core.management import call_command

from organization.models import Organization
from person.models import Person
from personextra.models import PersonExtra
from personbiography.models import PersonBiography
from violation.models import Violation
from source.models import Source, AccessPoint


@pytest.fixture(scope='module')
def data_folder():
    """The directory where importer fixture data is stored."""
    return 'tests/fixtures/importer'


@pytest.fixture
def mock_utils_geo_functions(mocker):
    """
    Mock out the geography functions in sfm_pc.utils so that we don't need
    OSM data in order to test the data import.
    """
    feature = collections.namedtuple(
        'OSMFeature',
        ('id', 'name', 'geometry', 'country_code', 'feature_type', 'st_x', 'st_y', 'tags')
    )(12345, 'Test Location', 'POINT(1 1)', 'mx', 'point', 1, 1, 'Test Location tags')

    mock_get_osm_by_id = mocker.patch('sfm_pc.utils.get_osm_by_id')
    mock_get_osm_by_id.return_value = feature

    mock_get_hierarchy_by_id = mocker.patch('sfm_pc.utils.get_hierarchy_by_id')
    mock_get_hierarchy_by_id.return_value = []

    geofunc = collections.namedtuple('GeoFunctions', ('get_osm_by_id', 'get_hierarchy_by_id'))
    return geofunc(mock_get_osm_by_id, mock_get_hierarchy_by_id)


@pytest.fixture
def data_import(data_folder, mock_utils_geo_functions):
    """Perform a test data import."""
    output = io.StringIO()
    call_command('import_google_doc', folder=data_folder, stdout=output)
    return output


@pytest.mark.django_db
def test_no_sources_missing(data_import):
    assert 'does not have sources' not in data_import.getvalue()
    assert 'has no confidence' not in data_import.getvalue()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'entity_name,Model',
    [
        ('units', Organization), ('persons', Person),
        ('persons_extra', (PersonExtra, PersonBiography)),
        ('incidents', Violation), ('sources', AccessPoint)
    ]
)
def test_number_of_imported_entities(entity_name, Model, data_import, data_folder):
    with open(os.path.join(data_folder, entity_name + '.csv')) as fobj:
        reader = csv.DictReader(fobj)
        raw_records = list(reader)
        # Exclude entities with a non-final status
        if entity_name in ('units', 'persons', 'incidents'):
            status_field = entity_name[:-1] + ':status:admin'
            comments_field = entity_name[:-1] + ':comments:admin'
            num_raw_records = sum(
                1 for rec in raw_records
                if rec[status_field] == '3' and 'duplicate' not in rec[comments_field].lower()
            )
        else:
            num_raw_records = len(raw_records)
    if type(Model) == tuple:
        num_records = sum(Mod.objects.count() for Mod in Model)
    else:
        num_records = Model.objects.count()
    assert num_records == num_raw_records


@pytest.mark.django_db
def test_sources(data_import, data_folder):
    """
    All records in the source data should have their own sources. Check all
    attributes of all entities and confirm that each has its own source.
    """
    src_related_attrs = [attr for attr in dir(AccessPoint.objects.first())
                         if attr.endswith('_related')]
    for access_point in AccessPoint.objects.all():
        related_objects = []
        for attr in src_related_attrs:
            related_objects += [obj for obj in getattr(access_point, attr).all()
                                if obj]
        related_obj_types = set(obj._meta.object_name for obj in related_objects)
        if len(related_obj_types) > 1:
            # Object types that we expect may share sources
            permitted_org_set = set([
                'CompositionChild', 'OrganizationName',
                'MembershipOrganizationMember', 'MembershipOrganizationOrganization',
                'MembershipPersonOrganization', 'MembershipPersonMember',
                'CompositionParent',
            ])
            permitted_person_set = set(['PersonName'])
            permitted_incident_set = set([
                'ViolationStartDate', 'ViolationStatus', 'ViolationType',
                'ViolationFirstAllegation', 'ViolationDescription',
                'ViolationEndDate', 'ViolationLastUpdate',
                'ViolationPerpetratorClassification'
            ])
            permitted_country_set = set([
                'OrganizationDivisionId', 'PersonDivisionId'
            ])
            assert any([
                related_obj_types.issubset(permitted_org_set),
                related_obj_types.issubset(permitted_person_set),
                related_obj_types.issubset(permitted_incident_set),
                related_obj_types.issubset(permitted_country_set)
            ])


@pytest.mark.django_db
def test_source_dates_and_timestamps(data_import):
    """Make sure Source date fields properly parse dates and timestamps."""
    timestamp_src = Source.objects.get(title='Source Timestamps')
    date_src = Source.objects.get(title='Source Dates')
    date_and_timestamp_prefixes = ('created', 'published', 'uploaded')
    for prefix in date_and_timestamp_prefixes:
        date_field = '{}_date'.format(prefix)
        timestamp_field = '{}_timestamp'.format(prefix)
        assert getattr(date_src, date_field)
        assert not getattr(date_src, timestamp_field)
        assert not getattr(timestamp_src, date_field)
        assert getattr(timestamp_src, timestamp_field)


@pytest.mark.django_db
def test_incidents(data_import, mock_utils_geo_functions):
    """Test some properties of imported Incidents."""
    # Make sure the full description gets rendered
    semicolon_incident = Violation.objects.first()
    semicolon_description = semicolon_incident.description.get_value().value
    assert len(semicolon_description.split(';')) == 2

    # Make sure perpetrator classifications get parsed correctly
    assert len(semicolon_incident.perpetratorclassification.get_list()) == 2

    # Check geometry fields
    expected_geo = mock_utils_geo_functions.get_osm_by_id.return_value
    assert semicolon_incident.adminlevel1.get_value() is None
    assert semicolon_incident.adminlevel2.get_value().value.id == expected_geo.id


@pytest.mark.django_db
def test_relationships(data_import):
    """Make sure the correct relationships between entities get imported."""
    # Test org compositions
    org_nodes = ('Alpha', 'Beta', 'Gamma', 'Delta')
    org_edges = (None, 'Alpha', 'Beta', 'Gamma')
    for node, edge in zip(org_nodes, org_edges):
        org = Organization.objects.get(
            # Orgs in the source data have trailing spaces in their names
            organizationname__value='Importer Test Organization {} Name '.format(node)
        )
        if edge:
            assert org.parent_organization.count() == 1
            expected_parent_name = 'Importer Test Organization {} Name '.format(edge)
            parent_org = org.parent_organization.first().object_ref.parent.get_value().value
            assert parent_org.name.get_value().value == expected_parent_name
        else:
            assert org.parent_organization.count() == 0
            assert org.child_organization.count() == 1

    # Test org memberships
    is_member_org = Organization.objects.get(
        organizationname__value='Is-member Organization name'
    )
    has_member_org = Organization.objects.get(
        organizationname__value='Has-member Organization name'
    )
    assert is_member_org.membershiporganizationmember_set.count() == 1
    assert has_member_org.membershiporganizationorganization_set.count() == 1

    membership = is_member_org.membershiporganizationmember_set.first().object_ref
    member_org = membership.organization.get_value().value
    assert member_org == has_member_org

    # Test chain of command
    person_nodes = org_nodes
    person_edges = person_nodes
    for node, edge in zip(person_nodes, person_edges):
        person = Person.objects.get(
            personname__value='Importer Test Person {} Name'.format(node)
        )
        assert person.memberships.count() == 1
        member_org = person.memberships.first().object_ref.organization.get_value().value
        expected_org_name = 'Importer Test Organization {} Name '.format(edge)
        assert member_org.name.get_value().value == expected_org_name
