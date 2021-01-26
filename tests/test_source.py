import json
from uuid import uuid4

import pytest

from django.test import TestCase, Client
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db import connection
from django.core.management import call_command
from django.db.models import Count

from reversion.models import Version

from source.models import Source, AccessPoint
from person.models import Person


@pytest.mark.django_db
def test_create_source(setUp):

    response = setUp.get(reverse_lazy('create-source'), follow=True)
    assert response.status_code == 200

    post_data = {
        'publication': 'Test Publication Title',
        'publication_country': 'Nigeria',
        'title': 'Test Source Title',
        'source_url': 'http://test.com/',
        'published_on': '2014-01-01',
        'comment': 'Test change',
        'uuid': str(uuid4()),
    }

    response = setUp.post(reverse_lazy('create-source'), post_data, follow=True)
    assert response.status_code == 200

    source = Source.objects.get(publication='Test Publication Title')

    assert source.title == post_data['title']
    assert source.source_url == post_data['source_url']

    revision = Version.objects.get_for_object(source).first().revision
    assert revision.comment == 'Test change'


@pytest.mark.django_db
def test_create_accesspoint(setUp, sources):
    source = sources[0]

    response = setUp.get(reverse_lazy('add-access-point',
                                            kwargs={'source_id': str(source.uuid)}))

    assert response.status_code == 200

    post_data = {
        'archive_url': 'https://web.archive.org/',
        'accessed_on': '2018-04-01',
        'page_number': '',
        'comment': 'This is a big change'
    }

    response = setUp.post(reverse_lazy('add-access-point',
                                                kwargs={'source_id': str(source.uuid)}),
                                post_data,
                                follow=True)

    assert response.status_code == 200

    accesspoint = AccessPoint.objects.get(source__uuid=source.uuid,
                                            accessed_on='2018-04-01')

    assert accesspoint.archive_url == 'https://web.archive.org/'

    revision = Version.objects.get_for_object(accesspoint).first().revision
    assert revision.comment == 'This is a big change'


@pytest.mark.django_db
def test_update_source(setUp, sources):
    source = sources[0]

    response = setUp.get(reverse_lazy('update-source', kwargs={'pk': source.uuid}))
    assert response.status_code == 200

    post_data = {
        'publication': 'Test Publication Title',
        'publication_country': source.publication_country,
        'title': source.title,
        'source_url': source.source_url,
        'published_date': source.published_date,
        'comment': 'Test change',
        'uuid': str(source.uuid),
    }

    response = setUp.post(reverse_lazy('update-source', kwargs={'pk': source.uuid}), post_data, follow=True)

    assert response.status_code == 200

    source = Source.objects.get(uuid=source.uuid)

    assert source.publication == 'Test Publication Title'

    revision = Version.objects.get_for_object(source).first().revision
    assert revision.comment == 'Test change'


@pytest.mark.django_db
def test_update_accesspoint(setUp, access_points):
    accesspoint = access_points[0]

    response = setUp.get(reverse_lazy('update-access-point',
                                            kwargs={'source_id': accesspoint.source.uuid,
                                                    'pk': accesspoint.uuid}))
    assert response.status_code == 200

    post_data = {
        'archive_url': 'https://web.archive.org/',
        'accessed_on': '2018-04-01',
        'trigger': accesspoint.trigger,
        'comment': 'This is a big change'
    }

    response = setUp.post(reverse_lazy('update-access-point',
                                            kwargs={'source_id': accesspoint.source.uuid,
                                                    'pk': accesspoint.uuid}),
                                post_data,
                                follow=True)
    assert response.status_code == 200

    accesspoint = AccessPoint.objects.get(uuid=accesspoint.uuid)
    assert accesspoint.archive_url == 'https://web.archive.org/'

    revision = Version.objects.get_for_object(accesspoint).first().revision
    assert revision.comment == 'This is a big change'


@pytest.mark.django_db
def test_autocomplete(setUp):
    url = '{}?q=Nigeria'.format(reverse_lazy('source-autocomplete'))

    response = setUp.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_view_source(setUp, sources, access_points):
    source = sources[0]
    url = reverse_lazy('view-source', args=[source.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    assert 'Select an access point' in response.content.decode('utf-8')
    # Make sure that all of the access points are represented as options on the page
    assert source.accesspoint_set.count() > 0
    for access_point in source.accesspoint_set.all():
        assert str(access_point.uuid) in response.content.decode('utf-8')


@pytest.mark.django_db
def test_view_source_with_evidence(setUp, sources, access_points):
    source = Source.objects.annotate(count=Count('accesspoint')).filter(count__gte=1).first()
    access_point = source.accesspoint_set.first()
    url = reverse_lazy('view-source-with-evidence', args=[source.uuid, access_point.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    assert 'evidences the following entities:' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_view_source_with_no_evidence(setUp, sources):
    source = Source.objects.annotate(count=Count('accesspoint')).filter(count=0).first()
    url = reverse_lazy('view-source', args=[source.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    assert 'No access points found' in response.content.decode('utf-8')


@pytest.fixture
def expected_access_points(setUp, sources):
    source = sources[0]
    return source.accesspoint_set.all()


@pytest.mark.django_db
def test_delete_source(setUp, sources):
    source = sources[0]
    url = reverse_lazy('delete-source', args=[source.uuid])
    response = setUp.post(url)

    assert response.status_code == 302

    with pytest.raises(Source.DoesNotExist):
        Source.objects.get(uuid=source.uuid)


@pytest.mark.django_db
def test_delete_source_view_no_related_entities(setUp, sources):
    source = sources[0]
    url = reverse_lazy('delete-source', args=[source.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure no related entities are rendered on the page.
    assert 'Related entities' not in response.content.decode('utf-8')
    # Make sure that the confirm button is enabled.
    assert 'disabled' not in response.content.decode('utf-8')


@pytest.mark.django_db
def test_delete_source_view_with_related_entities(setUp, sources, access_points, expected_access_points):
    source = sources[0]
    url = reverse_lazy('delete-source', args=[source.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure all the related entities are rendered on the page.
    for entity in expected_access_points:
        assert str(entity) in response.content.decode('utf-8')
    # Make sure that the confirm button is disabled.
    assert 'value="Confirm" disabled' in response.content.decode('utf-8')


@pytest.fixture
def expected_entity_values(organizations):
    expected_entity_values = []
    for org in organizations:
        expected_entity_values += [
            org.name.get_value().value,
            org.division_id.get_value().value,
            org.firstciteddate.get_value().value,
            org.lastciteddate.get_value().value,
        ] + [
            alias.get_value().value for alias in org.aliases.get_list()
        ] + [
            classification.get_value().value for classification in org.classification.get_list()
        ]
    return expected_entity_values


@pytest.mark.django_db
def test_access_point_related_entities(setUp, access_points, expected_entity_values):
    access_point = access_points[0]
    related_entities = access_point.related_entities
    assert len(related_entities) == len(expected_entity_values)
    # Some related entity values are not hashable, so compare lists instead of sets
    related_entity_values = [entity['value'] for entity in related_entities]
    for entity in related_entity_values:
        assert entity in expected_entity_values


@pytest.mark.django_db
def test_delete_access_point(setUp, access_points, searcher_mock, mocker):
    access_point = access_points[0]
    url = reverse_lazy('delete-access-point', args=[access_point.source.uuid, access_point.uuid])
    response = setUp.post(url)

    assert response.status_code == 302

    with pytest.raises(AccessPoint.DoesNotExist):
        AccessPoint.objects.get(uuid=access_point.uuid)

    searcher_mock.assert_not_called()


@pytest.mark.django_db
def test_delete_access_point_view_no_related_entities(setUp, access_points):
    access_point = access_points[0]
    url = reverse_lazy('delete-access-point', args=[access_point.source.uuid, access_point.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure no related entities are rendered on the page.
    assert 'Related entities' not in response.content.decode('utf-8')
    # Make sure that the confirm button is enabled.
    assert 'disabled' not in response.content.decode('utf-8')


@pytest.mark.django_db
def test_delete_access_point_view_with_related_entities(setUp, access_points, expected_entity_values):
    access_point = access_points[0]
    url = reverse_lazy('delete-access-point', args=[access_point.source.uuid, access_point.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure all the related entities are rendered on the page.
    for entity_value in expected_entity_values:
        assert str(entity_value) in response.content.decode('utf-8')
    # Make sure that the confirm button is disabled.
    assert 'value="Confirm" disabled' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_source_with_no_value_raises_error(setUp, people, new_access_points, fake_signal):
    """Make sure the user can't assign a source to an empty field."""
    # Test the CreateView.
    new_source_ids = [s.uuid for s in new_access_points]
    post_data = {
        'name': 'foo',
        'name_source': new_source_ids,
        'aliases_source': new_source_ids  # Add source field without a corresponding value
    }
    create_response = setUp.post(reverse_lazy('create-person'), post_data)
    assert create_response.status_code == 200

    create_form = create_response.context['form']
    assert 'aliases' in create_form.errors.keys()
    assert 'Empty fields should not have sources' in create_form.errors['aliases']

    # Test the EditView.
    edit_response = setUp.post(reverse_lazy('edit-person', args=[people[0].uuid]), post_data)
    assert edit_response.status_code == 200

    edit_form = edit_response.context['form']
    assert 'aliases' in edit_form.errors.keys()
    assert 'Empty fields should not have sources' in edit_form.errors['aliases']
