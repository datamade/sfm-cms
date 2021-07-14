import pprint

from django.conf import settings
from django.core.management.base import BaseCommand

import pysolr


class Command(BaseCommand):
    """
    A simple management command which clears the site-wide cache.

    Code adapted from Randall Degges:
    https://github.com/rdegges/django-clear-cache
    """

    help = 'Fully clear your site-wide cache.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config_dir',
            default='/app/solr_configs',
            help="Absolute path to directory containing Solr configs"
        )

    def handle(self, *args, **options):
        BASE_SOLR_URL = '/'.join(settings.SOLR_URL.split('/')[:-1])

        solr_admin = pysolr.SolrCoreAdmin('{}/admin/cores'.format(BASE_SOLR_URL))

        for conn in settings.HAYSTACK_CONNECTIONS.values():
            core_name = conn['URL'].split('/')[-1]
            print(core_name)
            response = solr_admin.create(core_name, instance_dir=options['config_dir'])
            pprint.pprint(response)
