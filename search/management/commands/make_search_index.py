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
            # default="people,organizations,sources,violations"
            default="people,organizations,violations"
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

    def index_organizations(self, doc_id=None, update=False):
        self.stdout.write(self.style.HTTP_NOT_MODIFIED('\n Indexing organizations ... '))

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
            content = [name.value]

            aliases = organization.aliases.get_list()
            if aliases:
                content.extend(al.get_value().value.value for al in aliases)

            classes = organization.classification.get_list()
            class_count = len(classes)
            if classes:
                content.extend(cl.get_value().value.value for cl in classes)

            hq = organization.headquarters.get_value()
            if hq:
                content.extend([hq.value])

            first_cited = self.format_date(organization.firstciteddate.get_value())
            last_cited = self.format_date(organization.lastciteddate.get_value())
            open_ended = organization.open_ended.get_value()

            division_ids, countries = set(), set()

            # Start by getting the division ID recorded for this org
            org_division_id = organization.division_id.get_value()
            if org_division_id:
                division_ids.update([org_division_id.value])
                org_country = country_name(org_division_id)
                countries.update([org_country])

            country_count = len(countries)

            # Grab foreign key sets
            emplacements = organization.emplacementorganization_set.all()

            exactloc_names, admin_names, admin_l1_names = set(), set(), set()
            for emp in emplacements:
                emp = emp.object_ref
                site = emp.site.get_value()
                if site:
                    site = site.value

                    exactloc_name = site.location_name.get_value()
                    if exactloc_name:
                        exactloc_names.update([exactloc_name.value])

                    admin_name = site.admin_name.get_value()
                    if admin_name:
                        admin_names.update([admin_name.value])

                    admin_l1_name = site.adminlevel1.get_value()
                    if admin_l1_name:
                        admin_l1_names.update([admin_l1_name.value])

                    emp_division_id = site.division_id.get_value()
                    if emp_division_id:
                        division_ids.update([emp_division_id.value])
                        emp_country = country_name(emp_division_id)
                        countries.update([emp_country])

            # For now, only index whether a site exists or not based on what we
            # display in the search table
            last_site_exists = int(max(len(exactloc_names), len(admin_names)) > 0)

            areas = set()
            assocs = organization.associationorganization_set.all()
            for assoc in assocs:
                area = assoc.object_ref.area.get_value()
                if area:
                    area_name = area.value.osmname.get_value()
                    if area_name:
                        areas.update([area_name.value])

            parent_names, parent_ids = [], []
            parents = organization.parent_organization.all()
            parent_count = len(parents)

            if parent_count == 0:
                documents.append({
                    'id': 'composition-{}'.format(org_id),
                    'composition_parent_id_s': org_id,
                    'composition_parent_name_s': name,
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
                parent_names.append(parent_name)

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
                        'entity_type': 'Composition',
                        'content': 'Composition',
                    })

            memberships = []
            mems = organization.membershiporganizationmember_set.all()
            for membership in mems:
                # Similar to parents, we have to traverse the directed graph
                # in order to get the entities we want
                org = membership.object_ref.organization.get_value().value
                if org.name.get_value():
                    memberships.append(org.name.get_value())

            # Convert sets to lists, for indexing
            division_ids, countries = list(division_ids), list(countries)
            exactloc_names, admin_names = list(exactloc_names), list(admin_names)
            admin_l1_names, areas = list(admin_l1_names), list(areas)

            # Add some attributes to the global index
            for attr in (parent_names, countries, exactloc_names, admin_names,
                         admin_l1_names, areas):
                content.extend(attr)

            content = '; '.join(content)

            document = {
                'id': org_id,
                'entity_type': 'Organization',
                'content': content,
                'location': '',  # disabled until we implement map search
                'country_ss': countries,
                'division_id_ss': division_ids,
                'start_date_dt': first_cited,
                'end_date_dt': last_cited,
                'open_ended_s': open_ended,
                'organization_name_s': name,
                'organization_parent_name_ss': parent_names,
                'organization_parent_count_i': parent_count,
                'organization_membership_ss': memberships,
                'organization_classification_ss': classes,
                'organization_classification_count_i': class_count,
                'organization_alias_ss': aliases,
                'organization_headquarters_s': hq,
                'organization_exact_location_ss': exactloc_names,
                'organization_site_count_i': last_site_exists,
                'organization_country_count_i': country_count,
                'organization_admin_ss': admin_names,
                'organization_adminlevel1_ss': admin_l1_names,
                'organization_area_ss': areas,
                'organization_start_date_dt': first_cited,
                'organization_end_date_dt': first_cited,
                'text': content
            }

            documents.append(document)

            if update:
                self.updated_count += 1
            else:
                self.added_count += 1

        self.add_to_index(documents)

    def index_people(self, doc_id=None, update=False):
        self.stdout.write(self.style.HTTP_NOT_MODIFIED('\n Indexing people ... '))

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
            content = [name.value]

            aliases = person.aliases.get_list()
            alias_count = 0
            if aliases:
                content.extend(al.get_value().value for al in aliases)
                alias_count = len(aliases)

            affiliations = person.memberships
            memberships = [mem.object_ref for mem in affiliations]

            division_ids, countries = set(), set()

            # Start by getting the division ID recorded for the person
            person_division_id = person.division_id.get_value()
            if person_division_id:
                division_ids.update([person_division_id.value])
                person_country = country_name(person_division_id)
                countries.update([person_country])

            ranks, roles, titles = set(), set(), set()
            latest_rank, latest_role, latest_title = None, None, None

            first_cited = None
            last_cited = None

            # Get most recent information
            latest_title = memberships[0].title.get_value()
            latest_role = memberships[0].role.get_value()
            most_recent_unit = memberships[0].organization.get_value()
            most_recent_rank = memberships[0].rank.get_value()
            latest_rank = most_recent_rank

            for membership in memberships:

                org = membership.organization.get_value()

                if org:

                    org = org.value

                    # Check to see if we can extend first/last cited dates
                    fcd = membership.firstciteddate.get_value()
                    if fcd:
                        if first_cited:
                            if fcd.value < first_cited.value:
                                first_cited = fcd
                        else:
                            first_cited = fcd

                    lcd = membership.lastciteddate.get_value()
                    if lcd:
                        if last_cited:
                            if lcd.value > last_cited.value:
                                last_cited = lcd
                        else:
                            last_cited = lcd

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

                        commander = {
                            'id': 'commander-{}'.format(membership.id),
                            'commander_person_id_s': person_id,
                            'commander_person_name_s': name,
                            'commander_org_id_s': org.uuid,
                            'commander_org_name_s': org.name.get_value().value,
                            'commander_assignment_range_dr': assignment_range,
                            'entity_type': 'Commander',
                            'content': 'Commander',
                        }
                        documents.append(commander)

                    elif role:
                        roles.add(role.value.value)

                    rank = membership.rank.get_value()
                    if rank:
                        ranks.add(rank.value.value)

                    title = membership.title.get_value()
                    if title:
                        titles.add(title.value)


                    # We also want to index the person based on the countries
                    # their member units have operated in
                    org_division_id = org.division_id.get_value()

                    if org_division_id:
                        division_ids.update([org_division_id.value])
                        org_country = country_name(org_division_id)
                        countries.update([org_country])



            # Convert sets to lists, for indexing
            division_ids, countries = list(division_ids), list(countries)
            ranks, roles, titles = list(ranks), list(roles), list(titles)

            # Add some attributes to the global index
            for attr in (roles, ranks, titles, countries):
                content.extend(attr)

            content = '; '.join(content)

            first_cited = self.format_date(first_cited)
            last_cited = self.format_date(last_cited)

            document = {
                'id': person_id,
                'entity_type': 'Person',
                'content': content,
                'location': '',  # disabled until we implement map search
                'country_ss': countries,
                'division_id_ss': division_ids,
                'person_title_ss': titles,
                'person_name_s': name,
                'person_alias_ss': aliases,
                'person_alias_count_i': alias_count,
                'person_role_ss': roles,
                'person_rank_ss': ranks,
                'person_most_recent_rank_s': most_recent_rank,
                'person_most_recent_unit_s': most_recent_unit,
                'person_title_ss': titles,
                'person_current_rank_s': latest_rank,
                'person_current_role_s': latest_role,
                'person_current_title_s': latest_title,
                'person_first_cited_dt': first_cited,
                'person_last_cited_dt': last_cited,
                'start_date_dt': first_cited,
                'end_date_dt': last_cited,
                'text': content
            }

            documents.append(document)

            if update:
                self.updated_count += 1
            else:
                self.added_count += 1

        self.add_to_index(documents)

    def index_violations(self, doc_id=None, update=False):
        self.stdout.write(self.style.HTTP_NOT_MODIFIED('\n Indexing violations ... '))

        if doc_id:
            violations = Violation.objects.filter(uuid=doc_id)
        else:
            violations = Violation.objects.all()

        documents = []

        for violation in violations:

            viol_id = str(violation.uuid)

            if update and self.check_index(viol_id):
                continue

            content = []

            description = violation.description.get_value()
            if description:
                description = description.value

            vtypes = violation.types.get_list()
            vtype_count = 0
            if vtypes:
                vtypes = list(str(vt.get_value().value) for vt in vtypes)
                vtype_count = len(vtypes)

            perps = violation.perpetrator.get_list()
            perp_names, perp_aliases = [], []
            perp_count = 0
            if perps:
                # Move from PerpetratorPerson -> Person
                perps = list(perp.get_value().value for perp in perps)
                perp_count = len(perps)
                for perp in perps:
                    aliases = perp.aliases.get_list()
                    if aliases:
                        perp_aliases.extend(al.get_value().value.value
                                            for al in aliases)

                    perp_names.append(perp.name.get_value().value)

            perp_orgs = violation.perpetratororganization.get_list()
            perp_org_names, perp_org_aliases = [], []
            perp_org_count = 0
            if perp_orgs:
                # Move from PerpetratorOrganization -> Organization
                perp_orgs = list(perp.get_value().value for perp in perp_orgs)
                perp_org_count = len(perp_orgs)
                for perp in perp_orgs:

                    org_aliases = perp.aliases.get_list()
                    if org_aliases:
                        perp_org_aliases.extend(al.get_value().value.value
                                                for al in org_aliases)

                    perp_org_names.append(perp.name.get_value().value)

            perp_org_classes = list(cls.value.value for cls in
                                    violation.violationperpetratorclassification_set.all())
            perp_org_class_count = len(perp_org_classes)

            division_id = violation.division_id.get_value()
            country = []
            if division_id:
                country = [country_name(division_id)]
            else:
                division_id = []

            location_description = violation.locationdescription.get_value()
            if location_description:
                location_description = location_description.value

            location_name = violation.location_name.get_value()
            if location_name:
                location_name = location_name.value

            osmname = violation.osmname.get_value()
            if osmname:
                osmname = osmname.value

            admin_l1_name = violation.adminlevel1.get_value()
            if admin_l1_name:
                admin_l1_name = admin_l1_name.value

            admin_l2_name = violation.adminlevel2.get_value()
            if admin_l2_name:
                admin_l2_name = admin_l2_name.value

            start_date = self.format_date(violation.startdate.get_value())
            end_date = self.format_date(violation.enddate.get_value())
            first_allegation = self.format_date(violation.first_allegation.get_value())
            last_update = self.format_date(violation.last_update.get_value())

            status = violation.status.get_value()
            if status:
                status = status.value

            global_index = [perp_names, perp_aliases, perp_org_names, perp_org_aliases,
                            perp_org_classes, vtypes, country]

            # We need to make solo attributes into lists to extend the `content`
            # list; before doing that, check to see that each attribute actually
            # exists
            for single_attr in (description, location_description,
                                location_name, osmname, admin_l1_name,
                                admin_l2_name):
                if single_attr:
                    global_index.append([single_attr])

            for attr in global_index:
                content.extend(attr)

            content = '; '.join(content)

            document = {
                'id': viol_id,
                'entity_type': 'Violation',
                'content': content,
                'location': '',
                'country_ss': country,
                'division_id_ss': division_id,
                'start_date_dt': start_date,
                'end_date_dt': end_date,
                'violation_type_ss': vtypes,
                'violation_type_count_i': vtype_count,
                'violation_description_t': description,
                'violation_start_date_dt': start_date,
                'violation_end_date_dt': end_date,
                'violation_first_allegation_dt': first_allegation,
                'violation_last_update_dt': last_update,
                'violation_status_s': status,
                'violation_location_description_s': location_description,
                'violation_location_name_s': location_name,
                'violation_osmname_s': osmname,
                'violation_adminlevel1_s': admin_l1_name,
                'violation_adminlevel2_s': admin_l2_name,
                'perpetrator_ss': perps,
                'perpetrator_count_i': perp_count,
                'perpetrator_alias_ss': perp_aliases,
                'perpetrator_organization_ss': perp_orgs,
                'perpetrator_organization_count_i': perp_org_count,
                'perpetrator_organization_alias_ss': perp_org_aliases,
                'perpetrator_classification_ss': perp_org_classes,
                'perpetrator_classification_count_i': perp_org_class_count,
                'text': content
            }

            documents.append(document)

            if update:
                self.updated_count += 1
            else:
                self.added_count += 1

        self.add_to_index(documents)

    def index_sources(self, doc_id=None, update=False):
        self.stdout.write(self.style.HTTP_NOT_MODIFIED('\n Indexing sources ... '))

        source_query= '''
            SELECT
              uuid,
              MAX(title) AS title,
              MAX(source_url) AS url,
              MAX(published_on)::timestamp as date_published,
              MAX(publication) AS publication,
              MAX(publication_country) AS publication_country
            FROM source_source
        '''

        if doc_id:
            source_query += '''
                WHERE uuid = '{doc_id}'
            '''.format(doc_id=doc_id)

        source_query += '''
            GROUP BY uuid
        '''

        source_cursor = connection.cursor()
        source_cursor.execute(source_query)
        source_columns = [c[0] for c in source_cursor.description]

        documents = []

        for source in source_cursor:

            source = dict(zip(source_columns, source))

            if update and self.check_index(source['id']):
                continue

            date_published = source['date_published'].strftime('%Y-%m-%dT%H:%M:%SZ')

            content = source['title']

            if len(content) == 0:
                # The import data script is missing one title - skip it for now
                continue

            document = {
                'id': source['uuid'],
                'entity_type': 'Source',
                'content': content,
                'source_url_t': source['url'],
                'source_title_t': source['title'],
                'start_date_dt': date_published,
                'end_date_dt': date_published,
                'publication_s': source['publication'],
                'country_s': source['publication_country'],
                'country_ss': source['publication_country'],
                'text': content
            }

            documents.append(document)

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
