# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-08-20 18:29
from __future__ import unicode_literals

from django.db import migrations
import django_date_extensions.fields


class Migration(migrations.Migration):

    dependencies = [
        ('source', '0034_auto_20180711_2034'),
    ]

    operations = [
        migrations.AlterField(
            model_name='source',
            name='published_on',
            field=django_date_extensions.fields.ApproximateDateField(),
        ),
    ]