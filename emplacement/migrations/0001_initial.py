# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import complex_fields.base_models
import django_date_extensions.fields


class Migration(migrations.Migration):

    dependencies = [
        ('source', '0023_auto_20180604_1610'),
        ('location', '0001_initial'),
        ('organization', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Emplacement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
            ],
            bases=(models.Model, complex_fields.base_models.BaseModel),
        ),
        migrations.CreateModel(
            name='EmplacementEndDate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('lang', models.CharField(max_length=5, null=True)),
                ('confidence', models.CharField(default=1, max_length=1, choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')])),
                ('value', django_date_extensions.fields.ApproximateDateField(max_length=10, blank=True, null=True, default=None)),
                ('object_ref', models.ForeignKey(to='emplacement.Emplacement')),
                ('sources', models.ManyToManyField(to='source.Source', related_name='emplacement_emplacementenddate_related')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EmplacementOrganization',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('lang', models.CharField(max_length=5, null=True)),
                ('confidence', models.CharField(default=1, max_length=1, choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')])),
                ('object_ref', models.ForeignKey(to='emplacement.Emplacement')),
                ('sources', models.ManyToManyField(to='source.Source', related_name='emplacement_emplacementorganization_related')),
                ('value', models.ForeignKey(to='organization.Organization')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EmplacementSite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('lang', models.CharField(max_length=5, null=True)),
                ('confidence', models.CharField(default=1, max_length=1, choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')])),
                ('object_ref', models.ForeignKey(to='emplacement.Emplacement')),
                ('sources', models.ManyToManyField(to='source.Source', related_name='emplacement_emplacementsite_related')),
                ('value', models.ForeignKey(to='location.Location')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EmplacementStartDate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('lang', models.CharField(max_length=5, null=True)),
                ('confidence', models.CharField(default=1, max_length=1, choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')])),
                ('value', django_date_extensions.fields.ApproximateDateField(max_length=10, blank=True, null=True, default=None)),
                ('object_ref', models.ForeignKey(to='emplacement.Emplacement')),
                ('sources', models.ManyToManyField(to='source.Source', related_name='emplacement_emplacementstartdate_related')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
