# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-07-06 18:37
from __future__ import unicode_literals

from django.db import migrations, connection


def insert_access_points(apps, schema_editor):
    cursor = connection.cursor()
    source_tables = '''
        SELECT relname
        FROM pg_catalog.pg_class
        WHERE relkind = 'r'
          AND relname LIKE '%_sources'
    '''

    cursor.execute(source_tables)

    source_tables = [r[0] for r in cursor]

    with connection.cursor() as curs:

        for source_table in source_tables:

            column_name = source_table.split('_')[1]
            ap_table = source_table.replace('_sources', '_accesspoints')

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

            if source_table == 'membershiporganization_membershiporganizationrealend_sources':
                ap_table = 'membershiporganization_membershiporganizationrealend_access5a60'

            if source_table == 'membershiporganization_membershiporganizationrealstart_sources':
                ap_table = 'membershiporganization_membershiporganizationrealstart_acceac5c'

            insert = '''
                INSERT INTO {0} (
                    accesspoint_id,
                    {1}_id
                )
                SELECT
                  ap.uuid AS accesspoint_id,
                  source.{1}_id
                FROM source_accesspoint AS ap
                JOIN {3} AS source
                  USING(source_id)
                ON CONFLICT DO NOTHING
            '''.format(ap_table,
                       column_name,
                       ap_table,
                       source_table)

            curs.execute(insert)


def remove_access_points(apps, schema_editor):
    cursor = connection.cursor()
    source_tables = '''
        SELECT relname
        FROM pg_catalog.pg_class
        WHERE relkind = 'r'
          AND relname LIKE '%_accesspoints'
    '''

    cursor.execute(source_tables)

    with connection.cursor() as curs:

        for row in cursor:
            source_table = row[0]
            curs.execute('TRUNCATE {} CASCADE'.format(source_table))


class Migration(migrations.Migration):

    dependencies = [
        ('source', '0031_auto_20180705_1536'),
        ('violation', '0014_auto_20180706_1825'),
        ('person', '0007_auto_20180706_1825'),
    ]

    operations = [
        migrations.RunPython(insert_access_points, reverse_code=remove_access_points)
    ]
