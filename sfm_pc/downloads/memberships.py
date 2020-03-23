from collections import OrderedDict

from django.db import models
from django.conf import settings
from django.db.models import Max, Case, When, Value, CharField, F
from django.contrib.postgres import fields as pg_fields
from django_date_extensions.fields import ApproximateDateField

from sfm_pc.fields import DistinctArrayAgg
from sfm_pc.downloads import mixins
from organization.models import Organization
from membershiporganization.models import MembershipOrganization


class MembershipOrganizationDownload(mixins.DownloadMixin, models.Model):
    membership_id = models.IntegerField(primary_key=True)
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
    member_id = models.UUIDField()
    member_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    member_id_confidence = models.CharField(max_length=1)
    member_name = models.TextField()
    member_name_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    member_name_confidence = models.CharField(max_length=1)
    member_division_id = models.TextField()
    member_division_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    member_division_id_confidence = models.CharField(max_length=1)
    member_classifications = pg_fields.ArrayField(models.TextField(), default=list)
    member_classifications_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    member_classifications_confidence = models.CharField(max_length=1)
    member_firstciteddate = ApproximateDateField()
    member_firstciteddate_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    member_firstciteddate_confidence = models.CharField(max_length=1)
    member_lastciteddate = ApproximateDateField()
    member_lastciteddate_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    member_lastciteddate_confidence = models.CharField(max_length=1)
    member_realstart = models.NullBooleanField(default=None)
    member_realstart_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    member_realstart_confidence = models.CharField(max_length=1)
    member_realend = models.NullBooleanField(default=None)
    member_realend_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    member_realend_confidence = models.CharField(max_length=1)

    model = MembershipOrganization
    published_filters = {
        'membershiporganizationmember__value__published': True,
        'membershiporganizationorganization__value__published': True
    }

    @classmethod
    def _get_field_map(cls):
        return OrderedDict([
            ('org_id', {
                'header': 'unit:id:admin',
                'value': F('membershiporganizationmember__value__uuid'),
                'serializer': cls.serializers['string'],
            }),
            ('name', {
                'header': Organization.get_spreadsheet_field_name('name'),
                'value': Max('membershiporganizationmember__value__organizationname__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('name_sources', {
                'header': Organization.get_spreadsheet_source_field_name('name'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationname__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('name_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('name'),
                'confidence': True,
                'value': Max('membershiporganizationmember__value__organizationname__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('division_id', {
                'header': Organization.get_spreadsheet_field_name('division_id'),
                'value': Max('membershiporganizationmember__value__organizationdivisionid__value'),
                'serializer': cls.serializers['division_id'],
            }),
            ('division_id_sources', {
                'header': Organization.get_spreadsheet_source_field_name('division_id'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationdivisionid__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('division_id_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('division_id'),
                'confidence': True,
                'value': Max('membershiporganizationmember__value__organizationdivisionid__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('classifications', {
                'header': Organization.get_spreadsheet_field_name('classification'),
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationclassification__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_sources', {
                'header': Organization.get_spreadsheet_source_field_name('classification'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationclassification__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('classification'),
                'confidence': True,
                'value': Max('membershiporganizationmember__value__organizationclassification__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('aliases', {
                'header': Organization.get_spreadsheet_field_name('aliases'),
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationalias__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_sources', {
                'header': Organization.get_spreadsheet_source_field_name('aliases'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationalias__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('aliases'),
                'confidence': True,
                'value': Max('membershiporganizationmember__value__organizationalias__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate', {
                'header': Organization.get_spreadsheet_field_name('firstciteddate'),
                'value': Max('membershiporganizationmember__value__organizationfirstciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('firstciteddate'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationfirstciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('firstciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'confidence': True,
                'value': Max('membershiporganizationmember__value__organizationfirstciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate', {
                'header': Organization.get_spreadsheet_field_name('lastciteddate'),
                'value': Max('membershiporganizationmember__value__organizationlastciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('lastciteddate'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationlastciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('lastciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'confidence': True,
                'value': Max('membershiporganizationmember__value__organizationlastciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart', {
                'header': Organization.get_spreadsheet_field_name('realstart'),
                'value': Max(
                    Case(
                        When(membershiporganizationmember__value__organizationrealstart__value=True, then=Value('Y')),
                        When(membershiporganizationmember__value__organizationrealstart__value=False, then=Value('N')),
                        When(membershiporganizationmember__value__organizationrealstart__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart_sources', {
                'header': Organization.get_spreadsheet_source_field_name('realstart'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationrealstart__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('realstart_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('realstart'),
                'confidence': True,
                'value': Max('membershiporganizationmember__value__organizationrealstart__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended', {
                'header': Organization.get_spreadsheet_field_name('open_ended'),
                'value': Max('membershiporganizationmember__value__organizationopenended__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended_sources', {
                'header': Organization.get_spreadsheet_source_field_name('open_ended'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationmember__value__organizationopenended__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('open_ended_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('open_ended'),
                'confidence': True,
                'value': Max('membershiporganizationmember__value__organizationopenended__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_id', {
                'header': 'unit:membership_id',
                'value': F('membershiporganizationorganization__value__uuid'),
                'serializer': cls.serializers['string'],
            }),
            ('member_id_sources', {
                'header': 'unit:membership_id:source',
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationorganization__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('member_id_confidence', {
                'header': 'unit:membership_id:confidence',
                'confidence': True,
                'value': Max('membershiporganizationorganization__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_name', {
                'header': MembershipOrganization.get_spreadsheet_field_name('organization'),
                'value': Max('membershiporganizationorganization__value__organizationname__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_name_sources', {
                'header': MembershipOrganization.get_spreadsheet_source_field_name('organization'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationorganization__value__organizationname__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('member_name_confidence', {
                'header': MembershipOrganization.get_spreadsheet_confidence_field_name('organization'),
                'confidence': True,
                'value': Max('membershiporganizationorganization__value__organizationname__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_division_id', {
                'header': 'unit:member_country',
                'value': Max('membershiporganizationorganization__value__organizationdivisionid__value'),
                'serializer': cls.serializers['division_id'],
            }),
            ('member_division_id_sources', {
                'header': 'unit:member_country:source',
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationorganization__value__organizationdivisionid__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('member_division_id_confidence', {
                'header': 'unit:member_country:confidence',
                'confidence': True,
                'value': Max('membershiporganizationorganization__value__organizationdivisionid__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_classifications', {
                'header': 'unit:member_classification',
                'value': DistinctArrayAgg('membershiporganizationorganization__value__organizationclassification__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('member_classifications_sources', {
                'header': 'unit:member_classification:source',
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationorganization__value__organizationclassification__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('member_classifications_confidence', {
                'header': 'unit:member_classification:confidence',
                'confidence': True,
                'value': Max('membershiporganizationorganization__value__organizationclassification__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_firstciteddate', {
                'header': MembershipOrganization.get_spreadsheet_field_name('firstciteddate'),
                'value': Max('membershiporganizationfirstciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_firstciteddate_sources', {
                'header': MembershipOrganization.get_spreadsheet_source_field_name('firstciteddate'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationfirstciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('member_firstciteddate_confidence', {
                'header': MembershipOrganization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'confidence': True,
                'value': Max('membershiporganizationfirstciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_realstart', {
                'header': MembershipOrganization.get_spreadsheet_field_name('realstart'),
                'value': Max(
                    Case(
                        When(membershiporganizationrealstart__value=True, then=Value('Y')),
                        When(membershiporganizationrealstart__value=False, then=Value('N')),
                        When(membershiporganizationrealstart__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('member_realstart_sources', {
                'header': MembershipOrganization.get_spreadsheet_source_field_name('realstart'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationrealstart__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('member_realstart_confidence', {
                'header': MembershipOrganization.get_spreadsheet_confidence_field_name('realstart'),
                'confidence': True,
                'value': Max('membershiporganizationrealstart__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_lastciteddate', {
                'header': MembershipOrganization.get_spreadsheet_field_name('lastciteddate'),
                'value': Max('membershiporganizationlastciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_lastciteddate_sources', {
                'header': MembershipOrganization.get_spreadsheet_source_field_name('lastciteddate'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationlastciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('member_lastciteddate_confidence', {
                'header': MembershipOrganization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'confidence': True,
                'value': Max('membershiporganizationlastciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('member_realend', {
                'header': MembershipOrganization.get_spreadsheet_field_name('realend'),
                'value': Max(
                    Case(
                        When(membershiporganizationrealend__value=True, then=Value('Y')),
                        When(membershiporganizationrealend__value=False, then=Value('N')),
                        When(membershiporganizationrealend__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('member_realend_sources', {
                'header': MembershipOrganization.get_spreadsheet_source_field_name('realend'),
                'source': True,
                'value': DistinctArrayAgg('membershiporganizationrealend__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('member_realend_confidence', {
                'header': MembershipOrganization.get_spreadsheet_confidence_field_name('realend'),
                'confidence': True,
                'value': Max('membershiporganizationrealend__confidence'),
                'serializer': cls.serializers['identity'],
            }),
        ])
