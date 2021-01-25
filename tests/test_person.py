from uuid import uuid4

import pytest

from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.models import User
from django.db.models import Count
from django.template.defaultfilters import truncatewords

from source.models import AccessPoint
from person.models import Person
from person.views import get_commanders
from organization.models import Organization
from membershipperson.models import MembershipPerson, Rank, Role
from tests.conftest import is_tab_active


@pytest.fixture
def expected_entity_names(violation,
                          membership_person):
    """
    Generate a list of related entity names that we expect to see in the
    Person DeleteView.
    """
    return [
        membership_person[0].organization.get_value().value.name.get_value().value,
        truncatewords(violation.description.get_value(), 10),
    ]


@pytest.mark.django_db
def test_person_related_entities(people, expected_entity_names):
    person = people[0]
    related_entities = person.related_entities
    assert len(related_entities) == len(expected_entity_names)
    assert set([entity['name'] for entity in related_entities]) == set(expected_entity_names)


@pytest.mark.django_db
def test_view_person(setUp, people):

    for person in people:
        response = setUp.get(reverse_lazy('view-person', args=[person.uuid]))
        assert response.status_code == 200


@pytest.mark.django_db
def test_edit_person(setUp, people, new_access_points, fake_signal):
    person = people[0]

    response = setUp.get(reverse_lazy('edit-person', kwargs={'slug': person.uuid}))

    assert response.status_code == 200

    new_source_ids = [s.uuid for s in new_access_points]

    post_data = {
        'name': person.name.get_value(),
        'name_source': [s.uuid for s in person.name.get_sources()],
        'name_confidence': '2',
        'aliases': [p.get_value().id for p in person.aliases.get_list()] + ['Foo'],
        'aliases_source': new_source_ids + [s.uuid for s in person.aliases.get_list()[0].get_sources()],
        'aliases_confidence': '2',
        'division_id': 'ocd-division/country:us',
        'division_id_source': new_source_ids + [s.uuid for s in person.division_id.get_sources()],
        'division_id_confidence': '3',
        'date_of_birth': '1976',
        'date_of_birth_source': new_source_ids,
        'date_of_birth_confidence': '1',
        'date_of_death': '2012-02-14',
        'date_of_death_source': new_source_ids,
        'date_of_death_confidence': '3',
        'deceased': True,
        'deceased_source': new_source_ids,
        'deceased_confidence': '3',
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 302

    assert 'Foo' in [p.get_value().value for p in person.aliases.get_list()]

    for alias in person.aliases.get_list():
        assert set(new_source_ids) <= {a.uuid for a in alias.get_sources()}

    assert person.division_id.get_value().value == 'ocd-division/country:us'
    assert person.name.get_value().confidence == '2'
    assert person.aliases.get_list()[0].get_value().confidence == '2'
    assert person.division_id.get_value().confidence == '3'

    # TODO: Test PersonExtra and PersonBiography fields

    fake_signal.assert_called_with(object_id=person.uuid, sender=Person)


@pytest.mark.django_db
def test_delete_person(setUp, people):
    person = people[0]
    url = reverse_lazy('delete-person', args=[person.uuid])
    response = setUp.post(url)

    assert response.status_code == 302

    with pytest.raises(Person.DoesNotExist):
        Person.objects.get(uuid=person.uuid)


@pytest.mark.django_db
def test_delete_person_view_with_related_entities(setUp, people, expected_entity_names):
    person = people[0]
    url = reverse_lazy('delete-person', args=[person.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure all the related entities are rendered on the page.
    for entity_name in expected_entity_names:
        assert entity_name in response.content.decode('utf-8')
    # Make sure that the confirm button is disabled.
    assert 'value="Confirm" disabled' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_delete_person_view_no_related_entities(setUp, people):
    person = people[0]
    url = reverse_lazy('delete-person', args=[person.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure no related entities are rendered on the page.
    assert 'Related entities' not in response.content.decode('utf-8')
    # Make sure that the confirm button is enabled.
    assert 'disabled' not in response.content.decode('utf-8')


@pytest.mark.django_db
def test_publish_unpublish_person(setUp, people, fake_signal):
    person = people[0]

    post_data = {
        'name': person.name.get_value(),
        'name_source': [s.uuid for s in person.name.get_sources()],
        'published': 'on',
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 302

    person.refresh_from_db()
    assert person.published

    fake_signal.assert_called_with(object_id=person.uuid, sender=Person)

    post_data = {
        'name': person.name.get_value(),
        'name_source': [s.uuid for s in person.name.get_sources()],
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    person.refresh_from_db()
    assert not person.published

    fake_signal.assert_called_with(object_id=person.uuid, sender=Person)


@pytest.mark.django_db
def test_no_source_one_value(setUp, base_people):
    person = base_people[0]

    post_data = {
        'name': person.name.get_value().value,
        'notes': person.name.get_value().value + ' Foo',
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 200

    assert 'This field now has a value so it requires sources' in response.context['form'].errors['notes']


@pytest.mark.django_db
def test_no_source_multiple_value(setUp, base_people):
    person = base_people[0]

    post_data = {
        'aliases': ['Foo', 'Bar'],
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 200

    assert 'This field has new values so it requires sources' in response.context['form'].errors['aliases']
    assert 'This field is required.' in response.context['form'].errors['name']

    assert 'Foo' not in [p.get_value().value for p in person.aliases.get_list()]
    assert 'Bar' not in [p.get_value().value for p in person.aliases.get_list()]


@pytest.mark.django_db
def test_no_source_one_new_value(setUp, people):
    person = people[0]

    post_data = {
        'aliases': [p.get_value().id for p in person.aliases.get_list()] + ['Foo'],
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 200

    assert 'This field has new values so it requires sources' in response.context['form'].errors['aliases']
    assert 'This field is required.' in response.context['form'].errors['name']

    assert 'Foo' not in [p.get_value().value for p in person.aliases.get_list()]


@pytest.mark.django_db
def test_no_source_empty_start(setUp, base_people):
    person = base_people[0]
    sources = [s.uuid for s in person.name.get_sources()]

    post_data = {
        'name': person.name.get_value().value,
        'name_source': sources,
        'aliases': person.name.get_value(),
    }

    response = setUp.post(reverse_lazy('edit-person',
                                       kwargs={'slug': person.uuid}),
                          post_data)

    assert response.status_code == 200

    assert 'This field has new values so it requires sources' in response.context['form'].errors['aliases']


@pytest.mark.django_db
def test_remove_value(setUp, people, fake_signal):
    person = people[0]

    aliases = [a.get_value().id for a in person.aliases.get_list()]
    removed = aliases.pop()

    post_data = {
        'name': person.name.get_value().value,
        'name_source': [s.uuid for s in person.name.get_sources()],
        'aliases': aliases,
        'aliases_source': [s.uuid for s in person.aliases.get_list()[0].get_sources()],
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 302

    assert aliases == [a.get_value().id for a in person.aliases.get_list()]

    fake_signal.assert_called_with(object_id=person.uuid, sender=Person)


@pytest.mark.django_db
def test_remove_value_same_sources(setUp, people, fake_signal):
    person = people[1]

    aliases = [a.get_value().id for a in person.aliases.get_list()]
    removed = aliases.pop()

    sources = set()

    for alias in person.aliases.get_list():
        for source in alias.get_sources():
            sources.add(source.uuid)

    post_data = {
        'name': person.name.get_value().value,
        'name_source': list(sources),
        'aliases': aliases,
        'aliases_source': list(sources),
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 302

    assert aliases == [a.get_value().id for a in person.aliases.get_list()]

    fake_signal.assert_called_with(object_id=person.uuid, sender=Person)


@pytest.mark.django_db
def test_remove_all_values(setUp, people, fake_signal):
    person = people[2]

    sources = [s.uuid for s in person.name.get_sources()]

    post_data = {
        'name': person.name.get_value().value,
        'name_source': sources,
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 302

    assert person.aliases.get_list() == []

    fake_signal.assert_called_with(object_id=person.uuid, sender=Person)


@pytest.mark.django_db
def test_duplicate_source(setUp, people, fake_signal):
    person = people[0]

    sources = [s.uuid for s in person.name.get_sources()]

    post_data = {
        'name': person.name.get_value().value,
        'name_source': sources + sources,
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 302

    assert len(person.name.get_sources()) == len(sources)
    fake_signal.assert_called_with(object_id=person.uuid, sender=Person)


@pytest.mark.django_db
def test_just_add_source(setUp, people, new_access_points, fake_signal):
    person = people[0]
    new_source = new_access_points[0]

    post_data = {
        'name': person.name.get_value().value,
        'name_source': [new_source.uuid],
    }

    response = setUp.post(reverse_lazy('edit-person', kwargs={'slug': person.uuid}), post_data)

    assert response.status_code == 302

    assert new_source in person.name.get_sources()
    fake_signal.assert_called_with(object_id=person.uuid, sender=Person)


@pytest.mark.django_db
def test_new_sources_required(setUp, base_people):
    person = base_people[1]
    sources = [s.uuid for s in person.name.get_sources()]

    post_data = {
        'name': person.name.get_value().value + ' Foo',
        'name_source': sources,
    }

    response = setUp.post(reverse_lazy('edit-person',
                                       kwargs={'slug': person.uuid}),
                          post_data)

    assert response.status_code == 200

    assert 'This field changed so it requires sources' in response.context['form'].errors['name']


@pytest.mark.django_db
def test_new_sources_required_multi(setUp, people):
    person = people[1]
    sources = [s.uuid for s in person.name.get_sources()]

    post_data = {
        'name': person.name.get_value().value,
        'name_source': sources,
        'aliases': [a.get_value().id for a in person.aliases.get_list()] + ['Foo'],
        'aliases_source': [s.uuid for s in person.aliases.get_list()[0].get_sources()],
        'gender': '',
    }

    response = setUp.post(reverse_lazy('edit-person',
                                       kwargs={'slug': person.uuid}),
                          post_data)

    assert response.status_code == 200

    assert 'This field has new values so it requires sources' in response.context['form'].errors['aliases']


@pytest.mark.django_db
def test_edit_posting(setUp,
                      membership_person,
                      new_access_points,
                      new_organizations,
                      fake_signal):

    membership = membership_person[0]
    person = membership.member.get_value().value
    response = setUp.get(reverse_lazy('edit-person-postings',
                                      kwargs={'person_id': person.uuid,
                                              'pk': membership.id}))

    assert response.status_code == 200

    sources = [s for s in membership.organization.get_sources()]

    new_source = new_access_points[0]

    new_organization = new_organizations[0]
    new_rank = Rank.objects.create(value='New Commander')
    new_role = Role.objects.create(value='New Honcho')

    post_data = {
        'member': person.id,
        'organization': new_organization.id,
        'organization_source': [new_source.uuid],
        'rank': new_rank.id,
        'rank_source': [new_source.uuid],
        'role': new_role.id,
        'role_source': [new_source.uuid],
        'title': 'Floober',
        'title_source': [new_source.uuid],
        'firstciteddate': '2007',
        'firstciteddate_source': [new_source.uuid],
        'lastciteddate': 'April 2012',
        'lastciteddate_source': [new_source.uuid],
        'realstart': True,
        'realstart_source': [new_source.uuid],
        'startcontext': 'Floop de doop',
        'startcontext_source': [new_source.uuid]
    }

    response = setUp.post(reverse_lazy('edit-person-postings',
                                       kwargs={'person_id': person.uuid,
                                               'pk': membership.id}),
                          post_data)

    assert response.status_code == 302

    assert membership.organization.get_value().value.uuid == new_organization.uuid
    assert new_source in membership.organization.get_sources()
    assert membership.rank.get_value().value == new_rank
    assert membership.role.get_value().value == new_role

    fake_signal.assert_called_with(object_id=membership.id,
                                   sender=MembershipPerson)


@pytest.mark.django_db
def test_boolean_none_to_true(setUp, membership_person, new_access_points, fake_signal):
    membership = membership_person[1]
    person = membership.member.get_value().value

    new_source = new_access_points[2]

    post_data = {
        'member': person.id,
        'organization': membership.organization.get_value().value.id,
        'organization_source': [str(s.uuid) for s in membership.organization.get_sources()],
        'realstart': 'on',
        'realstart_source': [new_source.uuid],
    }

    response = setUp.post(reverse_lazy('edit-person-postings',
                                       kwargs={'person_id': person.uuid,
                                               'pk': membership.id}),
                          post_data)

    assert response.status_code == 302

    assert membership.realstart.get_value().value == True

    fake_signal.assert_called_with(object_id=membership.id,
                                   sender=MembershipPerson)


@pytest.mark.django_db
def test_boolean_true_to_false(setUp, membership_person, new_access_points, fake_signal):
    membership = membership_person[1]
    person = membership.member.get_value().value

    new_source = new_access_points[1]

    post_data = {
        'member': person.id,
        'organization': membership.organization.get_value().value.id,
        'organization_source': [str(s.uuid) for s in membership.organization.get_sources()],
        'realstart_source': [new_source.uuid],
    }

    response = setUp.post(reverse_lazy('edit-person-postings',
                                       kwargs={'person_id': person.uuid,
                                               'pk': membership.id}),
                          post_data)

    assert response.status_code == 302

    assert membership.realstart.get_value().value == False

    fake_signal.assert_called_with(object_id=membership.id,
                                   sender=MembershipPerson)


@pytest.mark.django_db
def test_boolean_false_to_true(setUp, membership_person, fake_signal):
    membership = membership_person[0]
    person = membership.member.get_value().value

    post_data = {
        'member': person.id,
        'organization': membership.organization.get_value().value.id,
        'organization_source': [str(s.uuid) for s in membership.organization.get_sources()],
        'realend': 'on',
    }

    response = setUp.post(reverse_lazy('edit-person-postings',
                                       kwargs={'person_id': person.uuid,
                                               'pk': membership.id}),
                          post_data)

    assert response.status_code == 302

    assert membership.realend.get_value().value == True

    fake_signal.assert_called_with(object_id=membership.id,
                                   sender=MembershipPerson)


@pytest.mark.django_db
def test_boolean_true_no_sources(setUp, membership_person, fake_signal):
    membership = membership_person[1]
    person = membership.member.get_value().value

    post_data = {
        'member': person.id,
        'organization': membership.organization.get_value().value.id,
        'organization_source': [str(s.uuid) for s in membership.organization.get_sources()],
        'realstart': 'on',
    }

    response = setUp.post(reverse_lazy('edit-person-postings',
                                       kwargs={'person_id': person.uuid,
                                               'pk': membership.id}),
                          post_data)

    assert response.status_code == 302
    assert membership.realstart.get_value().value == True

    fake_signal.assert_called_with(object_id=membership.id,
                                   sender=MembershipPerson)


@pytest.mark.django_db
def test_no_existing_sources(setUp, membership_person):
    membership = membership_person[0]
    person = membership.member.get_value().value

    membership.rank.get_value().sources.set([])
    membership.rank.get_value().accesspoints.set([])

    post_data = {
        'member': person.id,
        'organization': membership.organization.get_value().value.id,
        'organization_source': [str(s.uuid) for s in membership.organization.get_sources()],
        'rank': membership.rank.get_value().value.id,
    }

    response = setUp.post(reverse_lazy('edit-person-postings',
                                       kwargs={'person_id': person.uuid,
                                               'pk': membership.id}),
                          post_data)

    assert response.status_code == 200
    assert 'Please add some sources to this field' in response.context['form'].errors['rank']


@pytest.mark.django_db
def test_create_person(setUp, new_access_points, fake_signal):

    response = setUp.get(reverse_lazy('create-person'))

    assert response.status_code == 200

    new_source_ids = [s.uuid for s in new_access_points]

    post_data = {
        'name': 'Someone Something',
        'name_source': new_source_ids,
        'aliases': ['Foo', 'Bar', 'Baz'],
        'aliases_source': new_source_ids,
        'division_id': 'ocd-division/country:us',
        'division_id_source': new_source_ids,
        'date_of_birth': '1976',
        'date_of_birth_source': new_source_ids,
        'date_of_death': '2012-02-14',
        'date_of_death_source': new_source_ids,
        'deceased': True,
        'deceased_source': new_source_ids,
    }

    response = setUp.post(reverse_lazy('create-person'), post_data)

    assert response.status_code == 302

    person = Person.objects.get(personname__value='Someone Something')

    assert 'Foo' in [p.get_value().value for p in person.aliases.get_list()]

    assert person.division_id.get_value().value == 'ocd-division/country:us'

    # TODO: Test PersonExtra/PersonBiography models

    fake_signal.assert_called_with(object_id=str(person.uuid), sender=Person)


@pytest.mark.django_db
def test_create_posting(setUp,
                        people,
                        new_access_points,
                        new_organizations,
                        fake_signal):

    person = people[0]

    response = setUp.get(reverse_lazy('create-person-posting',
                                      kwargs={'person_id': person.uuid}))

    assert response.status_code == 200
    assert "<h2>Add posting</h2>" in response.content.decode('utf-8')

    sources = [s for s in person.name.get_sources()]

    new_source = new_access_points[0]

    new_organization = new_organizations[0]
    new_rank = Rank.objects.create(value='New Commander')
    new_role = Role.objects.create(value='New Honcho')

    post_data = {
        'member': person.id,
        'organization': new_organization.id,
        'organization_source': [new_source.uuid],
        'rank': new_rank.id,
        'rank_source': [new_source.uuid],
        'role': new_role.id,
        'role_source': [new_source.uuid],
        'title': 'Floober',
        'title_source': [new_source.uuid],
        'firstciteddate': '2007',
        'firstciteddate_source': [new_source.uuid],
        'lastciteddate': 'April 2012',
        'lastciteddate_source': [new_source.uuid],
        'realstart': True,
        'realstart_source': [new_source.uuid],
        'startcontext': 'Floop de doop',
        'startcontext_source': [new_source.uuid]
    }

    response = setUp.post(reverse_lazy('create-person-posting',
                                       kwargs={'person_id': person.uuid}),
                          post_data)

    assert response.status_code == 302

    membership = MembershipPerson.objects.get(membershippersontitle__value='Floober')

    assert membership.organization.get_value().value.uuid == new_organization.uuid
    assert new_source in membership.organization.get_sources()
    assert membership.rank.get_value().value == new_rank
    assert membership.role.get_value().value == new_role

    fake_signal.assert_called_with(object_id=membership.id,
                                   sender=MembershipPerson)


@pytest.mark.django_db
def test_person_edit_buttons(setUp, people, membership_person):
    assert is_tab_active(setUp.get(reverse_lazy('edit-person', args=[people[0].uuid])),
                         'Basics')
    assert is_tab_active(setUp.get(reverse_lazy('create-person-posting', args=[people[0].uuid])),
                         'Postings')
    assert is_tab_active(
        setUp.get(
            reverse_lazy(
                'edit-person-postings',
                args=[people[0].uuid, membership_person[0].pk]
            )
        ),
        'Postings')


@pytest.mark.django_db
def test_get_commanders_ignores_title(setUp, access_points, people, membership_person, organizations, composition):
    """
    get_commanders() should ignore memberships that are identical except for
    title. Use the fact that we set up such a membership in the membership_person
    fixture to test to make sure get_commanders() only returns one commander.
    """
    person_id = people[0].uuid
    child_compositions = composition[0].parent.get_value().value.child_organization.all()
    commanders = get_commanders(None, None, child_compositions, person_id)
    assert len(commanders) == 1
