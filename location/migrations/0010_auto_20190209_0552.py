# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-02-09 05:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0009_auto_20190131_2040'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='adminlevel',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
