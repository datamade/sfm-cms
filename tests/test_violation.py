import pytest

from django.test import TestCase, Client
from django.core.urlresolvers import reverse_lazy
from django.db import connection
from django.core.management import call_command
from django.contrib.auth.models import User

from source.models import AccessPoint
from person.models import Person
from organization.models import Organization
from violation.models import Violation, ViolationType, \
    ViolationPerpetratorClassification


@pytest.fixture
def expected_entity_names(location_adminlevel1,
                          location_adminlevel2,
                          violation,
                          location_node,
                          people,
                          organizations):
    """
    Generate a list of related entity names that we expect to see in the
    DeleteView.
    """
    return [
        location_adminlevel1.name,
        location_adminlevel2.name,
        location_node.name,
    ] + [
        person.name.get_value().value for person in people
    ] + [
        org.name.get_value().value for org in organizations
    ]


@pytest.mark.django_db
def test_violation_related_entities(violation, expected_entity_names):
    related_entities = violation.related_entities
    assert len(related_entities) == len(expected_entity_names)
    assert set([entity['name'] for entity in related_entities]) == set(expected_entity_names)


@pytest.mark.django_db
def test_view_violation(client, violation):

    response = client.get(reverse_lazy('view-violation', args=[violation.uuid]))

    assert response.status_code == 200


@pytest.mark.django_db
def test_create_violation(setUp,
                          new_access_points,
                          new_people,
                          new_organizations,
                          fake_signal):

    types = ['Violation against freedom from torture']
    perpetrators = [p.id for p in new_people]
    perpetratororganizations = [o.id for o in new_organizations]
    perpetratorclassification = 'Real bad guys'

    create_url = reverse_lazy('create-violation')
    get_response = setUp.get(create_url)
    assert get_response.status_code == 200

    new_source_ids = [s.uuid for s in new_access_points]
    post_data = {
        'division_id': 'ocd-division/country:us',
        'startdate': '1976',
        'enddate': '2012-02-14',
        'types': types,
        'perpetrator': perpetrators,
        'perpetratororganization': perpetratororganizations,
        'perpetratorclassification': perpetratorclassification,
        'description': 'Test violation description',
        'description_source': new_source_ids,
    }

    post_response = setUp.post(create_url, post_data)
    assert post_response.status_code == 302

    violation = Violation.objects.last()
    assert set(new_source_ids) <= {s.uuid for s in violation.description.get_sources()}

    assert violation.division_id.get_value().value == 'ocd-division/country:us'
    assert str(violation.startdate.get_value().value) == '1976'
    assert str(violation.enddate.get_value().value) == '14th February 2012'
    assert types[0] in [v.get_value().value for v in violation.types.get_list()]
    assert violation.perpetratorclassification.get_list()[0].get_value().value == perpetratorclassification

    saved_perp_list = [p.get_value().value for p in violation.perpetrator.get_list()]
    for person in new_people:
        assert person in saved_perp_list

    fake_signal.assert_called_with(object_id=str(violation.uuid), sender=Violation)


@pytest.mark.django_db
def test_edit_violation(setUp,
                        violation,
                        new_access_points,
                        new_people,
                        new_organizations,
                        fake_signal):

    new_types = ['Violation against freedom from torture']

    perpetrators = [p.id for p in new_people]
    perpetratororganizations = [o.id for o in new_organizations]
    perpetratorclassification = 'Real bad guys'

    response = setUp.get(reverse_lazy('edit-violation', kwargs={'slug': violation.uuid}))

    assert response.status_code == 200

    new_source_ids = [s.uuid for s in new_access_points]

    post_data = {
        'division_id': 'ocd-division/country:us',
        'startdate': '1976',
        'enddate': '2012-02-14',
        'types': new_types,
        'perpetrator': perpetrators,
        'perpetratororganization': perpetratororganizations,
        'perpetratorclassification': perpetratorclassification,
        'description': violation.description.get_value().value,
        'description_source': new_source_ids,
    }

    response = setUp.post(reverse_lazy('edit-violation', kwargs={'slug': violation.uuid}), post_data)

    assert response.status_code == 302

    assert set(new_source_ids) <= {s.uuid for s in violation.description.get_sources()}

    assert violation.division_id.get_value().value == 'ocd-division/country:us'
    assert str(violation.startdate.get_value().value) == '1976'
    assert str(violation.enddate.get_value().value) == '14th February 2012'
    assert new_types[0] in [v.get_value().value for v in violation.types.get_list()]
    assert violation.perpetratorclassification.get_list()[0].get_value().value == perpetratorclassification

    for person in new_people:
        assert person in [p.get_value().value for p in violation.perpetrator.get_list()]

    fake_signal.assert_called_with(object_id=violation.uuid, sender=Violation)


@pytest.mark.django_db
def test_delete_violation(setUp, violation):
    url = reverse_lazy('delete-violation', args=[violation.uuid])
    response = setUp.post(url)

    assert response.status_code == 302

    with pytest.raises(Violation.DoesNotExist):
        Violation.objects.get(uuid=violation.uuid)


@pytest.mark.django_db
def test_delete_violation_view_with_related_entities(setUp, violation, expected_entity_names):
    url = reverse_lazy('delete-violation', args=[violation.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure all the related entities are rendered on the page.
    for entity_name in expected_entity_names:
        assert entity_name in response.content.decode('utf-8')
    # Make sure that the confirm button is disabled.
    assert 'value="Confirm" disabled' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_delete_violation_view_no_related_entities(setUp, violation, mocker):
    mocker.patch('violation.models.Violation.related_entities', new=[])
    url = reverse_lazy('delete-violation', args=[violation.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure no related entities are rendered on the page.
    assert 'Related entities' not in response.content.decode('utf-8')
    # Make sure that the confirm button is enabled.
    assert 'disabled' not in response.content.decode('utf-8')


@pytest.mark.django_db
def test_edit_violation_locations(setUp,
                                  violation,
                                  location_node,
                                  location_adminlevel1,
                                  location_adminlevel2,
                                  fake_signal):
    # Make sure we can load the locations edit view.
    get_response = setUp.get(reverse_lazy(
        'edit-violation-locations',
        kwargs={'slug': violation.uuid}
    ))
    assert get_response.status_code == 200

    # Test adding locations.
    post_data = {
        'locationdescription': 'Foo bar baz',
        'location': location_node.id,
        'adminlevel1': location_adminlevel1.id,
        'adminlevel2': location_adminlevel2.id,
    }

    post_response = setUp.post(
        reverse_lazy('edit-violation-locations', kwargs={'slug': violation.uuid}),
        post_data
    )
    assert post_response.status_code == 302

    assert violation.location.get_value().value == location_node
    assert violation.adminlevel1.get_value().value == location_adminlevel1
    assert violation.adminlevel2.get_value().value == location_adminlevel2

    fake_signal.assert_called_with(object_id=violation.uuid, sender=Violation)


@pytest.mark.django_db
def test_change_perpetrator_classification(setUp,
                                           people,
                                           organizations,
                                           new_access_points,
                                           fake_signal):

    response = setUp.get(reverse_lazy('create-violation'))

    assert response.status_code == 200

    new_source_ids = [s.uuid for s in new_access_points][:-1]

    new_types = ['Violation against freedom from torture']

    perpetrators = [p.id for p in people]
    perpetratororganizations = [o.id for o in organizations]

    new_classifications = ['Bad', 'Guys']

    post_data = {
        'division_id': 'ocd-division/country:us',
        'division_id_source': new_source_ids,
        'startdate': '1976',
        'startdate_source': new_source_ids,
        'enddate': '2012-02-14',
        'enddate_source': new_source_ids,
        'types': new_types,
        'types_source': new_source_ids,
        'perpetrator': perpetrators,
        'perpetrator_source': new_source_ids,
        'perpetratororganization': perpetratororganizations,
        'perpetratororganization_source': new_source_ids,
        'perpetratorclassification': new_classifications,
        'perpetratorclassification_source': new_source_ids,
        'description': 'Some real scary stuff',
        'description_source': new_source_ids,
    }

    response = setUp.post(reverse_lazy('create-violation'), post_data)

    assert response.status_code == 302

    violation = Violation.objects.get(violationdescription__value='Some real scary stuff')

    assert set(new_source_ids) <= {s.uuid for s in violation.description.get_sources()}

    assert violation.division_id.get_value().value == 'ocd-division/country:us'
    assert str(violation.startdate.get_value().value) == '1976'
    assert str(violation.enddate.get_value().value) == '14th February 2012'
    assert new_types[0] in [v.get_value().value for v in violation.types.get_list()]
    assert set([clsif.get_value().value for clsif in violation.perpetratorclassification.get_list()]) == set(new_classifications)

    for person in people:
        assert person in [p.get_value().value for p in violation.perpetrator.get_list()]

    fake_signal.assert_called_with(object_id=str(violation.uuid), sender=Violation)

    post_data = {
        'perpetratorclassification': 'More baddies',
        'perpetratorclassification_source': new_access_points[-1].uuid,
        'description': 'Some real scary stuff',
        'description_source': new_source_ids,
    }

    response = setUp.post(reverse_lazy('edit-violation', kwargs={'slug': violation.uuid}), post_data)

    assert response.status_code == 302

    assert len(violation.perpetratorclassification.get_list()) == 1
    assert violation.perpetratorclassification.get_list()[0].get_value().value == 'More baddies'

    fake_signal.assert_called_with(object_id=violation.uuid, sender=Violation)
