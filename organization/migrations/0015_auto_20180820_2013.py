# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-08-20 20:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0014_auto_20180820_2011'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationalias',
            name='value',
            field=models.TextField(null=True)
        ),
        migrations.AddField(
            model_name='organizationclassification',
            name='value',
            field=models.TextField(null=True)
        )
    ]
