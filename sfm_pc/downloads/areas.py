from collections import OrderedDict

from django.conf import settings
from django.db import models
from django.contrib.postgres import fields as pg_fields
from django_date_extensions.fields import ApproximateDateField

from .base import BaseDownload
from organization.models import Organization


class AreaDownload(BaseDownload):
    # Class metadata
    download_type = 'areas'

    # Download fields
    org_id = models.UUIDField()
    name = models.TextField()
    name_confidence = models.CharField(max_length=1)
    division_id = models.TextField()
    division_id_confidence = models.CharField(max_length=1)
    classifications = pg_fields.ArrayField(models.TextField(), default=list)
    classifications_confidence = models.CharField(max_length=1)
    aliases = pg_fields.ArrayField(models.TextField(), default=list)
    aliases_confidence = models.CharField(max_length=1)
    firstciteddate = ApproximateDateField()
    firstciteddate_confidence = models.CharField(max_length=1)
    lastciteddate = ApproximateDateField()
    lastciteddate_confidence = models.CharField(max_length=1)
    realstart = models.NullBooleanField(default=None)
    realstart_confidence = models.CharField(max_length=1)
    open_ended = models.CharField(max_length=1, default='N', choices=settings.OPEN_ENDED_CHOICES)
    open_ended_confidence = models.CharField(max_length=1)
    area_id = models.BigIntegerField()
    area_id_confidence = models.CharField(max_length=1)
    area_name = models.TextField()
    area_division_id = models.TextField()
    area_feature_type = models.TextField()
    area_admin_level = models.TextField()
    area_admin_level_1_id = models.BigIntegerField()
    area_admin_level_1_name = models.BigIntegerField()
    area_admin_level_2_id = models.BigIntegerField()
    area_admin_level_2_name = models.BigIntegerField()

    @classmethod
    def _get_field_map(cls):
        """
        Return metadata for each field defined on this model, to aid in serializing
        and exporing data.
        """
        return OrderedDict([
            ('org_id', {
                'sql': 'organization.uuid',
                'label': 'unit:id:admin',
                'serializer': cls.serializers['string'],
            }),
            ('name', {
                'sql': 'organization.name',
                'label': Organization.get_spreadsheet_field_name('name'),
                'serializer': cls.serializers['identity'],
            }),
            ('name_confidence', {
                'sql': 'organization.name_confidence',
                'label': Organization.get_spreadsheet_confidence_field_name('name'),
                'confidence': True,
                'serializer': cls.serializers['identity'],
            }),
            ('division_id', {
                'sql': 'organization.division_id',
                'label': Organization.get_spreadsheet_field_name('division_id'),
                'serializer': cls.serializers['division_id'],
            }),
            ('division_id_confidence', {
                'sql': 'organization.division_id_confidence',
                'label': Organization.get_spreadsheet_confidence_field_name('division_id'),
                'confidence': True,
                'serializer': cls.serializers['identity'],
            }),
            ('classifications', {
                'sql': 'organization.classifications',
                'label': Organization.get_spreadsheet_field_name('classification'),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_confidence', {
                'sql': 'organization.classifications_confidence',
                'label': Organization.get_spreadsheet_confidence_field_name('classification'),
                'confidence': True,
                'serializer': cls.serializers['identity'],
            }),
            ('aliases', {
                'sql': 'organization.aliases',
                'label': Organization.get_spreadsheet_field_name('aliases'),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_confidence', {
                'sql': 'organization.aliases_confidence',
                'label': Organization.get_spreadsheet_confidence_field_name('aliases'),
                'confidence': True,
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate', {
                'sql': 'organization.first_cited_date',
                'label': Organization.get_spreadsheet_field_name('firstciteddate'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate_confidence', {
                'sql': 'organization.first_cited_date_confidence',
                'label': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'confidence': True,
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate', {
                'sql': 'organization.last_cited_date',
                'label': Organization.get_spreadsheet_field_name('lastciteddate'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate_confidence', {
                'sql': 'organization.last_cited_date_confidence',
                'label': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'confidence': True,
                'serializer': cls.serializers['identity'],
            }),
            ('realstart', {
                'sql': 'organization.real_start',
                'label': Organization.get_spreadsheet_field_name('realstart'),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart_confidence', {
                'sql': 'organization.real_start_confidence',
                'label': Organization.get_spreadsheet_confidence_field_name('realstart'),
                'confidence': True,
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended', {
                'sql': 'organization.open_ended',
                'label': Organization.get_spreadsheet_field_name('open_ended'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended_confidence', {
                'sql': 'organization.open_ended_confidence',
                'label': Organization.get_spreadsheet_confidence_field_name('open_ended'),
                'confidence': True,
                'serializer': cls.serializers['identity'],
            }),
            ('area_id', {
                'sql': 'association.area_id',
                'label': 'unit:area_ops_id',
                'serializer': cls.serializers['identity'],
            }),
            ('area_id_confidence', {
                'sql': 'association.area_confidence',
                'label': 'unit:area_ops_id:confidence',
                'confidence': True,
                'serializer': cls.serializers['identity'],
            }),
            ('area_name', {
                'sql': 'location.name',
                'label': 'unit:area_ops_name',
                'serializer': cls.serializers['identity'],
            }),
            ('area_division_id', {
                'sql': 'location.division_id',
                'label': 'unit:area_ops_country',
                'serializer': cls.serializers['division_id'],
            }),
            ('area_feature_type', {
                'sql': 'location.feature_type',
                'label': 'unit:area_ops_feature_type',
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level', {
                'sql': 'location.admin_level',
                'label': 'unit:area_ops_admin_level',
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level_1_id', {
                'sql': 'location.admin_level_1_id',
                'label': 'unit:area_ops_admin_level_1_id',
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level_1_name', {
                'sql': 'location.admin_level_1_name',
                'label': 'unit:area_ops_admin_level_1_name',
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level_2_id', {
                'sql': 'location.admin_level_2_id',
                'label': 'unit:area_ops_admin_level_2_id',
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level_2_name', {
                'sql': 'location.admin_level_2_name',
                'label': 'unit:area_ops_admin_level_2_name',
                'serializer': cls.serializers['identity'],
            }),
        ])
