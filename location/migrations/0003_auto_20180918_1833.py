# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-09-18 18:33
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0002_location_geometry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='tags',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
    ]
