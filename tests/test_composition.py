from random import randint

from django.test import TestCase, Client
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db import connection
from django.core.management import call_command
from django.db.models.aggregates import Count

from organization.models import Organization, OrganizationName, OrganizationAlias
from source.models import Source
from composition.models import Classification
from composition.views import CompositionCreate

from sfm_pc.signals import update_orgname_index, update_orgalias_index, \
    update_personname_index, update_personalias_index, update_source_index


# class CompositionTest(TestCase):
#
#     client = Client()
#
#     def setUp(self):
#         self.user = User.objects.first()
#         self.client.force_login(self.user)
#         self.source = Source.objects.first()
#
#         self.classification, _ = Classification.objects.get_or_create(value='Command')
#
#         organizations = Organization.objects.all()[:3]
#         organizations = [{'id': o.id, 'name': o.name.get_value().value}
#                         for o in organizations]
#
#         session = self.client.session
#         session['organizations'] = organizations
#
#         session['source_id'] = str(self.source.uuid)
#         session.save()
#
#     def tearDown(self):
#         self.client.logout()

    # def test_create_composition(self):

    #     response = self.client.get(reverse_lazy('create-composition'), follow=True)

    #     assert response.context['source'] == self.source

    #     post_data = {
    #         'form-TOTAL_FORMS': '2',
    #         'form-INITIAL_FORMS': '0',
    #         'form-MAX_NUM_FORMS': '',
    #     }
    #     organizations = self.client.session.get('organizations')
    #     for index, organization in enumerate(organizations):

    #         # Skip the last org, so that we don't create a recursive hierarchy
    #         if index == len(organizations) - 1:
    #             continue

    #         data = {
    #             'form-{}-startdate'.format(index): '2001-01-01',
    #             'form-{}-startdate_confidence'.format(index): 1,
    #             'form-{}-realstart'.format(index): True,
    #             'form-{}-enddate'.format(index): '2010-01-01',
    #             'form-{}-enddate_confidence'.format(index): 1,
    #             'form-{}-open_ended'.format(index): 'Y',
    #             'form-{}-classification'.format(index): self.classification.id,
    #             'form-{}-classification_confidence'.format(index): 1,
    #             'form-{}-parent'.format(index): organization['id'],
    #             'form-{}-parent_confidence'.format(index): 1,
    #             'form-{}-child'.format(index): organizations[index - 1]['id'],
    #             'form-{}-child_confidence'.format(index): 1,
    #         }

    #         post_data.update(data)

    #     response = self.client.post(reverse_lazy('create-composition'), post_data)

    #     self.assertRedirects(response, reverse_lazy('create-organization-membership'))

    # def test_identical_parent_and_child(self):

    #     response = self.client.get(reverse_lazy('create-composition'), follow=True)

    #     post_data = {
    #         'form-TOTAL_FORMS': '3',
    #         'form-INITIAL_FORMS': '0',
    #         'form-MAX_NUM_FORMS': '',
    #     }

    #     organizations = self.client.session.get('organizations')
    #     for index, organization in enumerate(organizations):

    #         # Make the parent and child units the same
    #         data = {
    #             'form-{}-startdate'.format(index): '2001-01-01',
    #             'form-{}-startdate_confidence'.format(index): 1,
    #             'form-{}-realstart'.format(index): True,
    #             'form-{}-enddate'.format(index): '2010-01-01',
    #             'form-{}-enddate_confidence'.format(index): 1,
    #             'form-{}-open_ended'.format(index): 'Y',
    #             'form-{}-classification'.format(index): self.classification.id,
    #             'form-{}-classification_confidence'.format(index): 1,
    #             'form-{}-parent'.format(index): organization['id'],
    #             'form-{}-parent_confidence'.format(index): 1,
    #             'form-{}-child'.format(index): organization['id'],
    #             'form-{}-child_confidence'.format(index): 1,
    #         }

    #         post_data.update(data)

    #     response = self.client.post(reverse_lazy('create-composition'), post_data)

    #     assert 'must refer to different units' in response.content.decode('utf-8')

    # def test_recursive_hierarchy(self):

    #     response = self.client.get(reverse_lazy('create-composition'), follow=True)

    #     post_data = {
    #         'form-TOTAL_FORMS': '3',
    #         'form-INITIAL_FORMS': '0',
    #         'form-MAX_NUM_FORMS': '',
    #     }

    #     organizations = self.client.session.get('organizations')
    #     for index, organization in enumerate(organizations):

    #         # Making each org the parent of the org at the previous index
    #         # should create a circular hiearchy (since -1 indexes the last element
    #         # of a list)
    #         data = {
    #             'form-{}-startdate'.format(index): '2001-01-01',
    #             'form-{}-startdate_confidence'.format(index): 1,
    #             'form-{}-realstart'.format(index): True,
    #             'form-{}-enddate'.format(index): '2010-01-01',
    #             'form-{}-enddate_confidence'.format(index): 1,
    #             'form-{}-open_ended'.format(index): 'Y',
    #             'form-{}-classification'.format(index): self.classification.id,
    #             'form-{}-classification_confidence'.format(index): 1,
    #             'form-{}-parent'.format(index): organization['id'],
    #             'form-{}-parent_confidence'.format(index): 1,
    #             'form-{}-child'.format(index): organizations[index - 1]['id'],
    #             'form-{}-child_confidence'.format(index): 1,
    #         }

    #         post_data.update(data)

    #     response = self.client.post(reverse_lazy('create-composition'), post_data)

    #     assert 'command hierarchy is recursive' in response.content.decode('utf-8')

    # def test_exact_open_ended_without_end_date(self):

    #     response = self.client.get(reverse_lazy('create-composition'), follow=True)

    #     post_data = {
    #         'form-TOTAL_FORMS': '3',
    #         'form-INITIAL_FORMS': '0',
    #         'form-MAX_NUM_FORMS': '',
    #     }

    #     organizations = self.client.session.get('organizations')
    #     for index, organization in enumerate(organizations):

    #         # The open_ended value 'E' indicates the last cited date is also
    #         # the end date of the composition. If open_ended == 'E', the enddate
    #         # field cannot be null
    #         data = {
    #             'form-{}-startdate'.format(index): '2001-01-01',
    #             'form-{}-startdate_confidence'.format(index): 1,
    #             'form-{}-realstart'.format(index): True,
    #             'form-{}-enddate'.format(index): None,
    #             'form-{}-enddate_confidence'.format(index): 1,
    #             'form-{}-open_ended'.format(index): 'E',
    #             'form-{}-classification'.format(index): self.classification.id,
    #             'form-{}-classification_confidence'.format(index): 1,
    #             'form-{}-parent'.format(index): organization['id'],
    #             'form-{}-parent_confidence'.format(index): 1,
    #             'form-{}-child'.format(index): organizations[index - 1]['id'],
    #             'form-{}-child_confidence'.format(index): 1,
    #         }

    #         post_data.update(data)

    #     response = self.client.post(reverse_lazy('create-composition'), post_data)

    #     assert 'end date is required' in response.content.decode('utf-8')