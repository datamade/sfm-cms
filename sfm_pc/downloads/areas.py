from collections import OrderedDict

from django.db import models
from django.conf import settings
from django.db.models import Max, Case, When, Value, CharField, F
from django.contrib.postgres import fields as pg_fields
from django_date_extensions.fields import ApproximateDateField

from sfm_pc.fields import DistinctArrayAgg
from sfm_pc.downloads import mixins
from organization.models import Organization
from association.models import Association


class AreaDownload(mixins.DownloadMixin, models.Model):
    association_id = models.IntegerField(primary_key=True)
    org_id = models.UUIDField()
    name = models.TextField()
    name_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    name_confidence = models.CharField(max_length=1)
    division_id = models.TextField()
    division_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    division_id_confidence = models.CharField(max_length=1)
    classifications = pg_fields.ArrayField(models.TextField(), default=list)
    classifications_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    classifications_confidence = models.CharField(max_length=1)
    aliases = pg_fields.ArrayField(models.TextField(), default=list)
    aliases_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    aliases_confidence = models.CharField(max_length=1)
    firstciteddate = ApproximateDateField()
    firstciteddate_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    firstciteddate_confidence = models.CharField(max_length=1)
    lastciteddate = ApproximateDateField()
    lastciteddate_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    lastciteddate_confidence = models.CharField(max_length=1)
    realstart = models.NullBooleanField(default=None)
    realstart_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    realstart_confidence = models.CharField(max_length=1)
    open_ended = models.CharField(max_length=1, default='N', choices=settings.OPEN_ENDED_CHOICES)
    open_ended_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    open_ended_confidence = models.CharField(max_length=1)
    area_id = models.BigIntegerField()
    area_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    area_confidence = models.CharField(max_length=1)
    area_division_id = models.TextField()
    area_division_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    area_division_id_confidence = models.CharField(max_length=1)
    area_osm_feature_type = models.TextField()
    area_osm_feature_type_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    area_osm_feature_type_confidence = models.CharField(max_length=1)
    area_admin_level = models.TextField()
    area_admin_level_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    area_admin_level_confidence = models.CharField(max_length=1)
    area_admin_level_1_id = models.BigIntegerField()
    area_admin_level_1_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    area_admin_level_1_id_confidence = models.CharField(max_length=1)
    area_admin_level_1_name = models.BigIntegerField()
    area_admin_level_1_name_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    area_admin_level_1_name_confidence = models.CharField(max_length=1)
    area_admin_level_2_id = models.BigIntegerField()
    area_admin_level_2_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    area_admin_level_2_id_confidence = models.CharField(max_length=1)
    area_admin_level_2_name = models.BigIntegerField()
    area_admin_level_2_name_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    area_admin_level_2_name_confidence = models.CharField(max_length=1)

    model = Association
    published_filters = {
        'associationorganization__value__published': True,
    }

    @classmethod
    def _get_field_map(cls):
        return OrderedDict([
            ('org_id', {
                'header': 'unit:id:admin',
                'value': F('associationorganization__value__uuid'),
                'serializer': cls.serializers['string'],
            }),
            ('name', {
                'header': Organization.get_spreadsheet_field_name('name'),
                'value': Max('associationorganization__value__organizationname__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('name_sources', {
                'header': Organization.get_spreadsheet_source_field_name('name'),
                'source': True,
                'value': DistinctArrayAgg('associationorganization__value__organizationname__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('name_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('name'),
                'confidence': True,
                'value': Max('associationorganization__value__organizationname__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('division_id', {
                'header': Organization.get_spreadsheet_field_name('division_id'),
                'value': Max('associationorganization__value__organizationdivisionid__value'),
                'serializer': cls.serializers['division_id'],
            }),
            ('division_id_sources', {
                'header': Organization.get_spreadsheet_source_field_name('division_id'),
                'source': True,
                'value': DistinctArrayAgg('associationorganization__value__organizationdivisionid__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('division_id_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('division_id'),
                'confidence': True,
                'value': Max('associationorganization__value__organizationdivisionid__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('classifications', {
                'header': Organization.get_spreadsheet_field_name('classification'),
                'value': DistinctArrayAgg('associationorganization__value__organizationclassification__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_sources', {
                'header': Organization.get_spreadsheet_source_field_name('classification'),
                'source': True,
                'value': DistinctArrayAgg('associationorganization__value__organizationclassification__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('classification'),
                'confidence': True,
                'value': Max('associationorganization__value__organizationclassification__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('aliases', {
                'header': Organization.get_spreadsheet_field_name('aliases'),
                'value': DistinctArrayAgg('associationorganization__value__organizationalias__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_sources', {
                'header': Organization.get_spreadsheet_source_field_name('aliases'),
                'source': True,
                'value': DistinctArrayAgg('associationorganization__value__organizationalias__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('aliases'),
                'confidence': True,
                'value': Max('associationorganization__value__organizationalias__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate', {
                'header': Organization.get_spreadsheet_field_name('firstciteddate'),
                'value': Max('associationorganization__value__organizationfirstciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('firstciteddate'),
                'source': True,
                'value': DistinctArrayAgg('associationorganization__value__organizationfirstciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('firstciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'confidence': True,
                'value': Max('associationorganization__value__organizationfirstciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate', {
                'header': Organization.get_spreadsheet_field_name('lastciteddate'),
                'value': Max('associationorganization__value__organizationlastciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('lastciteddate'),
                'source': True,
                'value': DistinctArrayAgg('associationorganization__value__organizationlastciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('lastciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'confidence': True,
                'value': Max('associationorganization__value__organizationlastciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart', {
                'header': Organization.get_spreadsheet_field_name('realstart'),
                'value': Max(
                    Case(
                        When(associationorganization__value__organizationrealstart__value=True, then=Value('Y')),
                        When(associationorganization__value__organizationrealstart__value=False, then=Value('N')),
                        When(associationorganization__value__organizationrealstart__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart_sources', {
                'header': Organization.get_spreadsheet_source_field_name('realstart'),
                'source': True,
                'value': DistinctArrayAgg('associationorganization__value__organizationrealstart__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('realstart_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('realstart'),
                'confidence': True,
                'value': Max('associationorganization__value__organizationrealstart__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended', {
                'header': Organization.get_spreadsheet_field_name('open_ended'),
                'value': Max('associationorganization__value__organizationopenended__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended_sources', {
                'header': Organization.get_spreadsheet_source_field_name('open_ended'),
                'source': True,
                'value': DistinctArrayAgg('associationorganization__value__organizationopenended__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('open_ended_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('open_ended'),
                'confidence': True,
                'value': Max('associationorganization__value__organizationopenended__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('area_id', {
                'header': 'unit:area_ops_id',
                'value': F('associationarea__value__id'),
                'serializer': cls.serializers['identity'],
            }),
            ('area_id_sources', {
                'header': 'unit:area_ops_id:source',
                'source': True,
                'value': DistinctArrayAgg('associationarea__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('area_id_confidence', {
                'header': 'unit:area_ops_id:confidence',
                'confidence': True,
                'value': Max('associationarea__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('area_name', {
                'header': 'unit:area_ops_name',
                'value': Max('associationarea__value__name'),
                'serializer': cls.serializers['identity'],
            }),
            ('area_division_id', {
                'header': 'unit:area_ops_country',
                'value': Max('associationarea__value__division_id'),
                'serializer': cls.serializers['division_id'],
            }),
            ('area_osm_feature_type', {
                'header': 'unit:area_ops_feature_type',
                'value': Max('associationarea__value__feature_type'),
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level', {
                'header': 'unit:area_ops_admin_level',
                'value': Max('associationarea__value__adminlevel'),
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level_1_id', {
                'header': 'unit:area_ops_admin_level_1_id',
                'value': Max('associationarea__value__adminlevel1__id'),
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level_1_name', {
                'header': 'unit:area_ops_admin_level_1_name',
                'value': Max('associationarea__value__adminlevel1__name'),
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level_2_id', {
                'header': 'unit:area_ops_admin_level_2_id',
                'value': Max('associationarea__value__adminlevel2__id'),
                'serializer': cls.serializers['identity'],
            }),
            ('area_admin_level_2_name', {
                'header': 'unit:area_ops_admin_level_2_name',
                'value': Max('associationarea__value__adminlevel2__name'),
                'serializer': cls.serializers['identity'],
            }),
        ])
