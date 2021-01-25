import pytest

from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth.models import User
from django.template.defaultfilters import truncatewords

from organization.models import Organization, OrganizationAlias, \
    OrganizationClassification
from membershipperson.models import MembershipPerson, Rank, Role
from source.models import AccessPoint
from composition.models import Composition
from emplacement.models import Emplacement
from association.models import Association
from tests.conftest import is_tab_active


@pytest.fixture
def expected_entity_names(emplacement,
                          association,
                          composition,
                          violation,
                          membership_organization,
                          membership_person):
    """
    Generate a list of related entity names that we expect to see in the
    Organization DeleteView.
    """
    return [
        emplacement[0].site.get_value().value.name,
        association[0].area.get_value().value.name,
        composition[0].child.get_value().value.name.get_value().value,
        truncatewords(violation.description.get_value(), 10),
        membership_organization.organization.get_value().value.name.get_value().value,
        membership_person[0].member.get_value().value.name.get_value().value
    ]


@pytest.mark.django_db
def test_organization_related_entities(organizations, expected_entity_names):
    org = organizations[0]
    related_entities = org.related_entities
    assert len(related_entities) == len(expected_entity_names)
    assert set([entity['name'] for entity in related_entities]) == set(expected_entity_names)


@pytest.mark.django_db
def test_view_organization(full_organizations, client):

    them = Organization.objects.order_by('?')[:10]
    for it in them:
        response = client.get(reverse_lazy('view-organization', args=[it.uuid]))

        assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_edit_organization(save_and_continue,
                           setUp,
                           full_organizations,
                           fake_signal,
                           new_access_points):

    org = Organization.objects.exclude(child_organization__isnull=True,
                                       parent_organization__isnull=True).first()

    response = setUp.get(reverse_lazy('edit-organization', args=[org.uuid]))

    assert response.status_code == 200

    new_source_ids = [s.uuid for s in new_access_points]

    post_data = {
        'name': org.name.get_value().value,
        'name_source': new_source_ids,
        'aliases': [a.get_value().id for a in org.aliases.get_list()] + ['floop'],
        'aliases_source': new_source_ids
    }

    if save_and_continue:
        post_data['_continue'] = True

    response = setUp.post(reverse_lazy('edit-organization', args=[org.uuid]),
                          post_data)

    assert response.status_code == 302

    if save_and_continue:
        assert response.url == reverse_lazy('edit-organization', args=[org.uuid])
    else:
        assert response.url == reverse_lazy('view-organization', args=[org.uuid])

    assert set(new_access_points) <= set(org.name.get_sources())
    assert set(new_access_points) <= set(org.aliases.get_list()[0].get_sources())
    assert 'floop' in [a.get_value().value for a in org.aliases.get_list()]

    fake_signal.assert_called_with(object_id=org.uuid,
                                   sender=Organization)


@pytest.mark.django_db
def test_delete_organization(setUp, organizations):
    org = organizations[0]
    url = reverse_lazy('delete-organization', args=[org.uuid])
    response = setUp.post(url)

    assert response.status_code == 302
    assert response.url == reverse('search') + '?entity_type=Organization'

    with pytest.raises(Organization.DoesNotExist):
        Organization.objects.get(uuid=org.uuid)


@pytest.mark.django_db
def test_delete_organization_view_with_related_entities(setUp, organizations, expected_entity_names):
    org = organizations[0]
    url = reverse_lazy('delete-organization', args=[org.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure all the related entities are rendered on the page.
    for entity_name in expected_entity_names:
        assert entity_name in response.content.decode('utf-8')
    # Make sure that the confirm button is disabled.
    assert 'value="Confirm" disabled' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_delete_organization_view_no_related_entities(setUp, organizations):
    org = organizations[0]
    url = reverse_lazy('delete-organization', args=[org.uuid])
    response = setUp.get(url)
    assert response.status_code == 200
    # Make sure no related entities are rendered on the page.
    assert 'Related entities' not in response.content.decode('utf-8')
    # Make sure that the confirm button is enabled.
    assert 'disabled' not in response.content.decode('utf-8')


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_create_organization(save_and_continue,
                             setUp,
                             new_access_points,
                             fake_signal,
                             organization_classifications):

    response = setUp.get(reverse_lazy('create-organization'))

    assert response.status_code == 200

    new_source_ids = [s.uuid for s in new_access_points]

    classification_ids = [c.id for c in organization_classifications]

    post_data = {
        'name': 'Big, big guys',
        'name_source': new_source_ids,
        'aliases': ['floop', 'flooper'],
        'aliases_source': new_source_ids,
        'classification': classification_ids,
        'classification_source': new_source_ids,
        'division_id': 'ocd-division/country:us',
        'division_id_source': new_source_ids,
        'firstciteddate': '1999',
        'firstciteddate_source': new_source_ids,
        'lastciteddate': '2001',
        'lastciteddate_source': new_source_ids,
        'realstart': 'on',
        'open_ended': 'N',
        'open_ended_source': new_source_ids,
    }

    if save_and_continue:
        post_data['_continue'] = True

    response = setUp.post(reverse_lazy('create-organization'),
                          post_data)

    assert response.status_code == 302

    organization = Organization.objects.get(organizationname__value='Big, big guys')

    if save_and_continue:
        assert response.url == reverse_lazy('edit-organization', args=[organization.uuid])
    else:
        assert response.url == reverse_lazy('view-organization', args=[organization.uuid])

    assert set(new_access_points) <= set(organization.name.get_sources())
    assert set(new_access_points) <= set(organization.aliases.get_list()[0].get_sources())
    assert 'floop' in [a.get_value().value for a in organization.aliases.get_list()]

    fake_signal.assert_called_with(object_id=str(organization.uuid),
                                   sender=Organization)


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_edit_composition(save_and_continue,
                          setUp,
                          full_organizations,
                          new_access_points,
                          fake_signal):

    parent, middle, _ = full_organizations

    first_comp = middle.parent_organization.first().object_ref

    response = setUp.get(reverse_lazy('edit-organization-composition',
                                      args=[parent.uuid, first_comp.id]))

    assert response.status_code == 200

    new_source_ids = [s.uuid for s in new_access_points]

    post_data = {
        'parent': parent.id,
        'parent_source': new_source_ids,
        'child': middle.id,
        'child_source': new_source_ids,
        'classification': 'Command',
        'classification_source': new_source_ids,
    }

    if save_and_continue:
        post_data['_continue'] = True

    url = reverse_lazy(
        'edit-organization-composition',
        args=[parent.uuid, first_comp.id]
    )
    response = setUp.post(url, post_data)

    assert response.status_code == 302

    if save_and_continue:
        assert response.url == url
    else:
        assert response.url == reverse_lazy('view-organization', args=[parent.uuid])

    assert first_comp.parent.get_value().value == parent
    assert first_comp.child.get_value().value == middle
    assert [s for s in first_comp.child.get_sources()] == [s for s in first_comp.parent.get_sources()]

    fake_signal.assert_called_with(object_id=first_comp.id,
                                   sender=Composition)


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_create_composition(save_and_continue,
                            setUp,
                            organizations,
                            new_access_points,
                            fake_signal):

    parent, middle, _ = organizations

    response = setUp.get(reverse_lazy('create-organization-composition',
                                      args=[parent.uuid]))

    assert response.status_code == 200

    new_source_ids = [s.uuid for s in new_access_points]

    post_data = {
        'parent': parent.id,
        'parent_source': new_source_ids,
        'child': middle.id,
        'child_source': new_source_ids,
        'classification': 'Command',
        'classification_source': new_source_ids,
    }

    if save_and_continue:
        post_data['_continue'] = True

    response = setUp.post(reverse_lazy('create-organization-composition',
                                       args=[parent.uuid]),
                          post_data)

    assert response.status_code == 302

    composition = Composition.objects.filter(compositionparent__value=parent,
                                             compositionchild__value=middle).first()

    if save_and_continue:
        assert response.url == reverse_lazy(
            'edit-organization-composition',
            args=[parent.uuid, composition.id]
        )
    else:
        assert response.url == reverse_lazy('view-organization', args=[parent.uuid])

    assert composition.parent.get_value().value == parent
    assert composition.child.get_value().value == middle
    assert {s for s in composition.child.get_sources()} == {s for s in composition.parent.get_sources()}

    fake_signal.assert_called_with(object_id=composition.id,
                                   sender=Composition)


@pytest.mark.django_db
def test_delete_composition(setUp, full_organizations, fake_signal):
    parent, middle, _ = full_organizations
    first_comp = middle.parent_organization.first().object_ref

    response = setUp.post(reverse_lazy(
        'delete-organization-composition',
        args=[middle.uuid, first_comp.id]
    ))

    assert response.status_code == 302
    assert response.url == reverse_lazy('create-organization-composition', args=[middle.uuid])

    fake_signal.assert_called_with(object_id=middle.uuid, sender=Organization)


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_create_personnel(save_and_continue,
                          setUp,
                          organizations,
                          people,
                          membership_person,
                          new_access_points,
                          fake_signal):
    organization = organizations[0]
    person = people[0]
    rank = Rank.objects.first()
    role = Role.objects.first()

    url = reverse_lazy('create-organization-personnel', args=[organization.uuid])
    get_response = setUp.get(url)
    assert get_response.status_code == 200
    assert "<h2>Add personnel</h2>" in get_response.content.decode('utf-8')

    new_source_ids = [s.uuid for s in new_access_points]
    post_data = {
        'organization': organization.id,
        'member': person.id,
        'member_source': new_source_ids,
        'rank': rank.id,
        'rank_source': new_source_ids,
        'role': role.id,
        'role_source': new_source_ids,
        'title': 'Test title',
        'title_source': new_source_ids,
        'firstciteddate': '1999',
        'firstciteddate_source': new_source_ids,
        'lastciteddate': '2001',
        'lastciteddate_source': new_source_ids,
        'endcontext': 'Test end context',
        'endcontext_source': new_source_ids,
    }

    if save_and_continue:
        post_data['_continue'] = True

    post_response = setUp.post(url, post_data)

    assert post_response.status_code == 302

    # Since this person has probably already had a membership created by a fixture,
    # retrieve the last membership, which should correspond to the one we just made
    membership = MembershipPerson.objects.filter(
        membershippersonmember__value=person,
        membershippersonorganization__value=organization
    ).last()

    if save_and_continue:
        assert post_response.url == reverse_lazy(
            'edit-organization-personnel',
            args=[organization.uuid, membership.id]
        )
    else:
        assert post_response.url == reverse_lazy('view-organization', args=[organization.uuid])

    assert membership.member.get_value().value == person
    assert set(membership.member.get_sources()) == set(new_access_points)

    assert membership.organization.get_value().value == organization
    assert set(membership.organization.get_sources()) == set(new_access_points)

    assert membership.rank.get_value().value == rank
    assert set(membership.rank.get_sources()) == set(new_access_points)

    assert membership.role.get_value().value == role
    assert set(membership.role.get_sources()) == set(new_access_points)

    assert membership.title.get_value().value == 'Test title'
    assert set(membership.title.get_sources()) == set(new_access_points)

    assert str(membership.firstciteddate.get_value().value) == '1999'
    assert set(membership.firstciteddate.get_sources()) == set(new_access_points)

    assert str(membership.lastciteddate.get_value().value) == '2001'
    assert set(membership.lastciteddate.get_sources()) == set(new_access_points)

    assert membership.endcontext.get_value().value == 'Test end context'
    assert set(membership.endcontext.get_sources()) == set(new_access_points)

    fake_signal.assert_called_with(object_id=membership.id,
                                   sender=MembershipPerson)


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_edit_personnel(save_and_continue,
                        setUp,
                        membership_person,
                        people,
                        new_access_points,
                        fake_signal):
    membership = membership_person[0]
    org = membership.organization.get_value().value
    person = people[-1]

    url = reverse_lazy('edit-organization-personnel', args=[org.uuid, membership.id])
    get_response = setUp.get(url)
    assert get_response.status_code == 200
    assert "<h2>Edit personnel</h2>" in get_response.content.decode('utf-8')

    new_source_ids = [s.uuid for s in new_access_points]
    post_data = {
        'organization': org.id,
        'member': person.id,
        'member_source': new_source_ids,
    }

    if save_and_continue:
        post_data['_continue'] = True

    post_response = setUp.post(url, post_data)

    assert post_response.status_code == 302

    if save_and_continue:
        assert post_response.url == reverse_lazy(
            'edit-organization-personnel',
            args=[org.uuid, membership.id]
        )
    else:
        assert post_response.url == reverse_lazy('view-organization', args=[org.uuid])

    assert membership.member.get_value().value == person
    assert set(membership.member.get_sources()) == set(new_access_points)

    fake_signal.assert_called_with(object_id=membership.id, sender=MembershipPerson)


@pytest.mark.django_db
def test_delete_personnel(setUp, membership_person, fake_signal):
    membership = membership_person[0]
    org = membership.organization.get_value().value

    response = setUp.post(reverse_lazy(
        'delete-organization-personnel',
        args=[org.uuid, membership.id]
    ))

    assert response.status_code == 302
    assert response.url == reverse_lazy('create-organization-personnel', args=[org.uuid])

    fake_signal.assert_called_with(object_id=org.uuid, sender=Organization)


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_create_emplacement(save_and_continue,
                            setUp,
                            organizations,
                            location_node,
                            new_access_points,
                            fake_signal):
    organization = organizations[0]

    url = reverse_lazy('create-organization-emplacement', args=[organization.uuid])
    get_response = setUp.get(url)
    assert get_response.status_code == 200
    assert "<h2>Create site</h2>" in get_response.content.decode('utf-8')

    new_source_ids = [s.uuid for s in new_access_points]
    post_data = {
        'site': location_node.id,
        'site_source': new_source_ids,
        'organization': organization.id
    }

    if save_and_continue:
        post_data['_continue'] = True

    post_response = setUp.post(url, post_data)

    assert post_response.status_code == 302

    emplacement = organization.emplacements.first().object_ref

    if save_and_continue:
        assert post_response.url == reverse_lazy(
            'edit-organization-emplacement',
            args=[organization.uuid, emplacement.id]
        )
    else:
        assert post_response.url == reverse_lazy('view-organization', args=[organization.uuid])

    assert emplacement.site.get_value().value == location_node
    assert set(emplacement.site.get_sources()) == set(new_access_points)

    fake_signal.assert_called_with(object_id=emplacement.id, sender=Emplacement)


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_edit_emplacement(save_and_continue,
                          setUp,
                          emplacement,
                          location_node,
                          new_access_points,
                          fake_signal):
    emp = emplacement[0]
    org = emp.organization.get_value().value

    url = reverse_lazy('edit-organization-emplacement', args=[org.uuid, emp.id])
    get_response = setUp.get(url)
    assert get_response.status_code == 200
    assert "<h2>Edit site</h2>" in get_response.content.decode('utf-8')

    new_source_ids = [s.uuid for s in new_access_points]
    post_data = {
        'site': location_node.id,
        'site_source': new_source_ids,
        'organization': org.id
    }

    if save_and_continue:
        post_data['_continue'] = True

    post_response = setUp.post(url, post_data)

    assert post_response.status_code == 302

    if save_and_continue:
        assert post_response.url == url
    else:
        assert post_response.url == reverse_lazy('view-organization', args=[org.uuid])

    assert emp.site.get_value().value == location_node
    assert set(emp.site.get_sources()) == set(new_access_points)

    fake_signal.assert_called_with(object_id=emp.id, sender=Emplacement)


@pytest.mark.django_db
def test_delete_emplacement(setUp, emplacement, fake_signal):
    emp = emplacement[0]
    org = emp.organization.get_value().value

    response = setUp.post(reverse_lazy(
        'delete-organization-emplacement',
        args=[org.uuid, emp.id]
    ))

    assert response.status_code == 302
    assert response.url == reverse_lazy('create-organization-emplacement', args=[org.uuid])

    fake_signal.assert_called_with(object_id=org.uuid, sender=Organization)


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_create_association(save_and_continue,
                            setUp,
                            organizations,
                            location_relation,
                            new_access_points,
                            fake_signal):
    organization = organizations[0]

    url = reverse_lazy('create-organization-association', args=[organization.uuid])
    get_response = setUp.get(url)
    assert get_response.status_code == 200
    assert "<h2>Create area</h2>" in get_response.content.decode('utf-8')

    new_source_ids = [s.uuid for s in new_access_points]
    post_data = {
        'area': location_relation.id,
        'area_source': new_source_ids,
        'organization': organization.id
    }

    if save_and_continue:
        post_data['_continue'] = True

    post_response = setUp.post(url, post_data)

    assert post_response.status_code == 302

    assoc = organization.associations.first().object_ref

    if save_and_continue:
        assert post_response.url == reverse_lazy(
            'edit-organization-association',
            args=[organization.uuid, assoc.id]
        )
    else:
        assert post_response.url == reverse_lazy('view-organization', args=[organization.uuid])

    assert assoc.area.get_value().value == location_relation
    assert set(assoc.area.get_sources()) == set(new_access_points)

    fake_signal.assert_called_with(object_id=assoc.id, sender=Association)


@pytest.mark.django_db
@pytest.mark.parametrize('save_and_continue', [True, False])
def test_edit_association(save_and_continue,
                          setUp,
                          association,
                          location_relation,
                          new_access_points,
                          fake_signal):
    assoc = association[0]
    org = assoc.organization.get_value().value

    url = reverse_lazy('edit-organization-association', args=[org.uuid, assoc.id])
    get_response = setUp.get(url)
    assert get_response.status_code == 200
    assert "<h2>Edit area</h2>" in get_response.content.decode('utf-8')

    new_source_ids = [s.uuid for s in new_access_points]
    post_data = {
        'area': location_relation.id,
        'area_source': new_source_ids,
        'organization': org.id
    }

    if save_and_continue:
        post_data['_continue'] = True

    post_response = setUp.post(url, post_data)

    assert post_response.status_code == 302

    if save_and_continue:
        assert post_response.url == url
    else:
        assert post_response.url == reverse_lazy('view-organization', args=[org.uuid])

    assert assoc.area.get_value().value == location_relation
    assert set(assoc.area.get_sources()) == set(new_access_points)

    fake_signal.assert_called_with(object_id=assoc.id, sender=Association)


@pytest.mark.django_db
def test_delete_association(setUp, association, fake_signal):
    assoc = association[0]
    org = assoc.organization.get_value().value

    response = setUp.post(reverse_lazy(
        'delete-organization-association',
        args=[org.uuid, assoc.id]
    ))

    assert response.status_code == 302
    assert response.url == reverse_lazy('create-organization-association', args=[org.uuid])

    fake_signal.assert_called_with(object_id=org.uuid, sender=Organization)


@pytest.mark.django_db
def test_organization_edit_buttons(setUp,
                                   full_organizations,
                                   membership_person,
                                   membership_organization):
    org = full_organizations[0]
    composition = Composition.objects.first()
    person = org.personnel[0]
    association = org.associations[0].object_ref
    emplacement = org.emplacements[0].object_ref

    assert is_tab_active(setUp.get(reverse_lazy('edit-organization', args=[org.uuid])),
                        'Basics')

    assert is_tab_active(setUp.get(reverse_lazy('create-organization-composition', args=[org.uuid])),
                        'Relationships')
    assert is_tab_active(setUp.get(reverse_lazy('edit-organization-composition', args=[org.uuid, composition.pk])),
                        'Relationships')

    assert is_tab_active(setUp.get(reverse_lazy('create-organization-personnel', args=[org.uuid])),
                        'Personnel')
    assert is_tab_active(setUp.get(reverse_lazy('edit-organization-personnel', args=[org.uuid, person.pk])),
                        'Personnel')

    assert is_tab_active(setUp.get(reverse_lazy('create-organization-emplacement', args=[org.uuid])),
                        'Locations')
    assert is_tab_active(setUp.get(reverse_lazy('edit-organization-emplacement', args=[org.uuid, emplacement.pk])),
                        'Locations')

    assert is_tab_active(setUp.get(reverse_lazy('create-organization-association', args=[org.uuid])),
                        'Locations')
    assert is_tab_active(setUp.get(reverse_lazy('edit-organization-association', args=[org.uuid, association.pk])),
                        'Locations')

    assert is_tab_active(setUp.get(reverse_lazy('create-organization-membership', args=[org.uuid])),
                        'Relationships')
    assert is_tab_active(setUp.get(reverse_lazy('edit-organization-membership', args=[org.uuid, membership_organization.pk])),
                        'Relationships')
