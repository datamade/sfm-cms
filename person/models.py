import uuid

import reversion

from django.db import models
from django.db.models.functions import Coalesce
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.utils.functional import cached_property
from django.template.defaultfilters import truncatewords

from complex_fields.model_decorators import versioned, translated, sourced
from complex_fields.models import ComplexField, ComplexFieldContainer, \
    ComplexFieldListContainer
from complex_fields.base_models import BaseModel

from sfm_pc.utils import VersionsMixin
from sfm_pc.fields import GetComplexFieldNameMixin


VERSION_RELATED_FIELDS = [
    'personname_set',
    'personalias_set',
    'persondivisionid_set',
    'personnotes_set',
    'membershippersonmember_set',
    'violationperpetrator_set',
    'personextraperson_set',
    'personbiographyperson_set'
]


@reversion.register(follow=VERSION_RELATED_FIELDS)
class Person(models.Model, BaseModel, VersionsMixin, GetComplexFieldNameMixin):

    uuid = models.UUIDField(default=uuid.uuid4,
                            editable=False,
                            db_index=True)

    published = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        self.name = ComplexFieldContainer(self, PersonName)
        self.aliases = ComplexFieldListContainer(self, PersonAlias)
        self.division_id = ComplexFieldContainer(self, PersonDivisionId)
        self.notes = ComplexFieldContainer(self, PersonNotes)

        self.complex_fields = [
            self.name,
            self.division_id,
            self.notes,
        ]
        self.complex_lists = [self.aliases]

        self.required_fields = [
            "Person_PersonName",
        ]

        super().__init__(*args, **kwargs)

    def get_value(self):
        return self.name.get_value()

    def __str__(self):
        try:
            return str(self.personname_set.first().value)
        except AttributeError:
            return str(self.uuid)

    def get_absolute_url(self):
        return reverse('view-person', kwargs={'slug': self.uuid})

    @cached_property
    def memberships(self):
        '''
        Return all of this person's memberships, in a custom sorting order.

        Order by first cited date descending, then last cited date descending,
        with nulls last.
        '''
        mems = self.membershippersonmember_set\
                   .select_related('object_ref')\
                   .annotate(lcd=Coalesce('object_ref__membershippersonfirstciteddate__value',
                                          'object_ref__membershippersonlastciteddate__value',
                                          models.Value('1000-0-0')))\
                   .order_by('-lcd')

        return mems

    @property
    def last_cited(self):
        '''
        Get the global last citation date for this person, leaving out nulls.
        '''
        order = '-object_ref__membershippersonlastciteddate__value'
        memberships = self.membershippersonmember_set.order_by(order)
        for membership in memberships:
            # Filter nulls
            lcd = membership.object_ref.lastciteddate.get_value()
            if lcd:
                return lcd

    @property
    def first_cited(self):
        '''
        Get the global first citation date for this person, leaving out nulls.
        '''
        order = 'object_ref__membershippersonfirstciteddate__value'
        memberships = self.membershippersonmember_set.order_by(order)
        for membership in memberships:
            fcd = membership.object_ref.firstciteddate.get_value()
            if fcd:
                return fcd

    @property
    def related_entities(self):
        """
        Return a list of dicts with metadata for all of the entities linked to
        this Person.

        Metadata dicts must have the following keys:
            - name
            - entity_type
            - start_date
            - end_date
            - open_ended
            - url (a link to edit the entity)
        """
        related_entities = []

        # This person's postings.
        for membershippersonmember in self.membershippersonmember_set.all():
            membership = membershippersonmember.object_ref
            organization = membership.organization.get_value().value
            related_entities.append({
                'name': organization.name.get_value().value,
                'entity_type': _('MembershipPerson'),
                'start_date': membership.firstciteddate.get_value(),
                'end_date': membership.lastciteddate.get_value(),
                'open_ended': membership.realend.get_value(),
                'url': reverse(
                    'edit-person-postings',
                    kwargs={
                        'person_id': self.uuid,
                        'pk': membership.pk
                    }
                ),
            })

        # Incidents where this person was a perpetrator.
        for violationperpetrator in self.violationperpetrator_set.all():
            violation = violationperpetrator.object_ref
            related_entities.append({
                'name': truncatewords(violation.description.get_value(), 10),
                'entity_type': _('Violation'),
                'start_date': violation.startdate.get_value(),
                'end_date': violation.enddate.get_value(),
                'open_ended': '',
                'url': reverse('edit-violation', kwargs={'slug': violation.uuid}),
            })

        return related_entities


@translated
@versioned
@sourced
class PersonName(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Name")
    shortcode = 'p_n'
    spreadsheet_field_name = 'person:name'


@translated
@versioned
@sourced
class PersonAlias(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Other Names")
    shortcode = 'p_on'
    spreadsheet_field_name = 'person:other_names'


@translated
@versioned
@sourced
class PersonNotes(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Notes")
    shortcode = 'p_n_a'
    spreadsheet_field_name = 'person:notes:admin'


@sourced
@versioned
class PersonDivisionId(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _('Country')
    shortcode = 'p_c'
    spreadsheet_field_name = 'person:country'
