# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-07-08 19:20
from __future__ import unicode_literals

from django.db import migrations
import sfm_pc.fields


class Migration(migrations.Migration):

    dependencies = [
        ('membershipperson', '0009_auto_20190131_2040'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membershippersonfirstciteddate',
            name='value',
            field=sfm_pc.fields.I10nApproximateDateField(),
        ),
        migrations.AlterField(
            model_name='membershippersonlastciteddate',
            name='value',
            field=sfm_pc.fields.I10nApproximateDateField(),
        ),
    ]
