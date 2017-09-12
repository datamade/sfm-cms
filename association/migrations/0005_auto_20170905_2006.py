# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-09-05 20:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def map_new_type(apps, schema_editor):

    AssociationOpenEnded = apps.get_model("association", "AssociationOpenEnded")
    db_alias = schema_editor.connection.alias

    associations = AssociationOpenEnded.objects.using(db_alias).all()

    for assoc in associations:

        if assoc.value == True:

            assoc.new_value = 'Y'

        elif assoc.value == False:

            assoc.new_value = 'E'

        else:

            assoc.new_value = 'N'

        assoc.save()


class Migration(migrations.Migration):

    dependencies = [
        ('source', '0017_auto_20160826_2057'),
        ('association', '0004_associationopenended'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssociationRealStart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lang', models.CharField(max_length=5, null=True)),
                ('confidence', models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1)),
                ('value', models.NullBooleanField(default=None)),
                ('object_ref', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='association.Association')),
                ('sources', models.ManyToManyField(related_name='association_associationrealstart_related', to='source.Source')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunSQL(
            'SET CONSTRAINTS ALL IMMEDIATE',
            reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(
            'DROP MATERIALIZED VIEW IF EXISTS association',
            reverse_sql=migrations.RunSQL.noop),
        migrations.AddField(
            model_name='associationopenended',
            name='new_value',
            field=models.CharField(choices=[('Y', 'Yes'), ('N', 'No'), ('E', 'Exact')], default='N', max_length=1),
        ),
        migrations.RunPython(map_new_type),
        migrations.RemoveField(
            model_name='associationopenended',
            name='value',
        ),
        migrations.RenameField(
            model_name='associationopenended',
            old_name='new_value',
            new_name='value'
        ),
        migrations.RunSQL(
            migrations.RunSQL.noop,
            reverse_sql='SET CONSTRAINTS ALL IMMEDIATE'
        )
    ]
