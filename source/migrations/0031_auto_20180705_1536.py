# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-07-05 15:36
from __future__ import unicode_literals

import uuid

from django.db import migrations, models, connection

def update_source_tables(apps, schema_editor):

    cursor = connection.cursor()
    source_tables = '''
        SELECT relname
        FROM pg_catalog.pg_class
        WHERE relkind = 'r'
          AND relname LIKE '%_sources'
    '''

    cursor.execute(source_tables)

    with connection.cursor() as curs:

        for row in cursor:
            source_table = row[0]

            add_col = '''
                ALTER TABLE {}
                ADD COLUMN accesspoint_id uuid
            '''.format(source_table)

            column_name = source_table.split('_')[1]

            # There are some columns / tables which don't follow the standard
            # naming convention. Sort those out here:

            if column_name == 'fcd':
                column_name = 'membershiporganizationfirstciteddate'

            if column_name == 'lcd':
                column_name = 'membershiporganizationlastciteddate'

            if column_name == 'm':
                column_name = 'membershiporganizationmember'

            if column_name == 'moo':
                column_name = 'membershiporganizationorganization'

            insert  = '''
                INSERT INTO {0} (
                  source_id,
                  accesspoint_id,
                  {1}_id
                )
                  SELECT
                    source_table.source_id,
                    access_point.uuid AS accesspoint_id,
                    source_table.{1}_id
                  FROM {0} AS source_table
                  JOIN source_accesspoint AS access_point
                    USING(source_id)
            '''.format(source_table, column_name)

            curs.execute(add_col)
            curs.execute(insert)


def remove_access_point(apps, schema_editor):
    cursor = connection.cursor()
    source_tables = '''
        SELECT relname
        FROM pg_catalog.pg_class
        WHERE relkind = 'r'
          AND relname LIKE '%_sources'
    '''

    cursor.execute(source_tables)

    with connection.cursor() as curs:

        for row in cursor:
            source_table = row[0]

            drop_col = '''
                ALTER TABLE {}
                DROP COLUMN accesspoint_id
            '''.format(source_table)

            curs.execute(drop_col)


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('source', '0030_auto_20180705_1535'),
    ]

    operations = [
        migrations.RunPython(update_source_tables, reverse_code=remove_access_point),
        migrations.AlterField(
            model_name='accesspoint',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
        ),
    ]
