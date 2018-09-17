import uuid

import reversion

from django.db import models, connection
from django.db.models.functions import Coalesce
from django.contrib.gis.geos import Point
from django.utils.translation import ugettext as _
from django.db.models import Max
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.utils.functional import cached_property

from django_date_extensions.fields import ApproximateDateField

from complex_fields.model_decorators import versioned, translated, sourced
from complex_fields.models import ComplexField, ComplexFieldContainer, \
    ComplexFieldListContainer
from complex_fields.base_models import BaseModel

from sfm_pc.utils import VersionsMixin


VERSION_RELATED_FIELDS = [
    'personname_set',
    'personalias_set',
    'persondivisionid_set',
    'membershippersonmember_set',
    'violationperpetrator_set',
]


@reversion.register(follow=VERSION_RELATED_FIELDS)
class Person(models.Model, BaseModel, VersionsMixin):

    uuid = models.UUIDField(default=uuid.uuid4,
                            editable=False,
                            db_index=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = ComplexFieldContainer(self, PersonName)
        self.aliases = ComplexFieldListContainer(self, PersonAlias)
        self.division_id = ComplexFieldContainer(self, PersonDivisionId)
        self.gender = ComplexFieldContainer(self, PersonGender)
        self.date_of_birth = ComplexFieldContainer(self, PersonDateOfBirth)
        self.date_of_death = ComplexFieldContainer(self, PersonDateOfDeath)
        self.deceased = ComplexFieldContainer(self, PersonDeceased)
        self.biography = ComplexFieldContainer(self, PersonBiography)
        self.notes = ComplexFieldContainer(self, PersonNotes)
        self.external_links = ComplexFieldListContainer(self, PersonExternalLink)

        self.complex_fields = [
            self.name,
            self.division_id,
            self.gender,
            self.date_of_birth,
            self.date_of_death,
            self.deceased,
            self.biography,
            self.notes,
        ]
        self.complex_lists = [self.aliases, self.external_links]

        self.required_fields = [
            "Person_PersonName",
        ]

    def get_value(self):
        return self.name.get_value()

    def __str__(self):
        return str(self.name)

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


@translated
@versioned
@sourced
class PersonName(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Name")


@translated
@versioned
@sourced
class PersonAlias(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Alias")


@translated
@versioned
@sourced
class PersonGender(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Gender")


@versioned
@sourced
class PersonDateOfBirth(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Date of birth")


@versioned
@sourced
class PersonDateOfDeath(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Date of death")


@versioned
@sourced
class PersonDeceased(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.BooleanField(default=False)
    field_name = _("Deceased")


@translated
@versioned
@sourced
class PersonBiography(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Biography")


@translated
@versioned
@sourced
class PersonNotes(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Notes")


@sourced
@versioned
class PersonDivisionId(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _('Division ID')


@translated
@versioned
@sourced
class PersonExternalLink(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Notes")
