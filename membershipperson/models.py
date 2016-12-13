from django.db import models
from django.utils.translation import ugettext as _
from django.utils.translation import get_language
from django.db.models import Max

from django_date_extensions.fields import ApproximateDateField

from complex_fields.model_decorators import (versioned, translated, sourced,
                                             sourced_optional)
from complex_fields.models import ComplexField, ComplexFieldContainer
from complex_fields.base_models import BaseModel
from person.models import Person
from organization.models import Organization


class MembershipPerson(models.Model, BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.member = ComplexFieldContainer(self, MembershipPersonMember)
        self.organization = ComplexFieldContainer(self, MembershipPersonOrganization)
        self.role = ComplexFieldContainer(self, MembershipPersonRole)
        self.title = ComplexFieldContainer(self, MembershipPersonTitle)
        self.rank = ComplexFieldContainer(self, MembershipPersonRank)
        self.realstart = ComplexFieldContainer(self, MembershipPersonRealStart)
        self.realend = ComplexFieldContainer(self, MembershipPersonRealEnd)
        self.startcontext = ComplexFieldContainer(self, MembershipPersonStartContext)
        self.endcontext = ComplexFieldContainer(self, MembershipPersonEndContext)
        self.firstciteddate = ComplexFieldContainer(self, MembershipPersonFirstCitedDate)
        self.lastciteddate = ComplexFieldContainer(self, MembershipPersonLastCitedDate)

        self.complex_fields = [self.member, self.organization, self.role,
                               self.title, self.rank, self.realstart, self.realend,
                               self.startcontext, self.endcontext,
                               self.firstciteddate, self.lastciteddate]

        self.required_fields = [
            "MembershipPerson_MembershipPersonMember",
            "MembershipPerson_MembershipPersonOrganization",
        ]

    @classmethod
    def from_id(cls, id_):
        try:
            membership = cls.objects.get(id=id_)
            return membership
        except cls.DoesNotExist:
            return None

    def get_value(self):
        return '{0} member of {1}'.format(self.member.get_value(),
                                          self.organization.get_value())

    @classmethod
    def create(cls, dict_values, lang=get_language()):
        membership = cls()
        membership.update(dict_values, lang)
        return membership


@versioned
@sourced
class MembershipPersonMember(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = models.ForeignKey(Person, default=None, blank=True, null=True)
    field_name = _("Member")


@versioned
@sourced
class MembershipPersonOrganization(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = models.ForeignKey(Organization)
    field_name = _("Organization")


@versioned
@sourced
class MembershipPersonRole(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = models.ForeignKey('Role', default=None, blank=True, null=True)
    field_name = _("Role")


@translated
@versioned
@sourced
class MembershipPersonTitle(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Title")


@versioned
@sourced
class MembershipPersonRank(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = models.ForeignKey('Rank', default=None, blank=True, null=True)
    field_name = _("Rank")


@versioned
@sourced
class MembershipPersonFirstCitedDate(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = ApproximateDateField()
    field_name = _("First cited date")


@versioned
@sourced
class MembershipPersonLastCitedDate(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = ApproximateDateField()
    field_name = _("Last cited date")


@versioned
@sourced_optional
class MembershipPersonRealStart(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = models.BooleanField(default=None)
    field_name = _("Real start date")


@versioned
@sourced_optional
class MembershipPersonRealEnd(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = models.BooleanField(default=None)
    field_name = _("Real end date")


@versioned
@sourced
class MembershipPersonStartContext(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = models.ForeignKey('Context')
    field_name = _("Start context")


@versioned
@sourced
class MembershipPersonEndContext(ComplexField):
    object_ref = models.ForeignKey('MembershipPerson')
    value = models.ForeignKey('Context')
    field_name = _("End context")


class Role(models.Model):
    value = models.TextField()

    @classmethod
    def get_role_list(cls):
        roles = cls.objects.all()
        roles = [
            role.value
            for role in roles
        ]

        return roles

    def __str__(self):
        return self.value


class Rank(models.Model):
    value = models.TextField()

    def __str__(self):
        return self.value


class Context(models.Model):
    value = models.TextField()

    def __str__(self):
        return self.value
