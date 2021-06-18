# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-06-17 15:27
from __future__ import unicode_literals

from django.core.management import call_command
from django.db import migrations
import source.fields


def make_or_refresh_materialized_views(apps, schema_editor):
    call_command('make_materialized_views', views=['sources'])

class Migration(migrations.Migration):

    dependencies = [
        ('source', '0038_add_verbose_names'),
    ]

    operations = [
        migrations.RunSQL('''
            DROP MATERIALIZED VIEW IF EXISTS sfm_pc_sourcedownload
        ''', reverse_sql=migrations.RunSQL.noop),
        migrations.AlterField(
            model_name='accesspoint',
            name='archive_url',
            field=source.fields.URLField(max_length=2500, null=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='publication',
            field=source.fields.TextField(null=True, verbose_name='publisher'),
        ),
        migrations.AlterField(
            model_name='source',
            name='source_url',
            field=source.fields.URLField(blank=True, max_length=2500, null=True),
        ),
        migrations.RunPython(
            make_or_refresh_materialized_views,
            reverse_code=migrations.RunPython.noop
        ),
    ]
