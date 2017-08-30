from random import randint

from django.test import TestCase, Client
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db import connection
from django.core.management import call_command
from django.db.models.aggregates import Count

from organization.models import Organization, OrganizationName, OrganizationAlias
from source.models import Source, Publication
from composition.models import Classification

from sfm_pc.signals import update_orgname_index, update_orgalias_index, \
    update_personname_index, update_personalias_index, update_source_index, \
    update_publication_index

def setUpModule():

    post_save.disconnect(receiver=update_orgname_index, sender=OrganizationName)
    post_save.disconnect(receiver=update_orgalias_index, sender=OrganizationAlias)
    post_save.disconnect(receiver=update_source_index, sender=Source)
    post_save.disconnect(receiver=update_publication_index, sender=Publication)

    call_command('loaddata', 'tests/fixtures/auth.json')
    call_command('loaddata', 'tests/fixtures/source.json')
    call_command('loaddata', 'tests/fixtures/organization.json')


def tearDownModule():

    with connection.cursor() as conn:
        conn.execute('TRUNCATE auth_user CASCADE')
        conn.execute('TRUNCATE source_source CASCADE')
        conn.execute('TRUNCATE source_publication CASCADE')
        conn.execute('TRUNCATE organization_organization CASCADE')


class CompositionTest(TestCase):

    client = Client()

    def setUp(self):
        self.user = User.objects.first()
        self.client.force_login(self.user)
        self.source = Source.objects.first()

        self.classification, _ = Classification.objects.get_or_create(value='Command')

        session = self.client.session
        session['source_id'] = self.source.id
        session.save()

    def tearDown(self):
        self.client.logout()

    def getRandomOrganization(self):

        count = Organization.objects.aggregate(count=Count('id'))['count']

        random_index = randint(0, count - 1)

        return Organization.objects.all()[random_index]

    def test_create_composition(self):

        organizations = [self.getRandomOrganization() for i in range(3)]
        organizations = [{'id': o.id, 'name': o.name.get_value().value}
                         for o in organizations]

        session = self.client.session
        session['organizations'] = organizations
        session.save()

        response = self.client.get(reverse_lazy('create-composition'), follow=True)

        assert response.context['source'] == self.source

        post_data = {
            'form-TOTAL_FORMS': '3',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
        }

        for index, organization in enumerate(organizations):

            rel_type = 'child'
            if index % 2 == 0:
                rel_type = 'parent'

            data = {
                'form-{}-startdate'.format(index): '2001-01-01',
                'form-{}-enddate'.format(index): '2010-01-01',
                'form-{}-date_confidence'.format(index): 1,
                'form-{}-classification'.format(index): self.classification.id,
                'form-{}-classification_confidence'.format(index): 1,
                'form-{}-organization'.format(index): organization['id'],
                'form-{}-related_organization'.format(index): organizations[index - 1]['id'],
                'form-{}-related_org_confidence'.format(index): 1,
                'form-{}-relationship_type'.format(index): rel_type,
                'form-{}-relationship_type_confidence'.format(index): 1,
            }

            post_data.update(data)

        response = self.client.post(reverse_lazy('create-composition'), post_data)

        self.assertRedirects(response, reverse_lazy('create-organization-membership'))
