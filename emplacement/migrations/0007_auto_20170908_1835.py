# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-09-08 18:35
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('emplacement', '0006_emplacementrealstart'),
    ]

    operations = [
        migrations.CreateModel(
            name='Alias',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField()),
            ],
        ),
        migrations.AlterField(
            model_name='emplacementalias',
            name='value',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='emplacement.Alias'),
        ),
    ]
