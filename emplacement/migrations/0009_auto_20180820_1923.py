# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-08-20 19:23
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('emplacement', '0008_auto_20180706_1825'),
    ]

    operations = [
        migrations.RunSQL('''
            DROP MATERIALIZED VIEW IF EXISTS emplacement
        ''')
    ]
