# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2016-12-14 14:51
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('membershiporganization', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='membershiporganizationorganization',
            table='membershiporganization_moo',
        ),
    ]