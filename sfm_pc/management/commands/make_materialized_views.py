from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.utils import ProgrammingError

from sfm_pc.models import BasicDownload


class Command(BaseCommand):
    help = 'Create materialized views for spreadsheet exports'
    views_to_models = {
        'basic': BasicDownload,
    }

    def add_arguments(self, parser):
        parser.add_argument(
            'views',
            nargs='*',
            default=list(self.views_to_models.keys()),
            help='The name of the views to create or update'
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        for view in kwargs['views']:
            try:
                Model = self.views_to_models[view]
            except KeyError:
                raise CommandError(
                    'View {} is not valid, should be one of: {}'.format(
                        view,
                        list(self.views_to_models.keys())
                    )
                )
            query, params = Model.get_materialized_view_sql_with_params()
            with connection.cursor() as cursor:
                try:
                    cursor.execute(query, params)
                except ProgrammingError as e:
                    if 'already exists' in str(e):
                        self.stdout.write(
                            'View for "{}" already exists -- skipping'.format(
                                view
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            'Created view for "{}"'.format(view)
                        )
                    )
