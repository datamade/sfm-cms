from django.test import TestCase, Client
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db import connection
from django.core.management import call_command

from organization.models import Organization, OrganizationName, OrganizationAlias
from source.models import Source, Publication

from sfm_pc.signals import update_orgname_index, update_orgalias_index, \
    update_source_index, update_publication_index


def setUpModule():

    post_save.disconnect(receiver=update_orgname_index, sender=OrganizationName)
    post_save.disconnect(receiver=update_orgalias_index, sender=OrganizationAlias)
    post_save.disconnect(receiver=update_source_index, sender=Source)
    post_save.disconnect(receiver=update_publication_index, sender=Publication)

    call_command('loaddata', 'tests/fixtures/auth.json')
    call_command('loaddata', 'tests/fixtures/source.json')
    call_command('loaddata', 'tests/fixtures/organization.json')
    call_command('update_countries_plus')


def tearDownModule():

    with connection.cursor() as conn:
        conn.execute('TRUNCATE auth_user CASCADE')
        conn.execute('TRUNCATE source_source CASCADE')
        conn.execute('TRUNCATE source_publication CASCADE')
        conn.execute('TRUNCATE organization_organization CASCADE')


class OrganizationTest(TestCase):

    client = Client()

    def setUp(self):
        self.user = User.objects.first()
        self.client.force_login(self.user)
        self.source = Source.objects.first()

        session = self.client.session
        session['source_id'] = self.source.id
        session.save()

    def tearDown(self):
        self.client.logout()

    def getRandomOrganization(self):
        from django.db.models.aggregates import Count
        import random

        count = Organization.objects.aggregate(count=Count('id'))['count']

        random.seed(256)
        random_index = random.randint(0, count - 1)

        return Organization.objects.all()[random_index]

    def test_view_organization(self):

        for org_id in range(1, 10):
            response = self.client.get(reverse_lazy('detail_organization', args=[org_id]))

            try:
                assert response.status_code == 200
            except AssertionError as e:
                print(org_id)
                print(response.content)
                raise(e)

    def test_create_organization(self):
        response = self.client.get(reverse_lazy('create-organization'), follow=True)

        assert response.context['source'] == self.source

        post_data = {
            'form-TOTAL_FORMS': '3',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'form-FORMS_ADDED': 3,
            'form-0-name': -1,
            'form-0-name_text': 'Test Organization',
            'form-0-name_confidence': 1,
            'form-0-division_id': 'ocd-division/country:ng',
            'form-0-division_confidence': 1,
            'form-0-alias_text': ['Testy', 'Lil tester'],
            'form-0-classification_text': ['Army', 'Military'],
            'form-0-classification_confidence': 1,
            'form-0-alias': [],
            'form-0-alias_confidence': 1,
            'form-0-classification': [1, 2],
            'form-0-headquarters': 'Bolo',
            'form-0-headquarters_confidence': 1,
            'form-0-firstciteddate': '2001-01-01',
            'form-0-realstart': True,
            'form-0-firstciteddate_confidence': 1,
            'form-0-lastciteddate': '2001-01-02',
            'form-0-open_ended': 'Y',
            'form-0-lastciteddate_confidence': 1
        }

        org_ids = []

        for index in range(1, 3):
            organization = self.getRandomOrganization()

            aliases = [a.get_value().value.value for a in
                       organization.aliases.get_list()]

            alias_ids = [a.get_value().value.id for a in
                         organization.aliases.get_list()]

            classifications = [c.get_value().value.value for c in
                               organization.classification.get_list()]

            classification_ids = [c.get_value().value.id for c in
                                  organization.classification.get_list()]

            data = {
                'form-{}-name'.format(index): organization.id,
                'form-{}-name_text'.format(index): organization.name.get_value().value,
                'form-{}-name_confidence'.format(index): 1,
                'form-{}-division_id'.format(index): 'ocd-division/country:ng',
                'form-{}-division_confidence'.format(index): 1,
                'form-{}-alias_text'.format(index): aliases,
                'form-{}-classification_text'.format(index): classifications,
                'form-{}-classification_confidence'.format(index): 1,
                'form-{}-alias'.format(index): alias_ids,
                'form-{}-alias_confidence'.format(index): 1,
                'form-{}-classification'.format(index): classification_ids,
            }

            hq = organization.headquarters.get_value()
            if hq:
                hq = hq.value
                data['form-{}-headquarters'.format(index)] = hq,
                data['form-{}-headquarters_confidence'.format(index)] = 1

            fcd = organization.firstciteddate.get_value()
            if fcd:
                fcd = fcd.value
                data['form-{}-firstciteddate'.format(index)] = fcd,
                data['form-{}-firstciteddate_confidence'.format(index)] = 1

            lcd = organization.lastciteddate.get_value()
            if lcd:
                lcd = lcd.value
                data['form-{}-lastciteddate'.format(index)] = lcd,
                data['form-{}-lastciteddate_confidence'.format(index)] = 1

            open_ended = organization.open_ended.get_value()
            if open_ended:
                open_ended = open_ended.value
                data['form-{}-open_ended'.format(index)] = open_ended,
                data['form-{}-open_ended_confidence'.format(index)] = 1

            realstart = organization.realstart.get_value()
            if realstart:
                realstart = realstart.value
                data['form-{}-realstart'.format(index)] = realstart,
                data['form-{}-realstart_confidence'.format(index)] = 1

            org_ids.append(organization.id)
            post_data.update(data)

        response = self.client.post(reverse_lazy('create-organization'), post_data)

        self.assertRedirects(response, reverse_lazy('create-composition'))

        new_org = Organization.objects.get(organizationname__value='Test Organization').id
        other_orgs = [o.id for o in Organization.objects.filter(id__in=org_ids)]

        session_ids = [c['id'] for c in self.client.session['organizations']]

        assert set(session_ids) == {new_org, *other_orgs}

    def test_update_organization(self):
        organization = self.getRandomOrganization()

        response = self.client.get(reverse_lazy('edit_organization',
                                   args=[organization.id]))

        assert response.status_code == 200

        assert response.context['source_object'] == organization
        assert response.context['form_data']['name'] == organization.name.get_value()

        post_data = {
            'name': -1,
            'name_text': 'Test Organization',
            'name_confidence': 1,
            'division_id': 'ocd-division/country:ng',
            'division_confidence': 1,
            'alias_text': ['Testy', 'Lil tester'],
            'alias_confidence': 1,
            'classification_text': ['Army', 'Military'],
            'alias': [],
            'classification': [1, 2],
            'classification_confidence': 1,
            'source': self.source.id,
        }

        response = self.client.post(reverse_lazy('edit_organization',
                                    args=[organization.id]), post_data)

        self.assertRedirects(response, reverse_lazy('dashboard'))

        edited = Organization.objects.get(id=organization.id)

        assert str(edited.name.get_value()) == 'Test Organization'
