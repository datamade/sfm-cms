# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-18 15:51
from __future__ import unicode_literals

import os

from django.db import migrations, models, connection
import django.db.models.deletion
from django.conf import settings


def remake_views(apps, schema_editor):
    sql_folder_path = os.path.join(settings.BASE_DIR, 'sfm_pc/management/commands/sql')

    association_view = os.path.join(sql_folder_path, 'association_view.sql')
    association_source_view = os.path.join(sql_folder_path, 'association_sources_view.sql')

    with open(association_view) as em, open(association_source_view) as es:
        with connection.cursor() as curs:
            curs.execute(em.read())
            curs.execute(es.read())


class Migration(migrations.Migration):

    dependencies = [
        ('association', '0006_auto_20180706_1825'),
        ('location', '0005_remove_location_admin_level'),
    ]

    state_operations = [
        migrations.AlterField(
            model_name='associationarea',
            name='value',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='location.Location'),
        ),
    ]

    database_operations = [
        migrations.RunSQL('DROP MATERIALIZED VIEW IF EXISTS association'),
        migrations.RunSQL('DROP MATERIALIZED VIEW IF EXISTS association_sources'),
        migrations.RunSQL('ALTER TABLE association_associationarea DROP CONSTRAINT association_associationarea_value_id_9ed99f44_fk_area_area_id'),
        migrations.RunSQL('''
            UPDATE association_associationarea SET
              value_id=s.value_id
            FROM (
              SELECT
                ass_area.id AS area_id,
                osm.value AS value_id
              FROM association_associationarea AS ass_area
              JOIN area_area AS area
                ON ass_area.value_id = area.id
              JOIN area_areaosmid AS osm
                ON area.id = osm.object_ref_id
            ) AS s
            WHERE association_associationarea.id = s.area_id
        '''),
        migrations.RunPython(remake_views),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=state_operations,
            database_operations=database_operations
        )
    ]
