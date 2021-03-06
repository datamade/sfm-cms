# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-09-07 16:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geosite', '0011_auto_20170907_1558'),
    ]

    operations = [
        migrations.AlterField(
            model_name='geositeadminid',
            name='sources',
            field=models.ManyToManyField(related_name='geosite_geositeadminid_related', to='source.Source'),
        ),
        migrations.AlterField(
            model_name='geositeadminname',
            name='sources',
            field=models.ManyToManyField(related_name='geosite_geositeadminname_related', to='source.Source'),
        ),
    ]
