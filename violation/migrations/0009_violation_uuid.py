# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2016-10-27 19:40
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('violation', '0008_auto_20160812_1559'),
    ]

    operations = [
        migrations.AddField(
            model_name='violation',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
        ),
    ]
