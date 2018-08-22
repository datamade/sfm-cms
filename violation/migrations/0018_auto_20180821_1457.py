# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-08-21 14:57
from __future__ import unicode_literals

import os

from django.db import migrations, connection
from django.conf import settings


def remake_views(apps, schema_editor):
    sql_folder_path = os.path.join(settings.BASE_DIR, 'sfm_pc/management/commands/sql')
    view_paths = [
        os.path.join(sql_folder_path, 'violation_view.sql'),
        os.path.join(sql_folder_path, 'violation_sources_view.sql'),
        os.path.join(sql_folder_path, 'violation_all_export_view.sql'),
    ]
    for view_path in view_paths:
        with open(view_path) as sql:
            with connection.cursor() as curs:
                curs.execute(sql.read())



class Migration(migrations.Migration):

    dependencies = [
        ('violation', '0017_auto_20180821_1452'),
    ]

    operations = [
        migrations.RunSQL('''
            UPDATE violation_violationperpetratorclassification SET
              value=s.value
            FROM (
              SELECT id, value FROM violation_perpetratorclassification
            ) AS s
            WHERE violation_violationperpetratorclassification.id = s.id
        '''),
        migrations.RunSQL('''
            UPDATE violation_violationtype SET
              value=s.value
            FROM (
              SELECT id, code AS value FROM violation_type
            ) AS s
            WHERE violation_violationtype.id = s.id
        '''),
        migrations.RunPython(remake_views),
        migrations.RunSQL(
            '''
            ALTER TABLE violation_violationperpetratorclassification DROP COLUMN value_id
            '''
        ),
        migrations.RunSQL(
            '''
            ALTER TABLE violation_violationtype DROP COLUMN value_id
            '''
        ),
    ]