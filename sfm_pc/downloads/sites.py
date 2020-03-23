from collections import OrderedDict

from django.db import models
from django.conf import settings
from django.db.models import Max, Case, When, Value, CharField, F
from django.contrib.postgres import fields as pg_fields
from django_date_extensions.fields import ApproximateDateField

from sfm_pc.fields import DistinctArrayAgg
from sfm_pc.downloads import mixins
from organization.models import Organization
from emplacement.models import Emplacement


class SiteDownload(mixins.DownloadMixin, models.Model):
    emplacement_id = models.IntegerField(primary_key=True)
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
    site_id = models.BigIntegerField()
    site_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    site_confidence = models.CharField(max_length=1)
    site_osm_feature_type = models.TextField()
    site_osm_feature_type_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    site_osm_feature_type_confidence = models.CharField(max_length=1)
    site_admin_level = models.TextField()
    site_admin_level_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    site_admin_level_confidence = models.CharField(max_length=1)
    site_admin_level_1_id = models.BigIntegerField()
    site_admin_level_1_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    site_admin_level_1_id_confidence = models.CharField(max_length=1)
    site_admin_level_1_name = models.BigIntegerField()
    site_admin_level_1_name_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    site_admin_level_1_name_confidence = models.CharField(max_length=1)
    site_admin_level_2_id = models.BigIntegerField()
    site_admin_level_2_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    site_admin_level_2_id_confidence = models.CharField(max_length=1)
    site_admin_level_2_name = models.BigIntegerField()
    site_admin_level_2_name_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    site_admin_level_2_name_confidence = models.CharField(max_length=1)

    model = Emplacement
    published_filters = {
        'emplacementorganization__value__published': True,
    }

    @classmethod
    def _get_field_map(cls):
        return OrderedDict([
            ('org_id', {
                'header': 'unit:id:admin',
                'value': F('emplacementorganization__value__uuid'),
                'serializer': cls.serializers['string'],
            }),
            ('name', {
                'header': Organization.get_spreadsheet_field_name('name'),
                'value': Max('emplacementorganization__value__organizationname__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('name_sources', {
                'header': Organization.get_spreadsheet_source_field_name('name'),
                'source': True,
                'value': DistinctArrayAgg('emplacementorganization__value__organizationname__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('name_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('name'),
                'confidence': True,
                'value': Max('emplacementorganization__value__organizationname__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('division_id', {
                'header': Organization.get_spreadsheet_field_name('division_id'),
                'value': Max('emplacementorganization__value__organizationdivisionid__value'),
                'serializer': cls.serializers['division_id'],
            }),
            ('division_id_sources', {
                'header': Organization.get_spreadsheet_source_field_name('division_id'),
                'source': True,
                'value': DistinctArrayAgg('emplacementorganization__value__organizationdivisionid__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('division_id_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('division_id'),
                'confidence': True,
                'value': Max('emplacementorganization__value__organizationdivisionid__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('classifications', {
                'header': Organization.get_spreadsheet_field_name('classification'),
                'value': DistinctArrayAgg('emplacementorganization__value__organizationclassification__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_sources', {
                'header': Organization.get_spreadsheet_source_field_name('classification'),
                'source': True,
                'value': DistinctArrayAgg('emplacementorganization__value__organizationclassification__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('classification'),
                'confidence': True,
                'value': Max('emplacementorganization__value__organizationclassification__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('aliases', {
                'header': Organization.get_spreadsheet_field_name('aliases'),
                'value': DistinctArrayAgg('emplacementorganization__value__organizationalias__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_sources', {
                'header': Organization.get_spreadsheet_source_field_name('aliases'),
                'source': True,
                'value': DistinctArrayAgg('emplacementorganization__value__organizationalias__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('aliases'),
                'confidence': True,
                'value': Max('emplacementorganization__value__organizationalias__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate', {
                'header': Organization.get_spreadsheet_field_name('firstciteddate'),
                'value': Max('emplacementorganization__value__organizationfirstciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('firstciteddate'),
                'source': True,
                'value': DistinctArrayAgg('emplacementorganization__value__organizationfirstciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('firstciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'confidence': True,
                'value': Max('emplacementorganization__value__organizationfirstciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate', {
                'header': Organization.get_spreadsheet_field_name('lastciteddate'),
                'value': Max('emplacementorganization__value__organizationlastciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('lastciteddate'),
                'source': True,
                'value': DistinctArrayAgg('emplacementorganization__value__organizationlastciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('lastciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'confidence': True,
                'value': Max('emplacementorganization__value__organizationlastciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart', {
                'header': Organization.get_spreadsheet_field_name('realstart'),
                'value': Max(
                    Case(
                        When(emplacementorganization__value__organizationrealstart__value=True, then=Value('Y')),
                        When(emplacementorganization__value__organizationrealstart__value=False, then=Value('N')),
                        When(emplacementorganization__value__organizationrealstart__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart_sources', {
                'header': Organization.get_spreadsheet_source_field_name('realstart'),
                'source': True,
                'value': DistinctArrayAgg('emplacementorganization__value__organizationrealstart__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('realstart_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('realstart'),
                'confidence': True,
                'value': Max('emplacementorganization__value__organizationrealstart__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended', {
                'header': Organization.get_spreadsheet_field_name('open_ended'),
                'value': Max('emplacementorganization__value__organizationopenended__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended_sources', {
                'header': Organization.get_spreadsheet_source_field_name('open_ended'),
                'source': True,
                'value': DistinctArrayAgg('emplacementorganization__value__organizationopenended__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('open_ended_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('open_ended'),
                'confidence': True,
                'value': Max('emplacementorganization__value__organizationopenended__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('site_id', {
                'header': 'unit:site_exact_location_id_latitude',
                'value': F('emplacementsite__value__id'),
                'serializer': cls.serializers['identity'],
            }),
            ('site_id_sources', {
                'header': 'unit:site_exact_location:source',
                'source': True,
                'value': DistinctArrayAgg('emplacementsite__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('site_id_confidence', {
                'header': 'unit:site_exact_location:confidence',
                'confidence': True,
                'value': Max('emplacementsite__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('site_name', {
                'header': 'unit:site_exact_location_name_longitude',
                'value': Max('emplacementsite__value__name'),
                'serializer': cls.serializers['identity'],
            }),
            ('site_division_id', {
                'header': 'unit:site_country',
                'value': Max('emplacementsite__value__division_id'),
                'serializer': cls.serializers['division_id'],
            }),
            ('site_osm_feature_type', {
                'header': 'unit:site_feature_type',
                'value': Max('emplacementsite__value__feature_type'),
                'serializer': cls.serializers['identity'],
            }),
            ('site_admin_level', {
                'header': 'unit:site_admin_level',
                'value': Max('emplacementsite__value__adminlevel'),
                'serializer': cls.serializers['identity'],
            }),
            ('site_admin_level_1_id', {
                'header': 'unit:site_nearest_settlement_id',
                'value': Max('emplacementsite__value__adminlevel1__id'),
                'serializer': cls.serializers['identity'],
            }),
            ('site_admin_level_1_name', {
                'header': 'unit:site_nearest_settlement_name',
                'value': Max('emplacementsite__value__adminlevel1__name'),
                'serializer': cls.serializers['identity'],
            }),
            ('site_admin_level_2_id', {
                'header': 'unit:site_first_admin_area_id',
                'value': Max('emplacementsite__value__adminlevel2__id'),
                'serializer': cls.serializers['identity'],
            }),
            ('site_admin_level_2_name', {
                'header': 'unit:site_first_admin_area_name',
                'value': Max('emplacementsite__value__adminlevel2__name'),
                'serializer': cls.serializers['identity'],
            }),
        ])
