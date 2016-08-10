# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-10 20:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('source', '0014_auto_20160805_2031'),
        ('geosite', '0004_auto_20160810_1741'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeositeDivisionId',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lang', models.CharField(max_length=5, null=True)),
                ('confidence', models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1)),
                ('value', models.TextField(blank=True, default=None, null=True)),
                ('object_ref', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='geosite.Geosite')),
                ('sources', models.ManyToManyField(related_name='geosite_geositedivisionid_related', to='source.Source')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='geositeadminlevel1',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AlterField(
            model_name='geositeadminlevel2',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AlterField(
            model_name='geositecoordinates',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AlterField(
            model_name='geositegeoname',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AlterField(
            model_name='geositegeonameid',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
        migrations.AlterField(
            model_name='geositename',
            name='confidence',
            field=models.CharField(choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default=1, max_length=1),
        ),
    ]
