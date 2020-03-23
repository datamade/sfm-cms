from collections import OrderedDict

from django.db import models
from django.conf import settings
from django.db.models import Max, Case, When, Value, CharField, F
from django.contrib.postgres import fields as pg_fields
from django_date_extensions.fields import ApproximateDateField

from sfm_pc.fields import DistinctArrayAgg
from sfm_pc.downloads import mixins
from organization.models import Organization
from person.models import Person
from personextra.models import PersonExtra
from personbiography.models import PersonBiography
from membershipperson.models import MembershipPerson


class MembershipPersonDownload(mixins.DownloadMixin, models.Model):
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
    person_id = models.UUIDField()
    person_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_id_confidence = models.CharField(max_length=1)
    person_name = models.TextField()
    person_name_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_name_confidence = models.CharField(max_length=1)
    person_aliases = pg_fields.ArrayField(models.TextField(), default=list)
    person_aliases_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_aliases_confidence = models.CharField(max_length=1)
    person_division_id = models.TextField()
    person_division_id_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_division_id_confidence = models.CharField(max_length=1)
    person_date_of_birth = ApproximateDateField()
    person_date_of_birth_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_date_of_birth_confidence = models.CharField(max_length=1)
    person_date_of_death = ApproximateDateField()
    person_date_of_death_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_date_of_death_confidence = models.CharField(max_length=1)
    person_deceased = models.BooleanField()
    person_deceased_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_deceased_confidence = models.CharField(max_length=1)
    person_account_types = pg_fields.ArrayField(models.TextField(), default=list)
    person_account_types_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_account_types_confidence = models.CharField(max_length=1)
    person_accounts = pg_fields.ArrayField(models.TextField(), default=list)
    person_accounts_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_accounts_confidence = models.CharField(max_length=1)
    person_external_link_descriptions = pg_fields.ArrayField(models.TextField(), default=list)
    person_external_link_descriptions_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_external_link_descriptions_confidence = models.CharField(max_length=1)
    person_media_descriptions = pg_fields.ArrayField(models.TextField(), default=list)
    person_media_descriptions_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_media_descriptions_confidence = models.CharField(max_length=1)
    person_notes = pg_fields.ArrayField(models.TextField(), default=list)
    person_notes_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_notes_confidence = models.CharField(max_length=1)
    person_role = models.TextField()
    person_role_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_role_confidence = models.CharField(max_length=1)
    person_rank = models.TextField()
    person_rank_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_rank_confidence = models.CharField(max_length=1)
    person_title = models.TextField()
    person_title_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_title_confidence = models.CharField(max_length=1)
    person_firstciteddate = ApproximateDateField()
    person_firstciteddate_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_firstciteddate_confidence = models.CharField(max_length=1)
    person_realstart = models.NullBooleanField(default=None)
    person_realstart_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_realstart_confidence = models.CharField(max_length=1)
    person_startcontext = models.TextField()
    person_startcontext_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_startcontext_confidence = models.CharField(max_length=1)
    person_lastciteddate = ApproximateDateField()
    person_realend = models.NullBooleanField(default=None)
    person_realend_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_realend_confidence = models.CharField(max_length=1)
    person_endcontext = models.TextField()
    person_endcontext_sources = pg_fields.ArrayField(models.UUIDField(), default=list)
    person_endcontext_confidence = models.CharField(max_length=1)

    model = MembershipPerson
    published_filters = {
        'membershippersonmember__value__published': True,
        'membershippersonorganization__value__published': True
    }

    @classmethod
    def _get_field_map(cls):
        return OrderedDict([
            ('org_id', {
                'header': 'unit:id:admin',
                'value': F('membershippersonorganization__value__uuid'),
                'serializer': cls.serializers['string'],
            }),
            ('name', {
                'header': Organization.get_spreadsheet_field_name('name'),
                'value': Max('membershippersonorganization__value__organizationname__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('name_sources', {
                'header': Organization.get_spreadsheet_source_field_name('name'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationname__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('name_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('name'),
                'confidence': True,
                'value': Max('membershippersonorganization__value__organizationname__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('division_id', {
                'header': Organization.get_spreadsheet_field_name('division_id'),
                'value': Max('membershippersonorganization__value__organizationdivisionid__value'),
                'serializer': cls.serializers['division_id'],
            }),
            ('division_id_sources', {
                'header': Organization.get_spreadsheet_source_field_name('division_id'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationdivisionid__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('division_id_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('division_id'),
                'confidence': True,
                'value': Max('membershippersonorganization__value__organizationdivisionid__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('classifications', {
                'header': Organization.get_spreadsheet_field_name('classification'),
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationclassification__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_sources', {
                'header': Organization.get_spreadsheet_source_field_name('classification'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationclassification__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('classifications_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('classification'),
                'confidence': True,
                'value': Max('membershippersonorganization__value__organizationclassification__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('aliases', {
                'header': Organization.get_spreadsheet_field_name('aliases'),
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationalias__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_sources', {
                'header': Organization.get_spreadsheet_source_field_name('aliases'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationalias__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('aliases_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('aliases'),
                'confidence': True,
                'value': Max('membershippersonorganization__value__organizationalias__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate', {
                'header': Organization.get_spreadsheet_field_name('firstciteddate'),
                'value': Max('membershippersonorganization__value__organizationfirstciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('firstciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('firstciteddate'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationfirstciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('firstciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
                'confidence': True,
                'value': Max('membershippersonorganization__value__organizationfirstciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate', {
                'header': Organization.get_spreadsheet_field_name('lastciteddate'),
                'value': Max('membershippersonorganization__value__organizationlastciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('lastciteddate_sources', {
                'header': Organization.get_spreadsheet_source_field_name('lastciteddate'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationlastciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('lastciteddate_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
                'confidence': True,
                'value': Max('membershippersonorganization__value__organizationlastciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart', {
                'header': Organization.get_spreadsheet_field_name('realstart'),
                'value': Max(
                    Case(
                        When(membershippersonorganization__value__organizationrealstart__value=True, then=Value('Y')),
                        When(membershippersonorganization__value__organizationrealstart__value=False, then=Value('N')),
                        When(membershippersonorganization__value__organizationrealstart__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('realstart_sources', {
                'header': Organization.get_spreadsheet_source_field_name('realstart'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationrealstart__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('realstart_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('realstart'),
                'confidence': True,
                'value': Max('membershippersonorganization__value__organizationrealstart__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended', {
                'header': Organization.get_spreadsheet_field_name('open_ended'),
                'value': Max('membershippersonorganization__value__organizationopenended__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('open_ended_sources', {
                'header': Organization.get_spreadsheet_source_field_name('open_ended'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonorganization__value__organizationopenended__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('open_ended_confidence', {
                'header': Organization.get_spreadsheet_confidence_field_name('open_ended'),
                'confidence': True,
                'value': Max('membershippersonorganization__value__organizationopenended__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_id', {
                'header': 'person:admin:id',
                'value': F('membershippersonmember__value__uuid'),
                'serializer': cls.serializers['string'],
            }),
            ('person_id_sources', {
                'header': 'person:posting:source',
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_id_confidence', {
                'header': 'person:posting:confidence',
                'confidence': True,
                'value': Max('membershippersonmember__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_name', {
                'header': Person.get_spreadsheet_field_name('name'),
                'value': Max('membershippersonmember__value__personname__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_name_sources', {
                'header': Person.get_spreadsheet_source_field_name('name'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personname__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_name_confidence', {
                'header': Person.get_spreadsheet_confidence_field_name('name'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personname__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_aliases', {
                'header': Person.get_spreadsheet_field_name('aliases'),
                'value': DistinctArrayAgg('membershippersonmember__value__personalias__value', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_aliases_sources', {
                'header': Person.get_spreadsheet_source_field_name('aliases'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personalias__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_aliases_confidence', {
                'header': Person.get_spreadsheet_confidence_field_name('aliases'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personalias__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_division_id', {
                'header': Person.get_spreadsheet_field_name('division_id'),
                'value': Max('membershippersonmember__value__persondivisionid__value'),
                'serializer': cls.serializers['division_id'],
            }),
            ('person_division_id_sources', {
                'header': Person.get_spreadsheet_source_field_name('division_id'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__persondivisionid__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_division_id_confidence', {
                'header': Person.get_spreadsheet_confidence_field_name('division_id'),
                'confidence': True,
                'value': Max('membershippersonmember__value__persondivisionid__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_date_of_birth', {
                'header': PersonBiography.get_spreadsheet_field_name('date_of_birth'),
                'value': DistinctArrayAgg('membershippersonmember__value__personbiographyperson__object_ref__personbiographydateofbirth', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_date_of_birth_sources', {
                'header': PersonBiography.get_spreadsheet_source_field_name('date_of_birth'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personbiographyperson__object_ref__personbiographydateofbirth__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_date_of_birth_confidence', {
                'header': PersonBiography.get_spreadsheet_confidence_field_name('date_of_birth'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personbiographyperson__object_ref__personbiographydateofbirth__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_date_of_death', {
                'header': PersonBiography.get_spreadsheet_field_name('date_of_death'),
                'value': DistinctArrayAgg('membershippersonmember__value__personbiographyperson__object_ref__personbiographydateofdeath', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_date_of_death_sources', {
                'header': PersonBiography.get_spreadsheet_source_field_name('date_of_death'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personbiographyperson__object_ref__personbiographydateofdeath__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_date_of_death_confidence', {
                'header': PersonBiography.get_spreadsheet_confidence_field_name('date_of_death'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personbiographyperson__object_ref__personbiographydateofdeath__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_deceased', {
                'header': PersonBiography.get_spreadsheet_field_name('deceased'),
                'value': DistinctArrayAgg('membershippersonmember__value__personbiographyperson__object_ref__personbiographydeceased', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_deceased_sources', {
                'header': PersonBiography.get_spreadsheet_source_field_name('deceased'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personbiographyperson__object_ref__personbiographydeceased__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_deceased_confidence', {
                'header': PersonBiography.get_spreadsheet_confidence_field_name('deceased'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personbiographyperson__object_ref__personbiographydeceased__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_account_types', {
                'header': PersonExtra.get_spreadsheet_field_name('account_type'),
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextraaccounttype', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_account_types_sources', {
                'header': PersonExtra.get_spreadsheet_source_field_name('account_type'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextraaccounttype__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_account_types_confidence', {
                'header': PersonExtra.get_spreadsheet_confidence_field_name('account_type'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personextraperson__object_ref__personextraaccounttype__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_accounts', {
                'header': PersonExtra.get_spreadsheet_field_name('account'),
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextraaccount', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_accounts_sources', {
                'header': PersonExtra.get_spreadsheet_source_field_name('account'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextraaccount__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_accounts_confidence', {
                'header': PersonExtra.get_spreadsheet_confidence_field_name('account'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personextraperson__object_ref__personextraaccount__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_external_link_descriptions', {
                'header': PersonExtra.get_spreadsheet_field_name('external_link_description'),
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextraexternallinkdescription', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_external_link_descriptions_sources', {
                'header': PersonExtra.get_spreadsheet_source_field_name('external_link_description'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextraexternallinkdescription__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_external_link_descriptions_confidence', {
                'header': PersonExtra.get_spreadsheet_confidence_field_name('external_link_description'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personextraperson__object_ref__personextraexternallinkdescription__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_media_descriptions', {
                'header': PersonExtra.get_spreadsheet_field_name('media_description'),
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextramediadescription', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_media_descriptions_sources', {
                'header': PersonExtra.get_spreadsheet_source_field_name('media_description'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextramediadescription__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_media_descriptions_confidence', {
                'header': PersonExtra.get_spreadsheet_confidence_field_name('media_description'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personextraperson__object_ref__personextramediadescription__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_notes', {
                'header': PersonExtra.get_spreadsheet_field_name('notes'),
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextranotes', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_notes_sources', {
                'header': PersonExtra.get_spreadsheet_source_field_name('notes'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonmember__value__personextraperson__object_ref__personextranotes__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_notes_confidence', {
                'header': PersonExtra.get_spreadsheet_confidence_field_name('notes'),
                'confidence': True,
                'value': Max('membershippersonmember__value__personextraperson__object_ref__personextranotes__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_role', {
                'header': MembershipPerson.get_spreadsheet_field_name('role'),
                'value': Max('membershippersonrole__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_role_sources', {
                'header': MembershipPerson.get_spreadsheet_source_field_name('role'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonrole__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_role_confidence', {
                'header': MembershipPerson.get_spreadsheet_confidence_field_name('role'),
                'confidence': True,
                'value': Max('membershippersonrole__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_rank', {
                'header': MembershipPerson.get_spreadsheet_field_name('rank'),
                'value': Max('membershippersonrank__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_rank_sources', {
                'header': MembershipPerson.get_spreadsheet_source_field_name('rank'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonrank__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_rank_confidence', {
                'header': MembershipPerson.get_spreadsheet_confidence_field_name('rank'),
                'confidence': True,
                'value': Max('membershippersonrank__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_title', {
                'header': MembershipPerson.get_spreadsheet_field_name('title'),
                'value': Max('membershippersontitle__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_title_sources', {
                'header': MembershipPerson.get_spreadsheet_source_field_name('title'),
                'source': True,
                'value': DistinctArrayAgg('membershippersontitle__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_title_confidence', {
                'header': MembershipPerson.get_spreadsheet_confidence_field_name('title'),
                'confidence': True,
                'value': Max('membershippersontitle__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_firstciteddate', {
                'header': MembershipPerson.get_spreadsheet_field_name('firstciteddate'),
                'value': Max('membershippersonfirstciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_firstciteddate_sources', {
                'header': MembershipPerson.get_spreadsheet_source_field_name('firstciteddate'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonfirstciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_firstciteddate_confidence', {
                'header': MembershipPerson.get_spreadsheet_confidence_field_name('firstciteddate'),
                'confidence': True,
                'value': Max('membershippersonfirstciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_realstart', {
                'header': MembershipPerson.get_spreadsheet_field_name('realstart'),
                'value': Max(
                    Case(
                        When(membershippersonrealstart__value=True, then=Value('Y')),
                        When(membershippersonrealstart__value=False, then=Value('N')),
                        When(membershippersonrealstart__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('person_realstart_sources', {
                'header': MembershipPerson.get_spreadsheet_source_field_name('realstart'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonrealstart__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_realstart_confidence', {
                'header': MembershipPerson.get_spreadsheet_confidence_field_name('realstart'),
                'confidence': True,
                'value': Max('membershippersonrealstart__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_startcontext', {
                'header': MembershipPerson.get_spreadsheet_field_name('startcontext'),
                'value': Max('membershippersonstartcontext__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_startcontext_sources', {
                'header': MembershipPerson.get_spreadsheet_source_field_name('startcontext'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonstartcontext__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_startcontext_confidence', {
                'header': MembershipPerson.get_spreadsheet_confidence_field_name('startcontext'),
                'confidence': True,
                'value': Max('membershippersonstartcontext__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_lastciteddate', {
                'header': MembershipPerson.get_spreadsheet_field_name('lastciteddate'),
                'value': Max('membershippersonlastciteddate__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_lastciteddate_sources', {
                'header': MembershipPerson.get_spreadsheet_source_field_name('lastciteddate'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonlastciteddate__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_lastciteddate_confidence', {
                'header': MembershipPerson.get_spreadsheet_confidence_field_name('lastciteddate'),
                'confidence': True,
                'value': Max('membershippersonlastciteddate__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_realend', {
                'header': MembershipPerson.get_spreadsheet_field_name('realend'),
                'value': Max(
                    Case(
                        When(membershippersonrealend__value=True, then=Value('Y')),
                        When(membershippersonrealend__value=False, then=Value('N')),
                        When(membershippersonrealend__value=None, then=Value('')),
                        output_field=CharField()
                    )
                ),
                'serializer': cls.serializers['identity'],
            }),
            ('person_realend_sources', {
                'header': MembershipPerson.get_spreadsheet_source_field_name('realend'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonrealend__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_realend_confidence', {
                'header': MembershipPerson.get_spreadsheet_confidence_field_name('realend'),
                'confidence': True,
                'value': Max('membershippersonrealend__confidence'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_endcontext', {
                'header': MembershipPerson.get_spreadsheet_field_name('endcontext'),
                'value': Max('membershippersonendcontext__value'),
                'serializer': cls.serializers['identity'],
            }),
            ('person_endcontext_sources', {
                'header': MembershipPerson.get_spreadsheet_source_field_name('endcontext'),
                'source': True,
                'value': DistinctArrayAgg('membershippersonendcontext__sources', distinct=True),
                'serializer': cls.serializers['list'],
            }),
            ('person_endcontext_confidence', {
                'header': MembershipPerson.get_spreadsheet_confidence_field_name('endcontext'),
                'confidence': True,
                'value': Max('membershippersonendcontext__confidence'),
                'serializer': cls.serializers['identity'],
            }),
        ])
