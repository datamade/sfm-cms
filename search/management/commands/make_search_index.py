from os.path import join, abspath, dirname
import itertools

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.db.utils import ProgrammingError
from django.utils import dateformat

import pysolr
from dateutil import parser as dateparser

from countries_plus.models import Country

from search.search import Searcher
from person.models import Person
from membershipperson.models import MembershipPerson
from organization.models import Organization
from violation.models import Violation
from composition.models import Composition
from source.models import Source
from sfm_pc.templatetags.countries import country_name

class Command(BaseCommand):
    help = 'Add global search index'

    def __init__(self, *args, **kwargs):

        super(Command, self).__init__(*args, **kwargs)

        self.searcher = Searcher()
        self.updated_count = 0
        self.added_count = 0

    def add_arguments(self, parser):

        parser.add_argument(
            '--update',
            action='store_true',
            dest='update',
            default=False,
            help="Add new items to an existing search index"
        )
        parser.add_argument(
            '--entity-types',
            dest='entity_types',
            help='Comma separated list of entity types to index',
            default="compositions,commanders"
        )
        parser.add_argument(
            '--id',
            dest='doc_id',
            default=None,
            help="Specify a specific record ID to index"
        )
        parser.add_argument(
            '--recreate',
            action='store_true',
            dest='recreate',
            default=False,
            help="Delete all existing documents before creating the search index."
        )

    def handle(self, *args, **options):

        # Get command line args
        entity_types = [e.strip() for e in options['entity_types'].split(',')]
        update = options.get('update')
        doc_id = options.get('doc_id')
        recreate = options.get('recreate')

        '''
        TODO: How should recreate and update behave?
        '''
        if recreate:
            self.stdout.write(self.style.SUCCESS('Dropping current search index...'))
            self.searcher.delete(q='*:*')

        for entity_type in entity_types:

            getattr(self, 'index_{}'.format(entity_type))(update=update,
                                                          doc_id=doc_id)

        if update:
            success_message = 'Successfully updated global search index.'
            count = '{count} new indexes added.'.format(count=self.updated_count)
        else:
            success_message = 'Successfully created global search index.'
            count = '{count} new indexes added.'.format(count=self.added_count)

        self.stdout.write(self.style.SUCCESS(success_message))
        self.stdout.write(self.style.SUCCESS(count))

    def index_compositions(self, doc_id=None, update=False):
        self.stdout.write(self.style.HTTP_NOT_MODIFIED('\n Indexing compositions ... '))

        if doc_id:
            orgs = Organization.objects.filter(uuid=doc_id)
        else:
            orgs = Organization.objects.all()

        documents = []

        for organization in orgs:
            org_id = str(organization.uuid)

            # Skip this record if we're updating and it already exists
            if update and self.check_index(org_id):
                continue

            name = organization.name.get_value()

            parents = organization.parent_organization.all()
            published = all([p.value.published for p in parents])

            if parents.count() == 0:
                documents.append({
                    'id': 'composition-{}'.format(org_id),
                    'composition_parent_id_s': org_id,
                    'composition_parent_name_s': name,
                    'published_b': published,
                    'entity_type': 'Composition',
                    'content': 'Composition',
                })

            for parent in parents:
                # `parent_organization` returns a list of CompositionChilds,
                # so we have to jump through some hoops to get the foreign
                # key value
                composition = parent.object_ref
                parent = composition.parent.get_value().value
                parent_name = parent.name.get_value().value

                start_date = self.format_date(composition.startdate.get_value())
                end_date = self.format_date(composition.enddate.get_value())
                classification = composition.classification.get_value()
                open_ended = composition.open_ended.get_value()

                composition_daterange = None

                if start_date and end_date:
                    start_date = start_date.split('T')[0]
                    end_date = end_date.split('T')[0]

                    args = [start_date, end_date]

                    if dateparser.parse(start_date) > dateparser.parse(end_date):
                        args = [end_date, start_date]

                    composition_daterange = '[{0} TO {1}]'.format(*args)

                elif start_date and not end_date and open_ended and open_ended.value.strip() == 'Y':
                    composition_daterange = '[{} TO *]'.format(start_date.split('T')[0])

                elif start_date and not end_date and open_ended and open_ended.value.strip() == 'N':
                    date_string = start_date.split('T')[0]
                    composition_daterange = '[{} TO {}]'.format(date_string, date_string)

                elif not start_date and end_date:
                    composition_daterange = '[* TO {}]'.format(end_date.split('T')[0])

                if composition_daterange:
                    documents.append({
                        'id': 'composition-{}'.format(composition.id),
                        'composition_parent_id_s': str(parent.uuid),
                        'composition_parent_pk_i': parent.id,
                        'composition_parent_name_s': parent_name,
                        'composition_child_id_s': org_id,
                        'composition_child_pk_i': organization.id,
                        'composition_child_name_s': name,
                        'composition_daterange_dr': composition_daterange,
                        'published_b': published,
                        'entity_type': 'Composition',
                        'content': 'Composition',
                    })

            if update:
                self.updated_count += 1
            else:
                self.added_count += 1

        self.add_to_index(documents)

    def index_commanders(self, doc_id=None, update=False):
        self.stdout.write(self.style.HTTP_NOT_MODIFIED('\n Indexing commanders ... '))

        if doc_id:
            people = Person.objects.filter(uuid=doc_id)
        else:
            people = Person.objects.all()

        documents = []

        for person in people:
            person_id = str(person.uuid)

            if update and self.check_index(person_id):
                continue

            name = person.name.get_value()

            affiliations = person.memberships
            memberships = [mem.object_ref for mem in affiliations]

            for membership in memberships:

                org = membership.organization.get_value()

                if org:
                    org = org.value

                    fcd = membership.firstciteddate.get_value()
                    lcd = membership.lastciteddate.get_value()

                    assignment_range = None

                    if fcd and lcd:
                        fcd = self.format_date(fcd).split('T')[0]
                        lcd = self.format_date(lcd).split('T')[0]

                        args = [fcd, lcd]

                        if dateparser.parse(fcd) > dateparser.parse(lcd):
                            args = [lcd, fcd]

                        assignment_range = '[{0} TO {1}]'.format(*args)
                    elif fcd:
                        fcd = self.format_date(fcd).split('T')[0]
                        assignment_range = '[{} TO *]'.format(fcd)
                    elif lcd:
                        lcd = self.format_date(lcd).split('T')[0]
                        assignment_range = '[* TO {}]'.format(lcd)

                    role = membership.role.get_value()

                    if role and role.value.value == 'Commander' and assignment_range:

                        published = all([person.published, org.published])

                        commander = {
                            'id': 'commander-{}'.format(membership.id),
                            'commander_person_id_s': person_id,
                            'commander_person_name_s': name,
                            'commander_org_id_s': org.uuid,
                            'commander_org_name_s': org.name.get_value().value,
                            'commander_assignment_range_dr': assignment_range,
                            'published_b': published,
                            'entity_type': 'Commander',
                            'content': 'Commander',
                        }

                        documents.append(commander)

            if update:
                self.updated_count += 1
            else:
                self.added_count += 1

        self.add_to_index(documents)

    def add_to_index(self, documents):

        self.searcher.add(documents)

    def check_index(self, doc_id):
        '''
        Check if a document with the id `doc_id` already exists in the index.

        Returns boolean.
        '''
        results = self.searcher.search('id:"{doc_id}"'.format(doc_id=doc_id))

        return len(results) > 0

    def format_date(self, approx_df):
        '''
        Format an ApproximateDateField for use in the Solr index.

        '''
        if approx_df:
            # For now, we assign fuzzy dates bogus values for month/day if
            # they don't exist, but we should explore to see if Solr has better
            # ways of handling fuzzy dates
            approx_df = dateformat.format(approx_df.value, 'Y-m-d')
            approx_df = approx_df.replace('-00', '-01')
            approx_df += 'T00:00:00Z'

        return approx_df
