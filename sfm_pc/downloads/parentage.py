from collections import OrderedDict

from django.db import models
from django.conf import settings
from django.db.models import Max, Case, When, Value, CharField, F
from django.contrib.postgres import fields as pg_fields
from django_date_extensions.fields import ApproximateDateField

from sfm_pc.fields import DistinctArrayAgg
from sfm_pc.downloads import mixins
from organization.models import Organization
from composition.models import Composition


class ParentageDownload(mixins.DownloadMixin, models.Model):
    composition_id = models.IntegerField(primary_key=True)
    child_unit_id = models.UUIDField()
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
    related_id = models.UUIDField()
    related_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    related_id_confidence = models.CharField(max_length=1)
    related_classifications = pg_fields.ArrayField(models.TextField(), default=list)
    related_classifications_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    related_classifications_confidence = models.CharField(max_length=1)
    related_firstciteddate = ApproximateDateField()
    related_firstciteddate_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    related_firstciteddate_confidence = models.CharField(max_length=1)
    related_lastciteddate = ApproximateDateField()
    related_lastciteddate_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    related_lastciteddate_confidence = models.CharField(max_length=1)
    related_realstart = models.NullBooleanField(default=None)
    related_realstart_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    related_realstart_confidence = models.CharField(max_length=1)
    related_open_ended = models.CharField(max_length=1, default='N', choices=settings.OPEN_ENDED_CHOICES)
    related_open_ended_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    related_open_ended_confidence = models.CharField(max_length=1)

    model = Composition
    published_filters = {
        'compositionchild__value__published': True,
        'compositionparent__value__published': True
    }

    @classmethod
    def _get_field_map(cls):
        return OrderedDict([
            ('child_id', {
                'header': 'unit:id:admin',
                'value': F('compositionchild__value__uuid'),
                'serializer': cls.serializers['string'],
            }),
            ('name', {
                'header': Organization.get_spreadsheet_field_name('name'),
                'value': Max('compositionchild__value__organizationname__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('name_sources', {
                'header': Organization.get_spreadsheet_source_field_name('name'),
                'source': True,
                'value': DistinctArrayAgg('compositionchild__value__organizationname__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('name_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('name'),
                'confidence': True,
                'value': Max('compositionchild__value__organizationname__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('division_id', {
                'header': Organization.get_spreadsheet_field_name('division_id'),
                'value': Max('compositionchild__value__organizationdivisionid__value'),
                'serializer': cls.serializers['division_id'],
            }),
            ('division_id_sources', {
                'header': Organization.get_spreadsheet_source_field_name('division_id'),
                'source': True,
                'value': DistinctArrayAgg('compositionchild__value__organizationdivisionid__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('division_id_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('division_id'),
                'confidence': True,
                'value': Max('compositionchild__value__organizationdivisionid__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('classifications', {
                'header': Organization.get_spreadsheet_field_name('classification'),
                'value': DistinctArrayAgg('compositionchild__value__organizationclassification__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_sources', {
                'header': Organization.get_spreadsheet_source_field_name('classification'),
                'source': True,
                'value': DistinctArrayAgg('compositionchild__value__organizationclassification__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('classification'),
                'confidence': True,
                'value': Max('compositionchild__value__organizationclassification__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('aliases', {
                'header': Organization.get_spreadsheet_field_name('aliases'),
                'value': DistinctArrayAgg('compositionchild__value__organizationalias__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_sources', {
                'header': Organization.get_spreadsheet_source_field_name('aliases'),
                'source': True,
                'value': DistinctArrayAgg('compositionchild__value__organizationalias__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('aliases'),
                'confidence': True,
                'value': Max('compositionchild__value__organizationalias__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate', {
                'header': Organization.get_spreadsheet_field_name('firstciteddate'),
                'value': Max('compositionchild__value__organizationfirstciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('firstciteddate'),
                'source': True,
                'value': DistinctArrayAgg('compositionchild__value__organizationfirstciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('firstciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'confidence': True,
                'value': Max('compositionchild__value__organizationfirstciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate', {
                'header': Organization.get_spreadsheet_field_name('lastciteddate'),
                'value': Max('compositionchild__value__organizationlastciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('lastciteddate'),
                'source': True,
                'value': DistinctArrayAgg('compositionchild__value__organizationlastciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('lastciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'confidence': True,
                'value': Max('compositionchild__value__organizationlastciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart', {
                'header': Organization.get_spreadsheet_field_name('realstart'),
                'value': Max(
                    Case(
                        When(compositionchild__value__organizationrealstart__value=True, then=Value('Y')),
                        When(compositionchild__value__organizationrealstart__value=False, then=Value('N')),
                        When(compositionchild__value__organizationrealstart__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart_sources', {
                'header': Organization.get_spreadsheet_source_field_name('realstart'),
                'source': True,
                'value': DistinctArrayAgg('compositionchild__value__organizationrealstart__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('realstart_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('realstart'),
                'confidence': True,
                'value': Max('compositionchild__value__organizationrealstart__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended', {
                'header': Organization.get_spreadsheet_field_name('open_ended'),
                'value': Max('compositionchild__value__organizationopenended__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended_sources', {
                'header': Organization.get_spreadsheet_source_field_name('open_ended'),
                'source': True,
                'value': DistinctArrayAgg('compositionchild__value__organizationopenended__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('open_ended_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('open_ended'),
                'confidence': True,
                'value': Max('compositionchild__value__organizationopenended__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_id', {
                'header': Composition.get_spreadsheet_field_name('parent'),
                'value': F('compositionparent__value__uuid'),
                'serializer': cls.serializers['string'],
            }),
            ('related_id_sources', {
                'header': Composition.get_spreadsheet_source_field_name('parent'),
                'source': True,
                'value': DistinctArrayAgg('compositionparent__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('related_id_confidence', {
                'header': Composition.get_spreadsheet_confidence_field_name('parent'),
                'confidence': True,
                'value': Max('compositionparent__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_name', {
                'header': Composition.get_spreadsheet_field_name('parent') + ':name',
                'value': Max('compositionparent__value__organizationname__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_name_sources', {
                'header': Composition.get_spreadsheet_field_name('parent') + ':name:source',
                'source': True,
                'value': DistinctArrayAgg('compositionparent__value__organizationname__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('related_name_confidence', {
                'header': Composition.get_spreadsheet_field_name('parent') + ':name:confidence',
                'confidence': True,
                'value': Max('compositionparent__value__organizationname__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_division_id', {
                'header': Composition.get_spreadsheet_field_name('parent') + ':country',
                'value': Max('compositionparent__value__organizationdivisionid__value'),
                'serializer': cls.serializers['division_id'],
            }),
            ('related_division_id_sources', {
                'header': Composition.get_spreadsheet_field_name('parent') + ':country:sources',
                'source': True,
                'value': DistinctArrayAgg('compositionparent__value__organizationdivisionid__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('related_division_id_confidence', {
                'header': Composition.get_spreadsheet_field_name('parent') + ':country:confidence',
                'confidence': True,
                'value': Max('compositionparent__value__organizationdivisionid__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_classifications', {
                'header': Composition.get_spreadsheet_field_name('classification'),
                'value': DistinctArrayAgg('compositionclassification__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('related_classifications_sources', {
                'header': Composition.get_spreadsheet_source_field_name('classification'),
                'source': True,
                'value': DistinctArrayAgg('compositionclassification__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('related_classifications_confidence', {
                'header': Composition.get_spreadsheet_confidence_field_name('classification'),
                'confidence': True,
                'value': Max('compositionclassification__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_firstciteddate', {
                'header': Composition.get_spreadsheet_field_name('startdate'),
                'value': Max('compositionstartdate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_firstciteddate_sources', {
                'header': Composition.get_spreadsheet_source_field_name('startdate'),
                'source': True,
                'value': DistinctArrayAgg('compositionstartdate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('related_firstciteddate_confidence', {
                'header': Composition.get_spreadsheet_confidence_field_name('startdate'),
                'confidence': True,
                'value': Max('compositionstartdate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_realstart', {
                'header': Composition.get_spreadsheet_field_name('realstart'),
                'value': Max(
                    Case(
                        When(compositionrealstart__value=True, then=Value('Y')),
                        When(compositionrealstart__value=False, then=Value('N')),
                        When(compositionrealstart__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('related_realstart_sources', {
                'header': Composition.get_spreadsheet_source_field_name('realstart'),
                'source': True,
                'value': DistinctArrayAgg('compositionrealstart__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('related_realstart_confidence', {
                'header': Composition.get_spreadsheet_confidence_field_name('realstart'),
                'confidence': True,
                'value': Max('compositionrealstart__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_lastciteddate', {
                'header': Composition.get_spreadsheet_field_name('enddate'),
                'value': Max('compositionenddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_lastciteddate_sources', {
                'header': Composition.get_spreadsheet_source_field_name('enddate'),
                'source': True,
                'value': DistinctArrayAgg('compositionenddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('related_lastciteddate_confidence', {
                'header': Composition.get_spreadsheet_confidence_field_name('enddate'),
                'confidence': True,
                'value': Max('compositionenddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_open_ended', {
                'header': Composition.get_spreadsheet_field_name('open_ended'),
                'value': Max('compositionopenended__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('related_open_ended_sources', {
                'header': Composition.get_spreadsheet_source_field_name('open_ended'),
                'source': True,
                'value': DistinctArrayAgg('compositionopenended__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('related_open_ended_confidence', {
                'header': Composition.get_spreadsheet_confidence_field_name('open_ended'),
                'confidence': True,
                'value': Max('compositionopenended__confidence'),
                'serializer': cls.serializers['identity'],
            }),
        ])
