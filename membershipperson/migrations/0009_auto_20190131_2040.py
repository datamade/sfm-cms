# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-01-31 20:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membershipperson', '0008_auto_20180814_1449'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Context',
        ),
        migrations.RemoveField(
            model_name='membershippersonendcontext',
            name='value_id',
        ),
        migrations.RemoveField(
            model_name='membershippersonstartcontext',
            name='value_id',
        ),
        migrations.AlterField(
            model_name='membershippersonendcontext',
            name='value',
            field=models.TextField(default='foo'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='membershippersonstartcontext',
            name='value',
            field=models.TextField(default='foo'),
            preserve_default=False,
        ),
    ]
