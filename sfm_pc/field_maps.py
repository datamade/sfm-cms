# field_maps.py: Config dicts for exporting spreadsheets
from collections import OrderedDict

from django.db.models import Max, Case, When, Value, CharField, F
from django.contrib.postgres.aggregates import ArrayAgg

from organization.models import Organization
from composition.models import Composition


class DistinctArrayAgg(ArrayAgg):
    # Allow ArrayAgg queries to optionally filter duplicate values.
    # This change was introduced in Django 2.0, which we are not yet supporting.
    # See: https://github.com/django/django/commit/b5393028bfc939adf14d0fa5e4088cddd3b9dfa1
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, **extra):
        super().__init__(expression, distinct='DISTINCT ' if distinct else '', **extra)


# Serializer functions for use in exporting spreadsheet columns
serializers = {
    'string': lambda x: str(x),
    'identity': lambda x: x,
    'division_id': lambda x: x.split(':')[-1] if x else x,
    'list': lambda x: '; '.join(str(elem) for elem in x if elem),
}

# Basic download field map
basic = OrderedDict([
    ('org_uuid', {
        'header': 'unit:id:admin',
        'value': F('uuid'),
        'serializer': serializers['string'],
    }),
    ('name', {
        'header': Organization.get_spreadsheet_field_name('name'),
        'value': Max('organizationname__value'),
        'serializer': serializers['identity'],
    }),
    ('name_sources', {
        'header': Organization.get_spreadsheet_source_field_name('name'),
        'source': True,
        'value': DistinctArrayAgg('organizationname__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('name_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('name'),
        'confidence': True,
        'value': Max('organizationname__confidence'),
        'serializer': serializers['identity'],
    }),
    ('division_id', {
        'header': Organization.get_spreadsheet_field_name('division_id'),
        'value': Max('organizationdivisionid__value'),
        'serializer': serializers['division_id'],
    }),
    ('division_id_sources', {
        'header': Organization.get_spreadsheet_source_field_name('division_id'),
        'source': True,
        'value': DistinctArrayAgg('organizationdivisionid__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('division_id_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('division_id'),
        'confidence': True,
        'value': Max('organizationdivisionid__confidence'),
        'serializer': serializers['identity'],
    }),
    ('classifications', {
        'header': Organization.get_spreadsheet_field_name('classification'),
        'value': DistinctArrayAgg('organizationclassification__value', distinct=True),
        'serializer': serializers['list'],
    }),
    ('classifications_sources', {
        'header': Organization.get_spreadsheet_source_field_name('classification'),
        'source': True,
        'value': DistinctArrayAgg('organizationclassification__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('classifications_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('classification'),
        'confidence': True,
        'value': Max('organizationclassification__confidence'),
        'serializer': serializers['identity'],
    }),
    ('aliases', {
        'header': Organization.get_spreadsheet_field_name('aliases'),
        'value': DistinctArrayAgg('organizationalias__value', distinct=True),
        'serializer': serializers['list'],
    }),
    ('aliases_sources', {
        'header': Organization.get_spreadsheet_source_field_name('aliases'),
        'source': True,
        'value': DistinctArrayAgg('organizationalias__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('aliases_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('aliases'),
        'confidence': True,
        'value': Max('organizationalias__confidence'),
        'serializer': serializers['identity'],
    }),
    ('firstciteddate', {
        'header': Organization.get_spreadsheet_field_name('firstciteddate'),
        'value': Max('organizationfirstciteddate__value'),
        'serializer': serializers['identity'],
    }),
    ('firstciteddate_sources', {
        'header': Organization.get_spreadsheet_source_field_name('firstciteddate'),
        'source': True,
        'value': DistinctArrayAgg('organizationfirstciteddate__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('firstciteddate_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
        'confidence': True,
        'value': Max('organizationfirstciteddate__confidence'),
        'serializer': serializers['identity'],
    }),
    ('lastciteddate', {
        'header': Organization.get_spreadsheet_field_name('lastciteddate'),
        'value': Max('organizationlastciteddate__value'),
        'serializer': serializers['identity'],
    }),
    ('lastciteddate_sources', {
        'header': Organization.get_spreadsheet_source_field_name('lastciteddate'),
        'source': True,
        'value': DistinctArrayAgg('organizationlastciteddate__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('lastciteddate_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
        'confidence': True,
        'value': Max('organizationlastciteddate__confidence'),
        'serializer': serializers['identity'],
    }),
    ('realstart', {
        'header': Organization.get_spreadsheet_field_name('realstart'),
        'value': Max(
            Case(
                When(organizationrealstart__value=True, then=Value('Y')),
                When(organizationrealstart__value=False, then=Value('N')),
                When(organizationrealstart__value=None, then=Value('')),
                output_field=CharField()
            )
        ),
        'serializer': serializers['identity'],
    }),
    ('realstart_sources', {
        'header': Organization.get_spreadsheet_source_field_name('realstart'),
        'source': True,
        'value': DistinctArrayAgg('organizationrealstart__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('realstart_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('realstart'),
        'confidence': True,
        'value': Max('organizationrealstart__confidence'),
        'serializer': serializers['identity'],
    }),
    ('openended', {
        'header': Organization.get_spreadsheet_field_name('open_ended'),
        'value': Max('organizationopenended__value'),
        'serializer': serializers['identity'],
    }),
    ('openended_sources', {
        'header': Organization.get_spreadsheet_source_field_name('open_ended'),
        'source': True,
        'value': DistinctArrayAgg('organizationopenended__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('openended_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('open_ended'),
        'confidence': True,
        'value': Max('organizationopenended__confidence'),
        'serializer': serializers['identity'],
    }),
])

# Parentage field map
parentage = OrderedDict([
    ('child_uuid', {
        'header': 'unit:id:admin',
        'value': F('compositionchild__value__uuid'),
        'serializer': serializers['string'],
    }),
    ('name', {
        'header': Organization.get_spreadsheet_field_name('name'),
        'value': Max('compositionchild__value__organizationname__value'),
        'serializer': serializers['identity'],
    }),
    ('name_sources', {
        'header': Organization.get_spreadsheet_source_field_name('name'),
        'source': True,
        'value': DistinctArrayAgg('compositionchild__value__organizationname__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('name_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('name'),
        'confidence': True,
        'value': Max('compositionchild__value__organizationname__confidence'),
        'serializer': serializers['identity'],
    }),
    ('division_id', {
        'header': Organization.get_spreadsheet_field_name('division_id'),
        'value': Max('compositionchild__value__organizationdivisionid__value'),
        'serializer': serializers['division_id'],
    }),
    ('division_id_sources', {
        'header': Organization.get_spreadsheet_source_field_name('division_id'),
        'source': True,
        'value': DistinctArrayAgg('compositionchild__value__organizationdivisionid__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('division_id_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('division_id'),
        'confidence': True,
        'value': Max('compositionchild__value__organizationdivisionid__confidence'),
        'serializer': serializers['identity'],
    }),
    ('classifications', {
        'header': Organization.get_spreadsheet_field_name('classification'),
        'value': DistinctArrayAgg('compositionchild__value__organizationclassification__value', distinct=True),
        'serializer': serializers['list'],
    }),
    ('classifications_sources', {
        'header': Organization.get_spreadsheet_source_field_name('classification'),
        'source': True,
        'value': DistinctArrayAgg('compositionchild__value__organizationclassification__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('classifications_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('classification'),
        'confidence': True,
        'value': Max('compositionchild__value__organizationclassification__confidence'),
        'serializer': serializers['identity'],
    }),
    ('aliases', {
        'header': Organization.get_spreadsheet_field_name('aliases'),
        'value': DistinctArrayAgg('compositionchild__value__organizationalias__value', distinct=True),
        'serializer': serializers['list'],
    }),
    ('aliases_sources', {
        'header': Organization.get_spreadsheet_source_field_name('aliases'),
        'source': True,
        'value': DistinctArrayAgg('compositionchild__value__organizationalias__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('aliases_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('aliases'),
        'confidence': True,
        'value': Max('compositionchild__value__organizationalias__confidence'),
        'serializer': serializers['identity'],
    }),
    ('firstciteddate', {
        'header': Organization.get_spreadsheet_field_name('firstciteddate'),
        'value': Max('compositionchild__value__organizationfirstciteddate__value'),
        'serializer': serializers['identity'],
    }),
    ('firstciteddate_sources', {
        'header': Organization.get_spreadsheet_source_field_name('firstciteddate'),
        'source': True,
        'value': DistinctArrayAgg('compositionchild__value__organizationfirstciteddate__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('firstciteddate_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('firstciteddate'),
        'confidence': True,
        'value': Max('compositionchild__value__organizationfirstciteddate__confidence'),
        'serializer': serializers['identity'],
    }),
    ('lastciteddate', {
        'header': Organization.get_spreadsheet_field_name('lastciteddate'),
        'value': Max('compositionchild__value__organizationlastciteddate__value'),
        'serializer': serializers['identity'],
    }),
    ('lastciteddate_sources', {
        'header': Organization.get_spreadsheet_source_field_name('lastciteddate'),
        'source': True,
        'value': DistinctArrayAgg('compositionchild__value__organizationlastciteddate__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('lastciteddate_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('lastciteddate'),
        'confidence': True,
        'value': Max('compositionchild__value__organizationlastciteddate__confidence'),
        'serializer': serializers['identity'],
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
        'serializer': serializers['identity'],
    }),
    ('realstart_sources', {
        'header': Organization.get_spreadsheet_source_field_name('realstart'),
        'source': True,
        'value': DistinctArrayAgg('compositionchild__value__organizationrealstart__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('realstart_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('realstart'),
        'confidence': True,
        'value': Max('compositionchild__value__organizationrealstart__confidence'),
        'serializer': serializers['identity'],
    }),
    ('openended', {
        'header': Organization.get_spreadsheet_field_name('open_ended'),
        'value': Max('compositionchild__value__organizationopenended__value'),
        'serializer': serializers['identity'],
    }),
    ('openended_sources', {
        'header': Organization.get_spreadsheet_source_field_name('open_ended'),
        'source': True,
        'value': DistinctArrayAgg('compositionchild__value__organizationopenended__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('openended_confidence', {
        'header': Organization.get_spreadsheet_confidence_field_name('open_ended'),
        'confidence': True,
        'value': Max('compositionchild__value__organizationopenended__confidence'),
        'serializer': serializers['identity'],
    }),
    ('related_uuid', {
        'header': Composition.get_spreadsheet_field_name('parent'),
        'value': F('compositionparent__value__uuid'),
        'serializer': serializers['string'],
    }),
    ('related_uuid_sources', {
        'header': Composition.get_spreadsheet_source_field_name('parent'),
        'source': True,
        'value': DistinctArrayAgg('compositionparent__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('related_uuid_confidence', {
        'header': Composition.get_spreadsheet_confidence_field_name('parent'),
        'confidence': True,
        'value': Max('compositionparent__confidence'),
        'serializer': serializers['identity'],
    }),
    ('related_name', {
        'header': Composition.get_spreadsheet_field_name('parent') + ':name',
        'value': Max('compositionparent__value__organizationname__value'),
        'serializer': serializers['identity'],
    }),
    ('related_name_sources', {
        'header': Composition.get_spreadsheet_field_name('parent') + ':name:source',
        'source': True,
        'value': DistinctArrayAgg('compositionparent__value__organizationname__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('related_name_confidence', {
        'header': Composition.get_spreadsheet_field_name('parent') + ':name:confidence',
        'confidence': True,
        'value': Max('compositionparent__value__organizationname__confidence'),
        'serializer': serializers['identity'],
    }),
    ('related_division_id', {
        'header': Composition.get_spreadsheet_field_name('parent') + ':country',
        'value': Max('compositionparent__value__organizationdivisionid__value'),
        'serializer': serializers['division_id'],
    }),
    ('related_division_id_sources', {
        'header': Composition.get_spreadsheet_field_name('parent') + ':country:sources',
        'source': True,
        'value': DistinctArrayAgg('compositionparent__value__organizationdivisionid__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('related_division_id_confidence', {
        'header': Composition.get_spreadsheet_field_name('parent') + ':country:confidence',
        'confidence': True,
        'value': Max('compositionparent__value__organizationdivisionid__confidence'),
        'serializer': serializers['identity'],
    }),
    ('related_classifications', {
        'header': Composition.get_spreadsheet_field_name('classification'),
        'value': DistinctArrayAgg('compositionclassification__value', distinct=True),
        'serializer': serializers['list'],
    }),
    ('related_classifications_sources', {
        'header': Composition.get_spreadsheet_source_field_name('classification'),
        'source': True,
        'value': DistinctArrayAgg('compositionclassification__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('related_classifications_confidence', {
        'header': Composition.get_spreadsheet_confidence_field_name('classification'),
        'confidence': True,
        'value': Max('compositionclassification__confidence'),
        'serializer': serializers['identity'],
    }),
    ('related_firstciteddate', {
        'header': Composition.get_spreadsheet_field_name('startdate'),
        'value': Max('compositionstartdate__value'),
        'serializer': serializers['identity'],
    }),
    ('related_firstciteddate_sources', {
        'header': Composition.get_spreadsheet_source_field_name('startdate'),
        'source': True,
        'value': DistinctArrayAgg('compositionstartdate__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('related_firstciteddate_confidence', {
        'header': Composition.get_spreadsheet_confidence_field_name('startdate'),
        'confidence': True,
        'value': Max('compositionstartdate__confidence'),
        'serializer': serializers['identity'],
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
        'serializer': serializers['identity'],
    }),
    ('related_realstart_sources', {
        'header': Composition.get_spreadsheet_source_field_name('realstart'),
        'source': True,
        'value': DistinctArrayAgg('compositionrealstart__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('related_realstart_confidence', {
        'header': Composition.get_spreadsheet_confidence_field_name('realstart'),
        'confidence': True,
        'value': Max('compositionrealstart__confidence'),
        'serializer': serializers['identity'],
    }),
    ('related_lastciteddate', {
        'header': Composition.get_spreadsheet_field_name('enddate'),
        'value': Max('compositionenddate__value'),
        'serializer': serializers['identity'],
    }),
    ('related_lastciteddate_sources', {
        'header': Composition.get_spreadsheet_source_field_name('enddate'),
        'source': True,
        'value': DistinctArrayAgg('compositionenddate__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('related_lastciteddate_confidence', {
        'header': Composition.get_spreadsheet_confidence_field_name('enddate'),
        'confidence': True,
        'value': Max('compositionenddate__confidence'),
        'serializer': serializers['identity'],
    }),
    ('related_openended', {
        'header': Composition.get_spreadsheet_field_name('open_ended'),
        'value': Max('compositionopenended__value'),
        'serializer': serializers['identity'],
    }),
    ('related_openended_sources', {
        'header': Composition.get_spreadsheet_source_field_name('open_ended'),
        'source': True,
        'value': DistinctArrayAgg('compositionopenended__sources', distinct=True),
        'serializer': serializers['list'],
    }),
    ('related_openended_confidence', {
        'header': Composition.get_spreadsheet_confidence_field_name('open_ended'),
        'confidence': True,
        'value': Max('compositionopenended__confidence'),
        'serializer': serializers['identity'],
    }),
])
