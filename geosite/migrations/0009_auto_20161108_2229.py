# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2016-11-08 22:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geosite', '0008_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='geositeosmid',
            name='value',
            field=models.BigIntegerField(blank=True, default=None, null=True),
        ),
    ]
