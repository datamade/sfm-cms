# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-08-24 18:45
from __future__ import unicode_literals

import os

from django.db import migrations, connection
from django.conf import settings


def remake_view(apps, schema_editor):
    sql_folder_path = os.path.join(settings.BASE_DIR, 'sfm_pc/management/commands/sql')

    with open(os.path.join(sql_folder_path, 'composition_view.sql')) as f:
        with connection.cursor() as curs:
            curs.execute(f.read())

class Migration(migrations.Migration):

    dependencies = [
        ('composition', '0011_auto_20180824_1843'),
    ]

    operations = [
        migrations.RunSQL('''
            UPDATE composition_compositionclassification SET
              value=s.value
            FROM (
              SELECT id, value FROM composition_classification
            ) AS s
            WHERE composition_compositionclassification.value_id = s.id
        '''),
        migrations.RunPython(remake_view),
    ]
