import json
import pprint

from django.conf import settings
from django.core.management.base import BaseCommand

import pysolr


class WWICSolrCoreAdmin(pysolr.SolrCoreAdmin):

    def create(
        self, name, config_set=None, instance_dir=None, config="solrconfig.xml", schema="schema.xml"
    ):
        '''
        Extend pysolr to allow a config set to be specified.
        '''
        if not config_set:
            return super().create(name, instance_dir, config, schema)

        else:
            params = {"action": "CREATE", "name": name, "configSet": config_set}
            return self._get_url(self.url, params=params)


class Command(BaseCommand):

    help = 'Create a Solr core for each configured language.'

    ERRORS = {
        'already_exists': 'Core with name \'{}\' already exists.',
        'invalid_configset': 'Could not load configuration from directory',
    }

    def add_arguments(self, parser):
        '''
        Solr configsets are directories containing configs that can be reused
        across cores. This command assumes you've created a directory containing
        the necessary configs at the configSetBaseDir, usually
        /opt/solr/server/solr/configsets/.
        '''
        parser.add_argument(
            '--config_set',
            default='sfm_configs',
            help="Name of configset to use"
        )

    def handle(self, *args, **options):
        BASE_SOLR_URL = '/'.join(settings.SOLR_URL.split('/')[:-1])

        solr_admin = WWICSolrCoreAdmin('{}/admin/cores'.format(BASE_SOLR_URL))

        for conn in settings.HAYSTACK_CONNECTIONS.values():
            core_name = conn['URL'].split('/')[-1]

            self.stdout.write('Creating {}...'.format(core_name))

            response = json.loads(
                solr_admin.create(core_name, config_set=options['config_set'])
            )

            if response.get('error'):
                error_message = response['error']['msg']
                if error_message == self.ERRORS['already_exists'].format(core_name):
                    self.stdout.write(self.style.WARNING('{} already exists!'.format(core_name)))
                    continue
                elif self.ERRORS['invalid_configset'] in error_message:
                    self.stdout.write(self.style.ERROR(
                        'Specified config set "{}" does not exist. Did you move '
                        'your config directory to configSetBaseDir, usually '
                        '/opt/solr/server/solr/configsets/?'.format(options['config_set'])
                    ))
                    break
                else:
                    raise Exception(response)

            self.stdout.write(self.style.SUCCESS('Created {}!').format(core_name))
