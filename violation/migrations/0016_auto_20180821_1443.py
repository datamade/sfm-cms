# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-08-21 14:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('violation', '0015_auto_20180821_1441'),
    ]

    database_operations = [
        migrations.AlterField(
            model_name='violationperpetratorclassification',
            name='value',
            field=models.ForeignKey('PerpetratorClassification', db_constraint=False, db_index=True)
        ),
        migrations.AlterField(
            model_name='violationtype',
            name='value',
            field=models.ForeignKey('Type', db_constraint=False, db_index=True)
        ),
    ]

    state_operations = [
        migrations.AlterField(
            model_name='violationperpetratorclassification',
            name='value',
            field=models.IntegerField(db_index=True, null=False)
        ),
        migrations.RenameField(
            model_name='violationperpetratorclassification',
            old_name='value',
            new_name='value_id'
        ),
        migrations.AlterField(
            model_name='violationtype',
            name='value',
            field=models.IntegerField(db_index=True, null=False)
        ),
        migrations.RenameField(
            model_name='violationtype',
            old_name='value',
            new_name='value_id'
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=database_operations,
            state_operations=state_operations
        )
    ]
