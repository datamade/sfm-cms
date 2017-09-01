import uuid

from django.db import models
from django.utils.translation import ugettext as _
from django.conf import settings

from complex_fields.model_decorators import (versioned, translated, sourced,
                                             sourced_optional)
from complex_fields.models import ComplexField, ComplexFieldContainer, ComplexFieldListContainer
from complex_fields.base_models import BaseModel
from django_date_extensions.fields import ApproximateDateField


class Organization(models.Model, BaseModel):

    uuid = models.UUIDField(default=uuid.uuid4,
                            editable=False,
                            db_index=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = ComplexFieldContainer(self, OrganizationName)
        self.aliases = ComplexFieldListContainer(self, OrganizationAlias)
        self.classification = ComplexFieldListContainer(self, OrganizationClassification)
        self.division_id = ComplexFieldContainer(self, OrganizationDivisionId)
        self.firstciteddate = ComplexFieldContainer(self, OrganizationFirstCitedDate)
        self.lastciteddate = ComplexFieldContainer(self, OrganizationLastCitedDate)
        self.realstart = ComplexFieldContainer(self, OrganizationRealStart)
        self.open_ended = ComplexFieldContainer(self, OrganizationOpenEnded)

        self.complex_fields = [self.name, self.division_id, self.firstciteddate,
                               self.lastciteddate, self.realstart, self.open_ended]

        self.required_fields = [
            "Organization_OrganizationName",
        ]

    def get_value(self):
        return self.name.get_value()

    def __str__(self):
        return str(self.name)


@translated
@versioned
@sourced
class OrganizationName(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Name")


@translated
@versioned
@sourced
class OrganizationAlias(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.ForeignKey('Alias', default=None, blank=True, null=True)

    field_name = _("Alias")


class Alias(models.Model):
    value = models.TextField()

    def __str__(self):
        return self.value


@versioned
@sourced
class OrganizationClassification(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.ForeignKey('Classification', default=None, blank=True,
                              null=True)
    field_name = _("Classification")


class Classification(models.Model):
    value = models.TextField()

    def __str__(self):
        return self.value


@versioned
@sourced
class OrganizationDivisionId(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.TextField(default=None, blank=True, null=True)

    field_name = _("Division ID")

    def __str__(self):
        return self.value


@versioned
@sourced
class OrganizationFirstCitedDate(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = ApproximateDateField()
    field_name = _("First cited date")


@versioned
@sourced
class OrganizationLastCitedDate(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = ApproximateDateField()
    field_name = _("Last cited date")


@versioned
@sourced_optional
class OrganizationRealStart(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.NullBooleanField(default=None)
    field_name = _("Real start date")


@versioned
@sourced_optional
class OrganizationOpenEnded(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.CharField(default='N', max_length=1, choices=settings.OPEN_ENDED_CHOICES)
    field_name = _("Open ended")
