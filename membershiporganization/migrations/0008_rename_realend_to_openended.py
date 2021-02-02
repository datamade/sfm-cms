# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-02-02 19:54
from __future__ import unicode_literals

from django.db import migrations, models


def map_new_type(apps, schema_editor):

    MembershipOrganizationRealEnd = apps.get_model("membershiporganization", "MembershipOrganizationRealEnd")
    db_alias = schema_editor.connection.alias

    real_ends = MembershipOrganizationRealEnd.objects.using(db_alias).all()

    for end in real_ends:

        if end.value == True:

            end.new_value = 'Y'

        elif end.value == False:

            end.new_value = 'N'

        else:

            end.new_value = 'N'

        end.save()


class Migration(migrations.Migration):

    dependencies = [
        ('membershiporganization', '0007_auto_20180706_1825'),
    ]

    operations = [
        migrations.AddField(
            model_name='MembershipOrganizationRealEnd',
            name='new_value',
            field=models.CharField(choices=[('Y', 'Yes'), ('N', 'No'), ('E', 'Exact')], default='N', max_length=1),
        ),
        migrations.RunPython(map_new_type),
        migrations.RemoveField(
            model_name='MembershipOrganizationRealEnd',
            name='value',
        ),
        migrations.RenameField(
            model_name='MembershipOrganizationRealEnd',
            old_name='new_value',
            new_name='value'
        ),
        migrations.RenameModel('MembershipOrganizationRealEnd', 'MembershipOrganizationOpenEnded'),
        migrations.AlterModelTable('MembershipOrganizationOpenEnded', 'membershiporganization_membershiporganizationopenended'),
    ]
