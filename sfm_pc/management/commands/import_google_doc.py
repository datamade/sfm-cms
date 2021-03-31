import os
import io
import itertools
from datetime import datetime
import csv

import httplib2
import boto3

from oauth2client.service_account import ServiceAccountCredentials
from apiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from tqdm import tqdm

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import models, IntegrityError
from django.core.management import call_command
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.conf import settings

from django_date_extensions.fields import ApproximateDateField

import reversion

from countries_plus.models import Country

from haystack import connection_router, connections
from haystack.signals import RealtimeSignalProcessor

from source.models import Source, AccessPoint
from organization.models import Organization, OrganizationRealStart

from sfm_pc.utils import (import_class, CONFIDENCE_MAP, execute_sql)

from emplacement.models import Emplacement, EmplacementRealStart
from association.models import Association, AssociationRealStart
from composition.models import Composition, CompositionRealStart
from person.models import Person
from personextra.models import PersonExtra
from personbiography.models import PersonBiography
from membershipperson.models import (MembershipPerson, Role, Rank,
                                     MembershipPersonRealStart,
                                     MembershipPersonRealEnd)
from membershiporganization.models import (MembershipOrganization,
                                           MembershipOrganizationRealStart)
from violation.models import Violation, ViolationPerpetrator, \
    ViolationPerpetratorOrganization

from location.models import Location


class Command(BaseCommand):
    help = 'Import data from Google Drive Spreadsheet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--doc_id',
            dest='doc_id',
            default='1o-K13Od1pGc7FOQ-JS8LJW9Angk3_UPZHTmOU7hD3wU',
            help='Import data from specified Google Drive Document'
        )
        parser.add_argument(
            '--source_doc_id',
            dest='source_doc_id',
            default='15lChqP4cKsjk8uUbUTaUA5gOUM09-t9YMIODORHw--8',
            help='Import source data from specified Google Drive Document'
        )
        parser.add_argument(
            '--location_doc_id',
            dest='location_doc_id',
            default=None,
            help='Import location data from specified Google Drive file'
        )
        parser.add_argument(
            '--entity-types',
            dest='entity_types',
            default='organization,person,person_extra,event',
            help='Comma separated list of entity types to import'
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            dest='flush',
            default=False,
            help='Flush the existing database before importing data.'
        )
        parser.add_argument(
            '--start',
            dest='start',
            default=1,
            help='First row to begin parsing (for debugging)'
        )
        parser.add_argument(
            '--folder',
            dest='folder',
            help='Path to a folder containing data (for testing)'
        )

    def sourcesList(self, obj, attribute):
        sources = [s for s in getattr(obj, attribute).get_sources()]
        return list(set(s for s in sources if s))

    def get_credentials(self, *, scopes, credentials_file='credentials.json'):
        '''make sure relevant accounts have access to the sheets at console.developers.google.com'''

        this_dir = os.path.dirname(__file__)
        secrets_path = os.path.join(this_dir, credentials_file)

        client = boto3.resource('s3')
        client.Object('wwic-secrets', 'credentials.json').download_file(secrets_path)

        credentials = ServiceAccountCredentials.from_json_keyfile_name(secrets_path,
                                                                       scopes)
        return credentials

    def disconnectSignals(self):
        from django.db.models.signals import post_save
        from complex_fields.base_models import object_ref_saved
        from sfm_pc.signals import update_membership_index, update_composition_index

        object_ref_saved.disconnect(receiver=update_membership_index, sender=MembershipPerson)
        object_ref_saved.disconnect(receiver=update_composition_index, sender=Composition)

        self.haystack_signal_processor.teardown()

    def connectSignals(self):
        from django.db.models.signals import post_save
        from complex_fields.base_models import object_ref_saved
        from sfm_pc.signals import update_membership_index, update_composition_index

        object_ref_saved.connect(receiver=update_membership_index, sender=MembershipPerson)
        object_ref_saved.connect(receiver=update_composition_index, sender=Composition)

        self.haystack_signal_processor.setup()

    def handle(self, *args, **options):

        if options['flush']:
            self.stdout.write(self.style.SUCCESS('Dropping current database...'))

            # Flush database
            this_dir = os.path.abspath(os.path.dirname(__file__))
            flush_sql = os.path.join(this_dir, 'flush', 'flush.sql')

            execute_sql(flush_sql)

            # Recreate country codes
            call_command('update_countries_plus')

        # Get a handle on the "user" that will be doing the work
        importer_user = settings.IMPORTER_USER
        try:
            self.user = User.objects.create_user(importer_user['username'],
                                                 email=importer_user['email'],
                                                 password=importer_user['password'])
        except IntegrityError:
            self.user = User.objects.get(username=importer_user['username'])


        self.haystack_signal_processor = RealtimeSignalProcessor(connections,
                                                                 connection_router)
        # Disconnect post save signals
        self.disconnectSignals()

        if options.get('location_doc_id'):
            self.get_locations_from_drive(options['location_doc_id'])
            self.create_locations()

        if options.get('folder'):
            self.stdout.write('Loading data from folder {}...'.format(options['folder']))
            all_sheets = self.get_sheets_from_folder(options['folder'])
        else:
            self.stdout.write('Loading data from Google Sheets...')
            all_sheets = self.get_sheets_from_doc(options['doc_id'], options['source_doc_id'])

        self.create_sources(all_sheets['source'])

        skippers = ['Play Copy of Events']
        one_index_start = int(options['start'])
        zero_index_start = one_index_start - 1

        # These are used for the mapping that we need to make below
        entity_mapping_entities = [
            ('organization', 'unit:id:admin', 'unit:name'),
            ('person', 'person:id:admin', 'person:name'),
        ]

        # Create entity maps for persons and units
        for entity_type, id_key, name_key in entity_mapping_entities:

            sheets = all_sheets[entity_type]

            for sheet in sheets.values():

                entity_map = {}

                for idx, row in enumerate(sheet[zero_index_start:]):
                    if row:
                        entity_uuid = row[id_key]
                        try:
                            entity_name = row[name_key]
                        except KeyError:
                            self.log_error(
                                'Entity with ID "{}" is missing a name'.format(
                                    entity_uuid
                                ),
                                sheet=entity_type,
                                current_row=one_index_start + (idx + 1)
                            )
                        if entity_uuid:
                            entity_map[entity_name] = entity_uuid

                setattr(self, '{}_entity_map'.format(entity_type), entity_map)

        for entity_type in options['entity_types'].split(','):

            sheets = all_sheets[entity_type]

            for title, sheet in sheets.items():

                self.stdout.write(self.style.SUCCESS('Creating {0}s from {1} ... '.format(entity_type, title)))
                self.current_sheet = title

                if title not in skippers:
                    for index, row in enumerate(sheet[zero_index_start:]):
                        if row:
                            self.current_row = one_index_start + (index + 1)
                            getattr(self, 'create_{}'.format(entity_type))(row)

        data_src = options['folder'] if options.get('folder') else options['doc_id']
        self.stdout.write(self.style.SUCCESS('Successfully imported data from {}'.format(data_src)))
        # connect post save signals
        self.connectSignals()

    def create_locations(self):
        this_dir = os.path.abspath(os.path.dirname(__file__))
        location_file = os.path.join(this_dir, 'data', 'locations.geojson')
        call_command('import_locations', location_file=location_file)

    def get_locations_from_drive(self, location_doc_id):
        credentials = self.get_credentials(
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=credentials)
        request = service.files().get_media(fileId=location_doc_id)

        location_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(location_buffer, request)
        done = False

        self.stdout.write('Downloading locations file...')

        with tqdm(total=100) as progress_bar:
            while done is False:
                status, done = downloader.next_chunk()
                progress_bar.update(int(status.progress() * 100) - progress_bar.n)

        location_buffer.seek(0)

        this_dir = os.path.abspath(os.path.dirname(__file__))
        location_file = os.path.join(this_dir, 'data', 'locations.geojson')

        with open(location_file, 'wb') as f:
            f.write(location_buffer.getbuffer())

        self.stdout.write(
            self.style.SUCCESS('Downloaded locations file to {}'.format(location_file))
        )

    def get_sheets_from_doc(self, doc_id, source_doc_id):
        """
        Load data from Google Sheets. Required params include a Google Doc ID
        for top-level entities and a Doc ID for sources.
        """
        credentials = self.get_credentials(
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        http = credentials.authorize(httplib2.Http())
        service = build('sheets', 'v4', http=http)

        result = service.spreadsheets().get(
            spreadsheetId=doc_id,
            includeGridData=False
        ).execute()
        sheets = result['sheets']
        sheet_mapping = {}

        for sheet in sheets:
            title = sheet['properties']['title']
            sheet_data = service.spreadsheets().values().get(
                spreadsheetId=doc_id,
                range=title
            ).execute()
            sheet_mapping[title] = sheet_data['values']

        org_sheets = {}
        person_sheets = {}
        person_extra_sheets = {}
        event_sheets = {}

        for title, data in sheet_mapping.items():
            if 'scratch' in title.lower() or 'analysis' in title.lower():
                continue

            elif 'units' in title.lower():
                org_sheets[title] = self.format_dict_reader(data)

            elif 'persons_extra' in title.lower():
                person_extra_sheets[title] = self.format_dict_reader(data)

            elif 'persons' in title.lower():
                person_sheets[title] = self.format_dict_reader(data)

            elif 'incidents' in title.lower():
                event_sheets[title] = self.format_dict_reader(data)

        # Get data about sources
        source_data = service.spreadsheets().values().get(
            spreadsheetId=source_doc_id,
            range='sources'
        ).execute()
        # Convert the raw response to a DictReader
        source_sheet = {'values': self.format_dict_reader(source_data['values'])}

        return {
            'organization': org_sheets,
            'person': person_sheets,
            'person_extra': person_extra_sheets,
            'event': event_sheets,
            'source': source_sheet,
        }

    def get_sheets_from_folder(self, folder):
        """
        Load data from a folder on disk. Data must be stored as CSV files with the
        name of the entities represented therein (e.g. 'person.csv') and must be
        stored under the directory represented by the path string 'folder'.
        """
        all_sheets = {}
        entities = (
            ('organization', 'units', 'orgs'),
            ('person', 'persons', 'persons'),
            ('person_extra', 'persons_extra', 'persons_extra'),
            ('event', 'incidents', 'events'),
            ('source', 'sources', 'values')
        )
        for entity_type, filename, title in entities:
            path = os.path.join(folder, filename + '.csv')
            if not os.path.isfile(path):
                raise OSError('Required file {path} not found.'.format(path=path))

            with open(path) as fobj:
                reader = csv.reader(fobj)
                # We could use csv.DictReader directly here, but instead use
                # the format_dict_reader convenience method to test it
                records = self.format_dict_reader(list(reader))

            # Match the Google Sheets API response format
            all_sheets[entity_type] = {title: records}

        return all_sheets

    def format_dict_reader(self, lst):
        """
        Format a nested list, 'lst', as a list of dictionaries (like a
        csv.DictReader object).
        """
        header = lst[0]
        # Use itertools.zip_longest to preserve all of the header fields. This
        # is important because if every cell after the ith column in a row is
        # empty, the API will truncate the row at the ith cell when it returns
        # a response, leading the built-in zip() function to leave out those
        # elements (zip() will default to the length of the shortest iterable).
        return [dict(itertools.zip_longest(header, row, fillvalue='')) for row in lst[1:]]

    def log_error(self, message, sheet=None, current_row=None):
        current_sheet = sheet if sheet is not None else self.current_sheet
        current_row = current_row if current_row is not None else self.current_row
        log_message = message + ' (context: Sheet {0}, Row {1})'.format(current_sheet, current_row)
        self.stdout.write(self.style.ERROR(log_message))
        file_name = '{}-errors.csv'.format(slugify(current_sheet))
        if not os.path.isfile(file_name):
            with open(file_name, 'w') as f:
                header = ['row', 'message']
                writer = csv.writer(f)
                writer.writerow(header)

        with open(file_name, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([current_row,
                             message])

    def get_confidence(self, confidence_key):
        key = confidence_key.strip().lower()
        if key:
            try:
                return CONFIDENCE_MAP[key]
            except KeyError:
                self.log_error("Invalid confidence value '{}'".format(key))
        else:
            return 1

    def parse_date(self, value):
        parsed = None

        # Map legal input formats to the way that we want to
        # store them in the database
        formats = {
            '%Y-%m-%d': '%Y-%m-%d',
            '%Y': '%Y-0-0',
            '%Y-%m': '%Y-%m-0',
            '%B %Y': '%Y-%m-0',
            '%m/%Y': '%Y-%m-0',
            '%m/%d/%Y': '%Y-%m-%d',
        }

        for in_format, out_format in formats.items():
            try:
                parsed_input = datetime.strptime(value, in_format)

                if datetime.today() < parsed_input:
                    self.log_error('Date {value} is in the future'.format(value=value))
                    return None

                parsed = datetime.strftime(parsed_input, out_format)
                break
            except ValueError:
                pass

        return parsed

    def create_organization(self, org_data):
        organization = None

        org_positions = {
            'Name': {
                'value': Organization.get_spreadsheet_field_name('name'),
                'confidence': Organization.get_spreadsheet_confidence_field_name('name'),
                'source': Organization.get_spreadsheet_source_field_name('name'),
            },
            'Alias': {
                'value': Organization.get_spreadsheet_field_name('aliases'),
                'confidence': Organization.get_spreadsheet_confidence_field_name('aliases'),
                'source': Organization.get_spreadsheet_source_field_name('aliases'),
            },
            'Classification': {
                'value': Organization.get_spreadsheet_field_name('classification'),
                'confidence': Organization.get_spreadsheet_confidence_field_name('classification'),
                'source': Organization.get_spreadsheet_source_field_name('classification'),
            },
            'DivisionId': {
                'value': Organization.get_spreadsheet_field_name('division_id'),
                'confidence': Organization.get_spreadsheet_confidence_field_name('division_id'),
                'source': Organization.get_spreadsheet_source_field_name('division_id'),
            },
            'FirstCitedDate': {
                'value': Organization.get_spreadsheet_field_name('firstciteddate'),
                'day': Organization.get_spreadsheet_field_name('firstciteddate') + '_day',
                'month': Organization.get_spreadsheet_field_name('firstciteddate') + '_month',
                'year': Organization.get_spreadsheet_field_name('firstciteddate') + '_year',
                'confidence': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'source': Organization.get_spreadsheet_source_field_name('firstciteddate'),
            },
            'RealStart': {
                'value': Organization.get_spreadsheet_field_name('realstart'),
                'confidence': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'source': None,
            },
            'LastCitedDate': {
                'value': Organization.get_spreadsheet_field_name('lastciteddate'),
                'day': Organization.get_spreadsheet_field_name('lastciteddate') + '_day',
                'month': Organization.get_spreadsheet_field_name('lastciteddate') + '_month',
                'year': Organization.get_spreadsheet_field_name('lastciteddate') + '_year',
                'confidence': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'source': Organization.get_spreadsheet_source_field_name('lastciteddate'),
            },
            'OpenEnded': {
                'value': Organization.get_spreadsheet_field_name('open_ended'),
                'confidence': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'source': None,
            },
            'Headquarters': {
                'value': Organization.get_spreadsheet_field_name('headquarters'),
                'confidence': Organization.get_spreadsheet_confidence_field_name('headquarters'),
                'source': Organization.get_spreadsheet_source_field_name('headquarters'),
            }
        }

        composition_positions = {
            'Parent': {
                'value': Composition.get_spreadsheet_field_name('parent'),
                'confidence': Composition.get_spreadsheet_confidence_field_name('parent'),
                'source': Composition.get_spreadsheet_source_field_name('parent'),
            },
            'Classification': {
                'value': Composition.get_spreadsheet_field_name('classification'),
                'confidence': Composition.get_spreadsheet_confidence_field_name('classification'),
                'source': Composition.get_spreadsheet_source_field_name('classification'),
            },
            'StartDate': {
                'value': Composition.get_spreadsheet_field_name('startdate'),
                'day': Composition.get_spreadsheet_field_name('startdate') + '_day',
                'month': Composition.get_spreadsheet_field_name('startdate') + '_month',
                'year': Composition.get_spreadsheet_field_name('startdate') + '_year',
                'confidence': Composition.get_spreadsheet_confidence_field_name('startdate'),
                'source': Composition.get_spreadsheet_source_field_name('startdate'),
            },
            'RealStart': {
                'value': Composition.get_spreadsheet_field_name('realstart'),
                'confidence': Composition.get_spreadsheet_confidence_field_name('startdate'),
                'source': None,
            },
            'EndDate': {
                'value': Composition.get_spreadsheet_field_name('enddate'),
                'day': Composition.get_spreadsheet_field_name('enddate') + '_day',
                'month': Composition.get_spreadsheet_field_name('enddate') + '_month',
                'year': Composition.get_spreadsheet_field_name('enddate') + '_year',
                'confidence': Composition.get_spreadsheet_confidence_field_name('enddate'),
                'source': Composition.get_spreadsheet_source_field_name('enddate'),
            },
            'OpenEnded': {
                'value': Composition.get_spreadsheet_field_name('open_ended'),
                'confidence': Composition.get_spreadsheet_confidence_field_name('enddate'),
                'source': None,
            },
        }

        location_positions = {
            'Location': {
                'value': 'unit:location',
                'confidence': 'unit:location:confidence',
                'source': 'unit:location:source',
                'type': 'unit:location_type',
            }
        }

        membership_positions = {
            'OrganizationOrganization': {
                'value': MembershipOrganization.get_spreadsheet_field_name('organization'),
                'confidence': MembershipOrganization.get_spreadsheet_confidence_field_name('organization'),
                'source': MembershipOrganization.get_spreadsheet_source_field_name('organization'),
            },
            'FirstCitedDate': {
                'value': MembershipOrganization.get_spreadsheet_field_name('firstciteddate'),
                'day': MembershipOrganization.get_spreadsheet_field_name('firstciteddate') + '_day',
                'month': MembershipOrganization.get_spreadsheet_field_name('firstciteddate') + '_month',
                'year': MembershipOrganization.get_spreadsheet_field_name('firstciteddate') + '_year',
                'confidence': MembershipOrganization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'source': MembershipOrganization.get_spreadsheet_source_field_name('firstciteddate'),
            },
            'RealStart': {
                'value': MembershipOrganization.get_spreadsheet_field_name('realstart'),
                'confidence': MembershipOrganization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'source': None,
            },
            'LastCitedDate': {
                'value': MembershipOrganization.get_spreadsheet_field_name('lastciteddate'),
                'day': MembershipOrganization.get_spreadsheet_field_name('lastciteddate') + '_day',
                'month': MembershipOrganization.get_spreadsheet_field_name('lastciteddate') + '_month',
                'year': MembershipOrganization.get_spreadsheet_field_name('lastciteddate') + '_year',
                'confidence': MembershipOrganization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'source': MembershipOrganization.get_spreadsheet_source_field_name('lastciteddate'),
            },
            'OpenEnded': {
                'value': MembershipOrganization.get_spreadsheet_field_name('open_ended'),
                'confidence': MembershipOrganization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'source': None,
            },
        }

        # Need to get or create name first

        try:
            name_value = org_data[org_positions['Name']['value']]
            confidence = org_data[org_positions['Name']['confidence']]
            source = org_data[org_positions['Name']['source']]
        except IndexError:
            self.log_error('Row seems to be empty')
            return None

        # Skip this row if it's not ready for import
        admin_status = org_data['unit:status:admin']
        if admin_status != '3':
            self.stdout.write('Skipping unit "{}" because its status is {}'.format(
                name_value,
                admin_status
            ))
            return None

        try:
            country_code = org_data[org_positions['DivisionId']['value']]
        except IndexError:
            self.log_error('Country code missing')
            return None

        if confidence and source:

            try:
                confidence = self.get_confidence(confidence)
            except KeyError:
                confidence = None

            sources = self.get_sources(source)
            self.stdout.write(self.style.SUCCESS('Working on {}'.format(name_value)))

            if confidence and sources:

                division_id = 'ocd-division/country:{}'.format(country_code)
                division_confidence = self.get_confidence(
                    org_data[org_positions['DivisionId']['confidence']]
                )
                division_sources = self.get_sources(
                    org_data[org_positions['DivisionId']['source']]
                )

                org_info = {
                    'Organization_OrganizationName': {
                        'value': name_value,
                        'confidence': confidence,
                        'sources': sources.copy()
                    },
                    'Organization_OrganizationDivisionId': {
                        'value': division_id,
                        'confidence': division_confidence,
                        'sources': division_sources,
                    }
                }

                try:
                    uuid = self.organization_entity_map[name_value]
                except KeyError:
                    self.log_error('Could not find "{}" in list of organization names'.format(name_value))
                    return None

                try:
                    organization = Organization.objects.get(uuid=uuid)
                except Organization.DoesNotExist:
                    organization = Organization.objects.create(uuid=uuid,
                                                               published=True)
                except ValidationError:
                    self.log_error('Invalid unit UUID: "{}"'.format(uuid))
                    return None
                else:
                    existing_sources = self.sourcesList(organization, 'name')
                    org_info["Organization_OrganizationName"]['sources'] += existing_sources

                organization.update(org_info)

                org_attributes = ['Alias', 'Classification', 'OpenEnded', 'Headquarters']

                for attr in org_attributes:

                    self.make_relation(attr,
                                       org_positions[attr],
                                       org_data,
                                       organization)

                self.make_relation('FirstCitedDate',
                                   org_positions['FirstCitedDate'],
                                   org_data,
                                   organization,
                                   date=True)

                self.make_relation('LastCitedDate',
                                   org_positions['LastCitedDate'],
                                   org_data,
                                   organization,
                                   date=True)

                self.make_real_date(data=org_data,
                                    position=org_positions['RealStart']['value'],
                                    model=OrganizationRealStart,
                                    attribute='realstart',
                                    object_ref=organization)

                if org_data[location_positions['Location']['type']] == 'aoo':
                    # Create Area

                    try:
                        humane_id = org_data[location_positions['Location']['value']]
                    except IndexError:
                        humane_id = None

                    if humane_id:

                        self.make_area(humane_id,
                                       org_data,
                                       organization)

                elif org_data[location_positions['Location']['type']] == 'site':
                    # Create Emplacement

                    try:
                        site_osm_id = org_data[location_positions['Location']['value']]
                    except IndexError:
                        site_osm_id = None

                    if site_osm_id:

                        self.make_emplacement(site_osm_id,
                                              org_data,
                                              organization)

                if org_data['unit:relation_type'] == 'child':
                    # Create Compositions

                    try:
                        parent_org_name = org_data[composition_positions['Parent']['value']]
                    except IndexError:
                        parent_org_name = None

                    if parent_org_name:

                        try:
                            parent_confidence = self.get_confidence(org_data[composition_positions['Parent']['confidence']])
                        except (IndexError, KeyError):
                            self.log_error('Parent organization for {} does not have confidence'.format(organization.name))
                            parent_confidence = None

                        try:
                            parent_sources = self.get_sources(org_data[composition_positions['Parent']['source']])
                        except IndexError:
                            self.log_error('Parent organization for {} does not have a source'.format(organization.name))
                            parent_sources = None

                        if parent_confidence and parent_sources:
                            parent_org_info = {
                                'Organization_OrganizationName': {
                                    'value': parent_org_name,
                                    'confidence': parent_confidence,
                                    'sources': parent_sources
                                },
                                'Organization_OrganizationDivisionId': {
                                    'value': division_id,
                                    'confidence': division_confidence,
                                    'sources': division_sources,
                                },
                            }

                            try:
                                uuid = self.organization_entity_map[parent_org_name]
                            except KeyError:
                                self.log_error('Could not find "{}" in list of organization names'.format(parent_org_name))
                                return None

                            try:
                                parent_organization = Organization.objects.get(uuid=uuid)
                            except Organization.DoesNotExist:
                                parent_organization = Organization.objects.create(uuid=uuid,
                                                                                  published=True)
                            except ValidationError:
                                self.log_error('Invalid parent unit UUID: "{}"'.format(uuid))
                                return None
                            else:
                                existing_sources = self.sourcesList(parent_organization, 'name')
                                parent_org_info["Organization_OrganizationName"]['sources'] += existing_sources

                            parent_organization.update(parent_org_info)

                            comp_info = {
                                'Composition_CompositionParent': {
                                    'value': parent_organization,
                                    'confidence': parent_confidence,
                                    'sources': parent_sources
                                },
                                'Composition_CompositionChild': {
                                    'value': organization,
                                    'confidence': parent_confidence,
                                    'sources': parent_sources,
                                },
                            }

                            try:
                                composition = Composition.objects.get(compositionparent__value=parent_organization,
                                                                      compositionchild__value=organization)
                            except Composition.DoesNotExist:
                                composition = Composition.create(comp_info)

                            self.make_relation('StartDate',
                                               composition_positions['StartDate'],
                                               org_data,
                                               composition,
                                               date=True)

                            self.make_relation('EndDate',
                                               composition_positions['EndDate'],
                                               org_data,
                                               composition,
                                               date=True)

                            self.make_real_date(data=org_data,
                                                position=composition_positions['RealStart']['value'],
                                                model=CompositionRealStart,
                                                attribute='realstart',
                                                object_ref=composition)

                            self.make_relation('OpenEnded',
                                               composition_positions['OpenEnded'],
                                               org_data,
                                               composition)

                            self.make_relation('Classification',
                                               composition_positions['Classification'],
                                               org_data,
                                               composition)

                        else:
                            self.log_error('Parent organization for {} does not have source or confidence'.format(organization.name))

                elif org_data['unit:relation_type'] == 'member':
                    # Make memberships

                    try:
                        member_org_name = org_data[membership_positions['OrganizationOrganization']['value']]
                    except IndexError:
                        member_org_name = None

                    if member_org_name:
                        try:
                            confidence = self.get_confidence(org_data[membership_positions['OrganizationOrganization']['confidence']])
                        except (IndexError, KeyError):
                            self.log_error('Member organization for {} does not have confidence'.format(member_org_name))
                            confidence = None

                        try:
                            sources = self.get_sources(org_data[membership_positions['OrganizationOrganization']['source']])
                        except IndexError:
                            self.log_error('Member organization for {} does not have a source'.format(member_org_name))
                            sources = None

                        if confidence and sources:

                            member_org_info = {
                                'Organization_OrganizationName': {
                                    'value': member_org_name,
                                    'confidence': confidence,
                                    'sources': sources.copy(),
                                },
                                'Organization_OrganizationDivisionId': {
                                    'value': division_id,
                                    'confidence': division_confidence,
                                    'sources': division_sources,
                                },
                            }

                            try:
                                uuid = self.organization_entity_map[member_org_name]
                            except KeyError:
                                self.log_error('Could not find "{}" in list of organization names'.format(member_org_name))
                                return None

                            try:
                                member_organization = Organization.objects.get(uuid=uuid)
                            except Organization.DoesNotExist:
                                member_organization = Organization.objects.create(uuid=uuid,
                                                                                  published=True)
                            except ValidationError:
                                self.log_error('Invalid member unit UUID: "{}"'.format(uuid))
                                return None
                            else:
                                existing_sources = self.sourcesList(member_organization, 'name')
                                member_org_info["Organization_OrganizationName"]['sources'] += existing_sources

                            member_organization.update(member_org_info)

                            membership_info = {
                                'MembershipOrganization_MembershipOrganizationMember': {
                                    'value': organization,
                                    'confidence': confidence,
                                    'sources': sources.copy()
                                },
                                'MembershipOrganization_MembershipOrganizationOrganization': {
                                    'value': member_organization,
                                    'confidence': confidence,
                                    'sources': sources.copy()
                                },
                            }

                            try:
                                date_parts = [
                                    org_data[membership_positions['FirstCitedDate']['year']],
                                    org_data[membership_positions['FirstCitedDate']['month']],
                                    org_data[membership_positions['FirstCitedDate']['day']]
                                ]
                                fcd = self.parse_date('-'.join(filter(None, date_parts)))
                            except IndexError:
                                fcd = None

                            try:
                                date_parts = [
                                    org_data[membership_positions['LastCitedDate']['year']],
                                    org_data[membership_positions['LastCitedDate']['month']],
                                    org_data[membership_positions['LastCitedDate']['day']]
                                ]
                                lcd = self.parse_date('-'.join(filter(None, date_parts)))
                            except IndexError:
                                lcd = None

                            try:
                                membership = MembershipOrganization.objects.get(membershiporganizationmember__value=organization,
                                                                                membershiporganizationorganization__value=member_organization,
                                                                                membershiporganizationfirstciteddate__value=fcd,
                                                                                membershiporganizationlastciteddate__value=lcd)
                                sources = set(self.sourcesList(membership, 'member') + self.sourcesList(membership, 'organization'))
                                membership_info['MembershipOrganization_MembershipOrganizationMember']['sources'] += sources
                                membership.update(membership_info)

                            except MembershipOrganization.DoesNotExist:
                                membership = MembershipOrganization.create(membership_info)

                            self.make_relation('OpenEnded',
                                               membership_positions['OpenEnded'],
                                               org_data,
                                               membership)

                            self.make_relation('LastCitedDate',
                                               membership_positions['LastCitedDate'],
                                               org_data,
                                               membership,
                                               date=True)

                            self.make_relation('FirstCitedDate',
                                               membership_positions['FirstCitedDate'],
                                               org_data,
                                               membership,
                                               date=True)

                            self.make_real_date(data=org_data,
                                                position=membership_positions['RealStart']['value'],
                                                model=MembershipOrganizationRealStart,
                                                attribute='realend',
                                                object_ref=membership)

                            membership.save()

                        else:
                            self.log_error('Member organization for {} does not have source or confidence'.format(member_org_name))

                self.stdout.write(self.style.SUCCESS('Created {}'.format(organization.get_value())))

            else:
                self.log_error('{} did not have a confidence or source'.format(name_value))

        else:
            missing = []
            if not confidence:
                missing.append('confidence')
            if not source:
                missing.append('sources')

            self.log_error('{0} did not have {1}'.format(name_value, ', '.join(missing)))

        return organization

    def make_relation(self,
                      field_name,
                      positions,
                      data,
                      instance,
                      required=False,
                      require_confidence=True,
                      date=False,
                      multiple=True):

        value_position = positions['value']

        if not require_confidence:
            confidence_required = False
        else:
            confidence_required = instance.confidence_required

        try:
            confidence_position = positions['confidence']
        except KeyError:
            confidence_position = None

            if confidence_required:
                self.log_error('No confidence for {}'.format(field_name))
                return None

        source_position = positions['source']

        try:
            if not date:
                value = data[value_position]
            else:
                date_parts = [
                    data[value_position + '_year'],
                    data[value_position + '_month'],
                    data[value_position + '_day']
                ]
                value = '-'.join(filter(None, date_parts))
            value = value.strip()
        except IndexError:
            value = None

        if required and not value:
            self.log_error('No {0} information for {1}'.format(field_name, instance.get_value()))
            return None

        elif value:

            app_name = instance._meta.model_name
            model_name = instance._meta.object_name

            import_path = '{app_name}.models.{model_name}{field_name}'

            relation_path = import_path.format(app_name=app_name,
                                               model_name=model_name,
                                               field_name=field_name)

            relation_model = import_class(relation_path)

            source_required = getattr(relation_model, 'source_required', False)

            try:
                confidence = self.get_confidence(data[confidence_position])
            except (KeyError, IndexError, TypeError):
                confidence = 1
                if confidence_required:
                    self.log_error('No confidence for {}'.format(field_name))
                    return None

            if not source_position:

                if source_required:
                    self.log_error('No source for {}'.format(field_name))
                    return None
                else:
                    sources = []
            else:

                try:
                    sources = self.get_sources(data[source_position])
                except IndexError:
                    if source_required:
                        self.log_error('No source for {}'.format(field_name))
                        return None
                    else:
                        sources = []

            if (sources or not source_required) and (confidence or not confidence_required):

                if isinstance(relation_model._meta.get_field('value'), models.ForeignKey):
                    value_rel_path_fmt = '{app_name}.models.{field_name}'
                    value_rel_path = value_rel_path_fmt.format(app_name=app_name,
                                                               field_name=field_name)

                    try:
                        value_model = import_class(value_rel_path)
                    except AttributeError:
                        value_rel_path = value_rel_path_fmt.format(app_name=app_name,
                                                                   field_name='Context')
                        value_model = import_class(value_rel_path)

                    # Split on semicolons if multiple values are supported
                    values = [value] if not multiple else [val.strip() for val in value.split(';') if val.strip()]
                    for value_text in values:

                        value_obj, created = value_model.objects.get_or_create(value=value_text)

                        relation_instance, created = relation_model.objects.get_or_create(value=value_obj,
                                                                                          object_ref=instance,
                                                                                          lang='en')
                        if created:

                            for source in sources:
                                relation_instance.accesspoints.add(source)
                                relation_instance.sources.add(source.source)

                            with reversion.create_revision():
                                relation_instance.confidence = confidence
                                relation_instance.save()
                                reversion.set_user(self.user)

                elif isinstance(relation_model._meta.get_field('value'), ApproximateDateField):
                    parsed_value = self.parse_date(value)

                    if parsed_value:
                        relation_instance, created = relation_model.objects.get_or_create(value=parsed_value,
                                                                                          object_ref=instance,
                                                                                          lang='en')
                        if created:

                            for source in sources:
                                relation_instance.accesspoints.add(source)
                                relation_instance.sources.add(source.source)

                            with reversion.create_revision():
                                relation_instance.confidence = confidence
                                relation_instance.save()
                                reversion.set_user(self.user)

                    else:
                        self.log_error('Expected a date for {app_name}.models.{field_name} but got {value}'.format(app_name=app_name,
                                                                                                                   field_name=field_name,
                                                                                                                   value=value))
                        return None

                else:

                    # Split on semicolons if multiple values are supported.
                    values = [value] if not multiple else [val.strip() for val in value.split(';') if val.strip()]
                    for val in values:
                        relation_instance, created = relation_model.objects.get_or_create(value=val.strip(),
                                                                                          object_ref=instance,
                                                                                          lang='en')
                        if created:

                            for source in sources:
                                relation_instance.accesspoints.add(source)
                                relation_instance.sources.add(source.source)

                            with reversion.create_revision():
                                relation_instance.confidence = confidence
                                relation_instance.save()
                                reversion.set_user(self.user)

            else:
                missing = []
                if not confidence and instance.confidence_required:
                    missing.append('confidence')
                if not sources:
                    missing.append('sources')

                message = '{field_name} from {app_name}.{model_name} does not have {missing}'.format(field_name=field_name,
                                                                                                     app_name=app_name,
                                                                                                     model_name=model_name,
                                                                                                     missing=', '.join(missing))
                self.log_error(message)

            return None

    def make_area(self, humane_id, org_data, organization):

        positions = {
            'Location': {
                'value': 'unit:location',
                'confidence': 'unit:location:confidence',
                'source': 'unit:location:source',
            }
        }

        relation_positions = {
            'StartDate': {
                'value': Association.get_spreadsheet_field_name('startdate'),
                'day': Association.get_spreadsheet_field_name('startdate') + '_day',
                'month': Association.get_spreadsheet_field_name('startdate') + '_month',
                'year': Association.get_spreadsheet_field_name('startdate') + '_year',
                'confidence': Association.get_spreadsheet_confidence_field_name('startdate'),
                'source': Association.get_spreadsheet_source_field_name('startdate'),
            },
            'RealStart': {
                'value': Association.get_spreadsheet_field_name('realstart'),
                'confidence': Association.get_spreadsheet_confidence_field_name('startdate'),
                'source': None,
            },
            'EndDate': {
                'value': Association.get_spreadsheet_field_name('enddate'),
                'day': Association.get_spreadsheet_field_name('enddate') + '_day',
                'month': Association.get_spreadsheet_field_name('enddate') + '_month',
                'year': Association.get_spreadsheet_field_name('enddate') + '_year',
                'confidence': Association.get_spreadsheet_confidence_field_name('enddate'),
                'source': Association.get_spreadsheet_source_field_name('enddate'),
            },
            'OpenEnded': {
                'value': Association.get_spreadsheet_field_name('open_ended'),
                'confidence': Association.get_spreadsheet_confidence_field_name('enddate'),
                'source': None,
            },
        }

        try:
            area = Location.objects.from_humane_id(humane_id)

        except Location.DoesNotExist:
            self.log_error('Location "{0}" for Area for {1} does not exist'.format(humane_id, organization.name))
            return None

        try:
            area_confidence = self.get_confidence(org_data[positions['Location']['confidence']])
        except (IndexError, KeyError):
            self.log_error('Location for Area for {} does not have confidence'.format(organization.name))
            return None

        try:
            area_sources = self.get_sources(org_data[positions['Location']['source']])
        except IndexError:
            self.log_error('Location for Area for {} does not have source'.format(organization.name))
            return None

        area_info = {
            'Association_AssociationOrganization': {
                'value': organization,
                'confidence': area_confidence,
                'sources': area_sources
            },
            'Association_AssociationArea': {
                'value': area,
                'confidence': area_confidence,
                'sources': area_sources
            },
        }

        try:
            assoc = Association.objects.get(associationorganization__value=organization,
                                            associationarea__value=area)
            assoc.update(area_info)
        except Association.DoesNotExist:
            assoc = Association.create(area_info)

        for field_name, positions in relation_positions.items():

            if field_name == 'StartDate':
                self.make_relation(field_name,
                                   positions,
                                   org_data,
                                   assoc,
                                   date=True)

            elif field_name == 'EndDate':
                self.make_relation(field_name,
                                   positions,
                                   org_data,
                                   assoc,
                                   date=True)

            elif field_name == 'RealStart':
                self.make_real_date(data=org_data,
                                    position=positions['value'],
                                    model=AssociationRealStart,
                                    attribute='realstart',
                                    object_ref=assoc)

            else:
                self.make_relation(field_name,
                                   positions,
                                   org_data,
                                   assoc)

    def make_emplacement(self,
                         humane_id,
                         org_data,
                         organization):

        positions = {
            'Location': {
                'value': 'unit:location',
                'confidence': 'unit:location:confidence',
                'source': 'unit:location:source',
            }
        }

        relation_positions = {
            'StartDate': {
                'value': Emplacement.get_spreadsheet_field_name('startdate'),
                'day': Emplacement.get_spreadsheet_field_name('startdate') + '_day',
                'month': Emplacement.get_spreadsheet_field_name('startdate') + '_month',
                'year': Emplacement.get_spreadsheet_field_name('startdate') + '_year',
                'confidence': Emplacement.get_spreadsheet_confidence_field_name('startdate'),
                'source': Emplacement.get_spreadsheet_source_field_name('startdate'),
            },
            'RealStart': {
                'value': Emplacement.get_spreadsheet_field_name('realstart'),
                'confidence': Emplacement.get_spreadsheet_confidence_field_name('startdate'),
                'source': None
            },
            'EndDate': {
                'value': Emplacement.get_spreadsheet_field_name('enddate'),
                'day': Emplacement.get_spreadsheet_field_name('enddate') + '_day',
                'month': Emplacement.get_spreadsheet_field_name('enddate') + '_month',
                'year': Emplacement.get_spreadsheet_field_name('enddate') + '_year',
                'confidence': Emplacement.get_spreadsheet_confidence_field_name('enddate'),
                'source': Emplacement.get_spreadsheet_source_field_name('enddate'),
            },
            'OpenEnded': {
                'value': Emplacement.get_spreadsheet_field_name('open_ended'),
                'confidence': Emplacement.get_spreadsheet_confidence_field_name('enddate'),
                'source': None
            }
        }

        try:
            site = Location.objects.from_humane_id(humane_id)

        except Location.DoesNotExist:
            self.log_error('Location "{0}" for Site for {1} does not exist'.format(humane_id, organization.name))
            return None

        confidence = self.get_confidence(org_data[positions['Location']['confidence']])
        sources = self.get_sources(org_data[positions['Location']['source']])

        if sources and confidence:

            emp_data = {
                'Emplacement_EmplacementOrganization': {
                    'value': organization,
                    'confidence': confidence,
                    'sources': sources.copy()
                },
                'Emplacement_EmplacementSite': {
                    'value': site,
                    'confidence': confidence,
                    'sources': sources.copy()
                }
            }

            try:
                emplacement = Emplacement.objects.get(emplacementorganization__value=organization,
                                                      emplacementsite__value=site)
            except Emplacement.DoesNotExist:
                emplacement = Emplacement.create(emp_data)

            for field_name, positions in relation_positions.items():

                if field_name == 'StartDate':
                    self.make_relation(field_name,
                                       positions,
                                       org_data,
                                       emplacement,
                                       date=True)

                elif field_name == 'EndDate':
                    self.make_relation(field_name,
                                       positions,
                                       org_data,
                                       emplacement,
                                       date=True)

                elif field_name == 'RealStart':
                    self.make_real_date(data=org_data,
                                        position=positions['value'],
                                        model=EmplacementRealStart,
                                        attribute='realstart',
                                        object_ref=emplacement)

                else:
                    self.make_relation(field_name,
                                       positions,
                                       org_data,
                                       emplacement)

            return emplacement

        else:
            missing = []
            if not confidence:
                missing.append('confidence')
            if not sources:
                missing.append('sources')

            self.log_error('Emplacement for org {0} did not have {1}'.format(organization.name.get_value().value,
                                                                             ', '.join(missing)))
            return None

    def make_real_date(self, *, data, position, model, attribute, object_ref):
        '''
        Record a value from the sheet (`data`) corresponding to a real start/end
        date for a particular model instance.
        Params:
            - `data`: the sheet in question
            - `position`: index from which to retrieve the value
            - `model`: the model to create (e.g. OrganizationRealStart)
            - `attribute`: attribute of the model in question (e.g. 'realstart')
            - `object_ref`: the object instance that this date is tied to
        '''
        # We have to convert the 'Y'/'N' in the RealStart/End field to bool
        try:
            real_date = data[position]
        except IndexError:
            real_date = None

        if not real_date:
            return None

        if real_date == 'Y':
            real_date = True
        elif real_date == 'N':
            real_date = False
        else:
            real_date = None

        instance, created = model.objects.get_or_create(value=real_date,
                                                        object_ref=object_ref)

        if created:

            with reversion.create_revision():
                reversion.set_user(self.user)

        instance.save()

    def create_sources(self, source_sheet):

        self.current_sheet = 'sources'

        for idx, source_data in enumerate(source_sheet['values']):
            access_point_uuid = source_data['source:access_point_id:admin'].strip()
            try:
                AccessPoint.objects.get(uuid=access_point_uuid)
            except ValidationError:
                self.log_error(
                    'Invalid source UUID: "{}"'.format(access_point_uuid),
                    sheet='sources',
                    current_row=idx + 2  # Handle 0-index and header row
                )
            except AccessPoint.DoesNotExist:
                source_info = {
                    'title': source_data[Source.get_spreadsheet_field_name('title')],
                    'type': source_data[Source.get_spreadsheet_field_name('type')],
                    'author': source_data[Source.get_spreadsheet_field_name('author')],
                    'publication': source_data[Source.get_spreadsheet_field_name('publication')],
                    'publication_country': source_data[Source.get_spreadsheet_field_name('publication_country')],
                    'source_url': source_data[Source.get_spreadsheet_field_name('source_url')],
                    'user': self.user
                }
                # Figure out if created/uploaded/published dates are timestamps
                for prefix in ('published', 'created', 'uploaded'):
                    date_val = source_data[Source.get_spreadsheet_field_name('{}_date'.format(prefix))]
                    try:
                        # Try to parse the value as a timestamp (remove timezone
                        # marker for Pyton <3.7)
                        parsed_date = datetime.strptime(date_val.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        # Value is a date, or empty
                        parsed_date = self.parse_date(date_val)
                        source_info['{}_date'.format(prefix)] = parsed_date
                    else:
                        source_info['{}_timestamp'.format(prefix)] = parsed_date

                new_source, created = Source.objects.get_or_create(**source_info)

                AccessPoint.objects.create(
                    uuid=access_point_uuid,
                    type=source_data[AccessPoint.get_spreadsheet_field_name('type')],
                    trigger=source_data[AccessPoint.get_spreadsheet_field_name('trigger')],
                    accessed_on=self.parse_date(source_data[AccessPoint.get_spreadsheet_field_name('accessed_on')]),
                    archive_url=source_data[AccessPoint.get_spreadsheet_field_name('archive_url')],
                    source=new_source,
                    user=self.user
                )
            except ValueError:
                self.log_error("Invalid access point at: " + access_point_uuid)

    def get_sources(self, source_id_string):

        sources = []
        source_ids = [s.strip() for s in source_id_string.split(';') if s]

        for source_id in source_ids:
            try:
                source = AccessPoint.objects.get(uuid=source_id)
            except (ValueError, ValidationError):
                self.log_error("Invalid source: " + source_id)
            except AccessPoint.DoesNotExist:
                self.log_error("Missing source: " + source_id)
            else:
                sources.append(source)

        return sources

    def create_person(self, person_data):
        person = None

        person_positions = {
            'Name': {
                'value': Person.get_spreadsheet_field_name('name'),
                'confidence': Person.get_spreadsheet_confidence_field_name('name'),
                'source': Person.get_spreadsheet_source_field_name('name'),
            },
            'Alias': {
                'value': Person.get_spreadsheet_field_name('aliases'),
                'confidence': Person.get_spreadsheet_confidence_field_name('aliases'),
                'source': Person.get_spreadsheet_source_field_name('aliases'),
            },
            'DivisionId': {
                'value': Person.get_spreadsheet_field_name('division_id'),
                'confidence': Person.get_spreadsheet_confidence_field_name('division_id'),
                'source': Person.get_spreadsheet_source_field_name('division_id'),
            },
        }
        membership_positions = {
            'Organization': {
                'value': MembershipPerson.get_spreadsheet_field_name('organization'),
                # Confidence and source fields don't follow consistent naming convention
                'confidence': 'person:posting_unit:confidence',
                'source': 'person:posting_unit:source',
            },
            'Role': {
                'value': MembershipPerson.get_spreadsheet_field_name('role'),
                'confidence': MembershipPerson.get_spreadsheet_confidence_field_name('role'),
                'source': MembershipPerson.get_spreadsheet_source_field_name('role'),
            },
            'Title': {
                'value': MembershipPerson.get_spreadsheet_field_name('title'),
                'confidence': MembershipPerson.get_spreadsheet_confidence_field_name('title'),
                'source': MembershipPerson.get_spreadsheet_source_field_name('title'),
            },
            'Rank': {
                'value': MembershipPerson.get_spreadsheet_field_name('rank'),
                'confidence': MembershipPerson.get_spreadsheet_confidence_field_name('rank'),
                'source': MembershipPerson.get_spreadsheet_source_field_name('rank'),
            },
            'FirstCitedDate': {
                'value': MembershipPerson.get_spreadsheet_field_name('firstciteddate'),
                'day': MembershipPerson.get_spreadsheet_field_name('firstciteddate') + '_day',
                'month': MembershipPerson.get_spreadsheet_field_name('firstciteddate') + '_month',
                'year': MembershipPerson.get_spreadsheet_field_name('firstciteddate') + '_year',
                'confidence': MembershipPerson.get_spreadsheet_confidence_field_name('firstciteddate'),
                'source': MembershipPerson.get_spreadsheet_source_field_name('firstciteddate'),
            },
            'RealStart': {
                'value': MembershipPerson.get_spreadsheet_field_name('realstart'),
                'confidence': MembershipPerson.get_spreadsheet_confidence_field_name('firstciteddate'),
                'source': None,
            },
            'StartContext': {
                'value': MembershipPerson.get_spreadsheet_field_name('startcontext'),
                'confidence': MembershipPerson.get_spreadsheet_confidence_field_name('startcontext'),
                'source': MembershipPerson.get_spreadsheet_source_field_name('startcontext'),
            },
            'LastCitedDate': {
                'value': MembershipPerson.get_spreadsheet_field_name('lastciteddate'),
                'day': MembershipPerson.get_spreadsheet_field_name('lastciteddate') + '_day',
                'month': MembershipPerson.get_spreadsheet_field_name('lastciteddate') + '_month',
                'year': MembershipPerson.get_spreadsheet_field_name('lastciteddate') + '_year',
                'confidence': MembershipPerson.get_spreadsheet_confidence_field_name('lastciteddate'),
                'source': MembershipPerson.get_spreadsheet_source_field_name('lastciteddate'),
            },
            'RealEnd': {
                'value': MembershipPerson.get_spreadsheet_field_name('realend'),
                'confidence': MembershipPerson.get_spreadsheet_confidence_field_name('lastciteddate'),
                'source': None,
            },
            'EndContext': {
                'value': MembershipPerson.get_spreadsheet_field_name('endcontext'),
                'confidence': MembershipPerson.get_spreadsheet_confidence_field_name('endcontext'),
                'source': MembershipPerson.get_spreadsheet_source_field_name('endcontext'),
            },
        }

        try:
            name_value = person_data[person_positions['Name']['value']]
            confidence = person_data[person_positions['Name']['confidence']]
            source = person_data[person_positions['Name']['source']]
        except IndexError:
            self.log_error('Row seems to be empty')
            return None

        # Skip this row if it's not ready for import
        admin_status = person_data['person:status:admin']
        if admin_status != '3':
            self.stdout.write('Skipping person "{}" because its status is {}'.format(
                name_value,
                admin_status
            ))
            return None

        try:
            country_code = person_data[person_positions['DivisionId']['value']]
        except IndexError:
            self.log_error('Country code missing')
            return None

        if confidence and source:

            try:
                confidence = self.get_confidence(confidence)
            except KeyError:
                confidence = None

            sources = self.get_sources(source)
            self.stdout.write(self.style.SUCCESS('Working on {}'.format(name_value)))

            if confidence and sources:

                division_id = 'ocd-division/country:{}'.format(country_code)
                division_confidence = self.get_confidence(
                    person_data[person_positions['DivisionId']['confidence']]
                )
                division_sources = self.get_sources(
                    person_data[person_positions['DivisionId']['source']]
                )

                person_info = {
                    'Person_PersonName': {
                        'value': name_value,
                        'confidence': confidence,
                        'sources': sources.copy()
                    },
                    'Person_PersonDivisionId': {
                        'value': division_id,
                        'confidence': division_confidence,
                        'sources': division_sources,
                    }
                }

                try:
                    uuid = self.person_entity_map[name_value]
                except KeyError:
                    self.log_error('Could not find "{}" in list of person names'.format(name_value))
                    return None

                try:
                    person = Person.objects.get(uuid=uuid)
                except Person.DoesNotExist:
                    person = Person.objects.create(uuid=uuid, published=True)
                except ValidationError:
                    self.log_error('Invalid person UUID: "{}"'.format(uuid))
                    return None
                else:
                    sources = self.sourcesList(person, 'name')
                    person_info["Person_PersonName"]['sources'] += sources

                person.update(person_info)

                self.make_relation('Alias',
                                   person_positions['Alias'],
                                   person_data,
                                   person)

                # Make membership objects
                try:
                    uuid = person_data[membership_positions['Organization']['value']]
                    organization_name = {
                        v: k for k, v in self.organization_entity_map.items()
                    }[uuid]
                except IndexError:
                    self.log_error('Row seems to be empty')
                    return None
                except KeyError:
                    self.log_error('Organization "{}" not in entity map'.format(uuid))
                    return None

                try:
                    confidence = self.get_confidence(person_data[membership_positions['Organization']['confidence']])
                except (KeyError, IndexError):
                    self.log_error('Person {0} as a member of {1} has no confidence'.format(name_value, organization_name))
                    return None

                try:
                    sources = self.get_sources(person_data[membership_positions['Organization']['source']])
                except (KeyError, IndexError):
                    self.log_error('Person {0} as a member of {1} has no sources'.format(name_value, organization_name))
                    return None

                org_info = {
                    'Organization_OrganizationName': {
                        'value': organization_name,
                        'confidence': confidence,
                        'sources': sources.copy(),
                    },
                    'Organization_OrganizationDivisionId': {
                        'value': division_id,
                        'confidence': division_confidence,
                        'sources': division_sources,
                    }
                }

                try:
                    organization = Organization.objects.get(uuid=uuid)

                except Organization.DoesNotExist:
                    organization = Organization.objects.create(uuid=uuid,
                                                               published=True)
                    organization.update(org_info)

                except ValidationError:
                    self.log_error('Invalid member unit UUID: "{}"'.format(uuid))
                    return None

                else:
                    name_sources = self.sourcesList(organization, 'name')
                    div_sources = self.sourcesList(organization, 'division_id')

                    org_info["Organization_OrganizationName"]['sources'] += name_sources
                    org_info["Organization_OrganizationDivisionId"]['sources'] += div_sources

                    if organization.name.get_value():
                        name_confidence = organization.name.get_value().confidence

                        if name_confidence:
                            name_confidence = int(name_confidence)
                            org_info["Organization_OrganizationName"]['confidence'] = name_confidence

                    if organization.division_id.get_value():
                        div_confidence = organization.division_id.get_value().confidence

                        if div_confidence:
                            div_confidence = int(div_confidence)
                            org_info["Organization_OrganizationDivisionId"]['confidence'] = div_confidence

                    organization.update(org_info)

                membership_data = {
                    'MembershipPerson_MembershipPersonMember': {
                        'value': person,
                        'confidence': confidence,
                        'sources': sources.copy(),
                    },
                    'MembershipPerson_MembershipPersonOrganization': {
                        'value': organization,
                        'confidence': confidence,
                        'sources': sources.copy(),
                    },
                }

                try:
                    date_parts = [
                        person_data[membership_positions['FirstCitedDate']['year']],
                        person_data[membership_positions['FirstCitedDate']['month']],
                        person_data[membership_positions['FirstCitedDate']['day']]
                    ]
                    fcd = self.parse_date('-'.join(filter(None, date_parts)))
                except IndexError:
                    fcd = None

                try:
                    date_parts = [
                        person_data[membership_positions['LastCitedDate']['year']],
                        person_data[membership_positions['LastCitedDate']['month']],
                        person_data[membership_positions['LastCitedDate']['day']]
                    ]
                    lcd = self.parse_date('-'.join(filter(None, date_parts)))
                except IndexError:
                    lcd = None

                try:
                    role_name = person_data[membership_positions['Role']['value']]
                except IndexError:
                    role = None
                else:
                    if role_name:
                        role, _ = Role.objects.get_or_create(value=role_name)
                        role = role.id
                    else:
                        role = None

                try:
                    rank_name = person_data[membership_positions['Rank']['value']]
                except IndexError:
                    rank = None
                else:
                    if rank_name:
                        rank, _ = Rank.objects.get_or_create(value=rank_name)
                        rank = rank.id
                    else:
                        rank = None

                try:
                    title = person_data[membership_positions['Title']['value']] or None
                except IndexError:
                    title = None

                try:
                    membership = MembershipPerson.objects.get(membershippersonmember__value=person,
                                                              membershippersonorganization__value=organization,
                                                              membershippersonfirstciteddate__value=fcd,
                                                              membershippersonlastciteddate__value=lcd,
                                                              membershippersonrole__value=role,
                                                              membershippersonrank__value=rank,
                                                              membershippersontitle__value=title)
                    sources = set(self.sourcesList(membership, 'member') + self.sourcesList(membership, 'organization'))
                    membership_data['MembershipPerson_MembershipPersonMember']['sources'] += sources
                    membership.update(membership_data)

                except MembershipPerson.DoesNotExist:
                    membership = MembershipPerson.create(membership_data)

                self.make_relation('Role',
                                   membership_positions['Role'],
                                   person_data,
                                   membership)

                self.make_relation('Title',
                                   membership_positions['Title'],
                                   person_data,
                                   membership)

                self.make_relation('Rank',
                                   membership_positions['Rank'],
                                   person_data,
                                   membership)

                self.make_relation('FirstCitedDate',
                                   membership_positions['FirstCitedDate'],
                                   person_data,
                                   membership,
                                   date=True)

                self.make_real_date(data=person_data,
                                    position=membership_positions['RealStart']['value'],
                                    model=MembershipPersonRealStart,
                                    attribute='realstart',
                                    object_ref=membership)

                self.make_relation('StartContext',
                                   membership_positions['StartContext'],
                                   person_data,
                                   membership)

                self.make_relation('LastCitedDate',
                                   membership_positions['LastCitedDate'],
                                   person_data,
                                   membership,
                                   date=True)

                self.make_real_date(data=person_data,
                                    position=membership_positions['RealEnd']['value'],
                                    model=MembershipPersonRealEnd,
                                    attribute='realstart',
                                    object_ref=membership)

                self.make_relation('EndContext',
                                   membership_positions['EndContext'],
                                   person_data,
                                   membership)

                self.stdout.write(self.style.SUCCESS('Created {}'.format(person.get_value())))

            else:
                self.log_error('{} did not have a confidence or source'.format(name_value))

    def create_person_extra(self, data):
        """
        Create a PersonExtra objects from a row in the persons_extra sheet.
        """
        person_positions = {
            'Name': {
                'value': PersonExtra.get_spreadsheet_field_name('person'),
            },
            'Id': {
                'value': 'person_extra:id:admin',
            },
        }

        biography_positions = {
            'Gender': {
                'key': 'Person_PersonBiographyGender',
                'value': PersonBiography.get_spreadsheet_field_name('gender'),
                'confidence': PersonBiography.get_spreadsheet_confidence_field_name('gender'),
                'source': PersonBiography.get_spreadsheet_source_field_name('gender'),
            },
            'DateOfBirth': {
                'key': 'Person_PersonBiographyDateOfBirth',
                'value': PersonBiography.get_spreadsheet_field_name('date_of_birth'),
                'confidence': PersonBiography.get_spreadsheet_confidence_field_name('date_of_birth'),
                'source': PersonBiography.get_spreadsheet_source_field_name('date_of_birth'),
            },
            'Deceased': {
                'key': 'Person_PersonBiographyDeceased',
                'value': PersonBiography.get_spreadsheet_field_name('deceased'),
                'confidence': PersonBiography.get_spreadsheet_confidence_field_name('deceased'),
                'source': PersonBiography.get_spreadsheet_source_field_name('deceased'),
            },
            'DateOfDeath': {
                'key': 'Person_PersonBiographyDateOfDeath',
                'value': PersonBiography.get_spreadsheet_field_name('date_of_death'),
                'confidence': PersonBiography.get_spreadsheet_confidence_field_name('date_of_death'),
                'source': PersonBiography.get_spreadsheet_source_field_name('date_of_death'),
            },
        }

        extra_positions = {
            'AccountType': {
                'key': 'Person_PersonExtraAccountType',
                'value': PersonExtra.get_spreadsheet_field_name('account_type'),
                'confidence': PersonExtra.get_spreadsheet_confidence_field_name('account_type'),
                'source': PersonExtra.get_spreadsheet_source_field_name('account_type'),
            },
            'AccountId': {
                'key': 'Person_PersonExtraAccount',
                'value': PersonExtra.get_spreadsheet_field_name('account'),
                'confidence': PersonExtra.get_spreadsheet_confidence_field_name('account'),
                'source': PersonExtra.get_spreadsheet_source_field_name('account'),
            },
            'ExternalLinkDescription': {
                'key': 'Person_PersonExtraExternalLinkDescription',
                'value': PersonExtra.get_spreadsheet_field_name('external_link_description'),
                'confidence': PersonExtra.get_spreadsheet_confidence_field_name('external_link_description'),
                'source': PersonExtra.get_spreadsheet_source_field_name('external_link_description'),
            },
            'MediaDescription': {
                'key': 'Person_PersonExtraMediaDescription',
                'value': PersonExtra.get_spreadsheet_field_name('media_description'),
                'confidence': PersonExtra.get_spreadsheet_confidence_field_name('media_description'),
                'source': PersonExtra.get_spreadsheet_source_field_name('media_description'),
            },
            'Notes': {
                'key': 'Person_PersonExtraNotes',
                'value': PersonExtra.get_spreadsheet_field_name('notes'),
            },
        }

        try:
            person_name_value = data[person_positions['Name']['value']]
        except KeyError:
            self.log_error('Row appears to be missing a Person name')
            return None

        try:
            person_id_value = data[person_positions['Id']['value']]
        except KeyError:
            self.log_error('Row appears to be missing a Person ID')
            return None

        try:
            person = Person.objects.get(uuid=person_id_value)
        except Person.DoesNotExist:
            self.log_error('No person with the ID {} was found'.format(person_id_value))
            return None
        except ValidationError:
            self.log_error('Invalid person ID: "{}"'.format(person_id_value))
            return None

        try:
            assert person.name.get_value().value == person_name_value
        except AssertionError:
            self.log_error(
                'Stored person name "{}" does not match spreadsheet value "{}"'.format(
                    person.name.get_value(), person_name_value
                ))
            return None

        self.stdout.write(
            self.style.SUCCESS(
                'Working on {}'.format(person_name_value)
            )
        )

        # Check if the row corresponds to a PersonBiography or PersonExtra
        # object instance
        is_biography = False
        for bio_field in biography_positions.values():
            if data[bio_field['value']]:
                is_biography = True
                break

        is_extra = False
        for extra_field in extra_positions.values():
            if data[extra_field['value']]:
                is_extra = True
                break

        if (is_biography and not is_extra) or (not is_biography and is_extra):
            # Define a convenience function for parsing info from positions
            def get_info_from_positions(positions):
                info = {}
                for positions in positions.values():
                    if positions.get('key'):
                        info[positions['key']] = {
                            'value': data[positions['value']]
                        }
                        if positions.get('confidence'):
                            info[positions['key']]['confidence'] = self.get_confidence(
                                data[positions['confidence']]
                            )
                        if positions.get('sources'):
                            info[positions['key']]['sources'] = self.get_sources(
                                data[positions['sources']]
                            )
                return info

            if is_biography:
                # This is a PersonBiography instance
                person_bio_info = get_info_from_positions(biography_positions)
                # PersonBiographies should have a 1:1 relationship with Persons
                person_bio = PersonBiography.create({
                    'PersonBiography_PersonBiographyPerson': {'value': person}
                })
                person_bio.update(person_bio_info)
            else:
                # This is a PersonExtra instance
                person_extra_info = get_info_from_positions(extra_positions)
                # A Person can have many PersonExtras, so we can just create
                # a new one here.
                person_extra = PersonExtra.create({
                    'PersonExtra_PersonExtraPerson': {'value': person}
                })
                person_extra.update(person_extra_info)

        elif not is_biography and not is_extra:
            self.log_error('Row appears to have no data')
            return None

        else:
            self.log_error((
                'Row has both biographical and extra data in it. Since '
                'biographical data requires a 1:1 relationship with a Person, '
                'but extra data can have a many-to-one relationship, this '
                'row is invalid.'
            ))
            return None

        self.stdout.write(
            self.style.SUCCESS(
                'Created extra information for {}'.format(person_name_value)
            )
        )

    def create_event(self, event_data):

        positions = {
            'StartDate': {
                'value': Violation.get_spreadsheet_field_name('startdate'),
                'source': 'incident:all:source',
                'model_field': 'violationstartdate',
            },
            'EndDate': {
                'value': Violation.get_spreadsheet_field_name('enddate'),
                'source': 'incident:all:source',
                'model_field': 'violationenddate',
            },
            # AKA "date of publication"
            'FirstAllegation': {
                'value': Violation.get_spreadsheet_field_name('first_allegation'),
                'source': 'incident:all:source',
                'model_field': 'violationfirstallegation',
            },
            'LastUpdate': {
                'value': Violation.get_spreadsheet_field_name('last_update'),
                'source': 'incident:all:source',
                'model_field': 'violationlastupdate',
            },
            'Status': {
                'value': Violation.get_spreadsheet_field_name('status'),
                'source': 'incident:all:source',
                'model_field': 'violationstatus',
            },
            'LocationDescription': {
                'value': Violation.get_spreadsheet_field_name('locationdescription'),
                'source': 'incident:all:source',
                'model_field': 'violationlocationdescription',
            },
            'Location': {
                'value': Violation.get_spreadsheet_field_name('location_id'),
                'source': 'incident:all:source',
                'model_field': 'violationexactlocation',
            },
            'Type': {
                'value': Violation.get_spreadsheet_field_name('types'),
                'source': 'incident:all:source',
                'model_field': 'violationtype',
            },
            'Description': {
                'value': Violation.get_spreadsheet_field_name('description'),
                'source': 'incident:all:source',
                'model_field': 'violationdescription',
            },
            'Perpetrator': {
                'value': Violation.get_spreadsheet_field_name('perpetrator'),
                'source': 'incident:all:source'
            },
            'PerpetratorOrganization': {
                'value': Violation.get_spreadsheet_field_name('perpetratororganization'),
                'source': 'incident:all:source'
            },
            'PerpetratorClassification': {
                'value': Violation.get_spreadsheet_field_name('perpetratorclassification'),
                'source': 'incident:all:source'
            }
        }

        uuid = event_data['incident:id:admin']

        # Skip this row if it's not ready for import
        admin_status = event_data['incident:status:admin']
        if admin_status != '3':
            self.stdout.write('Skipping event "{}" because its status is {}'.format(
                uuid,
                admin_status
            ))
            return None

        with reversion.create_revision():
            try:
                violation, created = Violation.objects.get_or_create(
                    uuid=uuid,
                    published=True
                )
            except ValidationError:
                self.log_error('Invalid Incident UUID: "{}"'.format(uuid))
                return None

            reversion.set_user(self.user)

        # Simple attributes that support multiple values
        simple_multi_attrs = ('LocationDescription', 'Type', 'Status')

        for attr in simple_multi_attrs:
            self.make_relation(attr,
                               positions[attr],
                               event_data,
                               violation,
                               require_confidence=False)

        # Simple attributes that only support single values
        simple_single_attrs = ('Description',)

        for attr in simple_single_attrs:
            self.make_relation(attr,
                               positions[attr],
                               event_data,
                               violation,
                               require_confidence=False,
                               multiple=False)

        date_attrs = ('StartDate', 'EndDate', 'FirstAllegation', 'LastUpdate')

        for attr in date_attrs:

            self.make_relation(attr,
                               positions[attr],
                               event_data,
                               violation,
                               require_confidence=False,
                               date=True)

        try:
            # All data in this sheet use the same source
            sources = self.get_sources(event_data[positions['Type']['source']])
        except IndexError:
            self.log_error('Row does not have required source column')
            return None

        event_info = {}

        humane_id = event_data[positions['Location']['value']]

        try:
            exact_location = Location.objects.from_humane_id(humane_id)
        except Location.DoesNotExist:
            self.log_error('Location {} for ViolationLocation does not exist'.format(humane_id))
            self.log_error('Country code missing')
            return None

        else:
            if exact_location.name and exact_location.id:
                event_info.update({
                    'Violation_ViolationLocationName': {
                        'value': exact_location.name,
                        'sources': sources.copy(),
                        'confidence': 1
                    },
                    'Violation_ViolationLocationId': {
                        'value': exact_location.id,
                        'sources': sources.copy(),
                        'confidence': 1
                    },
                })

            geo, admin1, admin2 = exact_location, exact_location.adminlevel1, exact_location.adminlevel2

            event_info.update({
                'Violation_ViolationOSMName': {
                    'value': geo.name,
                    'sources': sources.copy(),
                    'confidence': 1
                },
                'Violation_ViolationOSMId': {
                    'value': geo.id,
                    'sources': sources.copy(),
                    'confidence': 1
                },
            })

            if admin1:
                event_info.update({
                    'Violation_ViolationAdminLevel1': {
                        'value': admin1,
                        'sources': sources.copy(),
                        'confidence': 1
                    },
                })
            if admin2:
                event_info.update({
                    'Violation_ViolationAdminLevel2': {
                        'value': admin2,
                        'sources': sources.copy(),
                        'confidence': 1
                    },
                })

            event_info.update({
                'Violation_ViolationLocation': {
                    'value': geo,
                    'sources': sources.copy(),
                    'confidence': 1
                },
            })

            event_info.update({
                'Violation_ViolationDivisionId': {
                    'value': geo.division_id,
                    'sources': sources.copy(),
                    'confidence': 1,
                }
            })

            violation.update(event_info)

        # Record perpetrators

        try:
            perpetrator = event_data[positions['Perpetrator']['value']]
        except IndexError:
            perpetrator = None

        if perpetrator:

            perps = [perp.strip() for perp in perpetrator.split(';') if perp.strip()]

            for perp in perps:

                try:
                    uuid = self.person_entity_map[perp]
                except KeyError:
                    self.log_error('Could not find "{}" in list of person names'.format(perp))
                    continue

                try:
                    person = Person.objects.get(uuid=uuid)
                except ValidationError:
                    self.log_error('Invalid perpetrator UUID: "{}"'.format(uuid))
                    continue
                except Person.DoesNotExist:
                    person_info = {
                        'Person_PersonName': {
                            'value': perp,
                            'confidence': 1,
                            'sources': sources.copy(),
                        },
                        'Person_PersonDivisionId': {
                            'value': geo.division_id,
                            'confidence': 1,
                            'sources': sources.copy()
                        }
                    }
                    person = Person.objects.create(uuid=uuid, published=True)
                    person.update(person_info)

                vp, created = ViolationPerpetrator.objects.get_or_create(value=person,
                                                                         object_ref=violation)
                if created:

                    with reversion.create_revision():
                        for source in sources:
                            vp.accesspoints.add(source)
                            vp.sources.add(source.source)
                        vp.save()
                        reversion.set_user(self.user)

        try:
            perp_org = event_data[positions['PerpetratorOrganization']['value']]
        except IndexError:
            perp_org = None

        if perp_org:

            orgs = [perp.strip() for perp in perp_org.split(';') if perp.strip()]

            for org in orgs:

                try:
                    uuid = self.organization_entity_map[org]
                except KeyError:
                    self.log_error('Could not find "{}" in list of organization names'.format(org))
                    continue

                try:
                    organization = Organization.objects.get(uuid=uuid)
                except ValidationError:
                    self.log_error('Invalid perpetrator unit UUID: "{}"'.format(uuid))
                    continue
                except (Organization.DoesNotExist, ValueError):

                    info = {
                        'Organization_OrganizationName': {
                            'value': org,
                            'confidence': 1,
                            'sources': sources.copy(),
                        },
                        'Organization_OrganizationDivisionId': {
                            'value': geo.division_id,
                            'confidence': 1,
                            'sources': sources.copy(),
                        }
                    }
                    organization = Organization.objects.create(uuid=uuid,
                                                               published=True)
                    organization.update(info)

                vpo_obj, created = ViolationPerpetratorOrganization.objects.get_or_create(value=organization,
                                                                                          object_ref=violation)

                if created:

                    with reversion.create_revision():
                        for source in sources:
                            vpo_obj.accesspoints.add(source)
                            vpo_obj.sources.add(source.source)
                        vpo_obj.save()
                        reversion.set_user(self.user)

        self.make_relation('PerpetratorClassification',
                           positions['PerpetratorClassification'],
                           event_data,
                           violation,
                           require_confidence=False)
