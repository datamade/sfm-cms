from django.db import models
from django.utils.translation import ugettext as _
from django.utils.translation import get_language
from django.db.models import Max
from django.conf import settings

from django_date_extensions.fields import ApproximateDateField

from complex_fields.model_decorators import (versioned, sourced, sourced_optional,
                                             translated)
from complex_fields.models import (ComplexField, ComplexFieldContainer,
                                   ComplexFieldListContainer)
from complex_fields.base_models import BaseModel
from organization.models import Organization
from location.models import Location
from sfm_pc.fields import GetComplexFieldNameMixin


class Emplacement(models.Model, BaseModel, GetComplexFieldNameMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.startdate = ComplexFieldContainer(self, EmplacementStartDate)
        self.enddate = ComplexFieldContainer(self, EmplacementEndDate)
        self.realstart = ComplexFieldContainer(self, EmplacementRealStart)
        self.open_ended = ComplexFieldContainer(self, EmplacementOpenEnded)
        self.organization = ComplexFieldContainer(self, EmplacementOrganization)
        self.site = ComplexFieldContainer(self, EmplacementSite)
        self.aliases = ComplexFieldListContainer(self, EmplacementAlias)

        self.complex_fields = [self.startdate, self.enddate, self.organization,
                               self.site, self.open_ended, self.realstart]

        self.complex_lists = [self.aliases]

        self.required_fields = [
            "Emplacement_EmplacementOrganization",
            "Emplacement_EmplacementSite",
        ]

    def get_value(self):
        return '{0} ({1})'.format(self.organization.get_value(),
                                  self.site.get_value())

@versioned
@sourced
class EmplacementStartDate(ComplexField):
    object_ref = models.ForeignKey('Emplacement')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("First Cited Date")
    shortcode = 'u_sfcd'
    spreadsheet_field_name = 'unit:site_first_cited_date'


@versioned
@sourced_optional
class EmplacementRealStart(ComplexField):
    object_ref = models.ForeignKey('Emplacement')
    value = models.NullBooleanField(default=None, blank=True, null=True)
    field_name = _("Is Foundation Date?")
    shortcode = 'u_sfcdf'
    spreadsheet_field_name = 'unit:site_first_cited_date_founding'


@versioned
@sourced
class EmplacementEndDate(ComplexField):
    object_ref = models.ForeignKey('Emplacement')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Last Cited Date")
    shortcode = 'u_slcd'
    spreadsheet_field_name = 'unit:site_last_cited_date'


@versioned
@sourced_optional
class EmplacementOpenEnded(ComplexField):
    object_ref = models.ForeignKey('Emplacement')
    value = models.CharField(default='N', max_length=1, choices=settings.OPEN_ENDED_CHOICES)
    field_name = _("Is Open Ended?")
    shortcode = 'u_slcdo'
    spreadsheet_field_name = 'unit:site_open'


@versioned
@sourced
class EmplacementOrganization(ComplexField):
    object_ref = models.ForeignKey('Emplacement')
    value = models.ForeignKey(Organization)
    field_name = _("Unit")


@versioned
@sourced
class EmplacementSite(ComplexField):
    object_ref = models.ForeignKey('Emplacement')
    value = models.ForeignKey(Location)
    field_name = _("Site")


@translated
@versioned
@sourced
class EmplacementAlias(ComplexField):
    object_ref = models.ForeignKey('Emplacement')
    value = models.TextField(blank=True, null=True)
    field_name = _("Alias")
