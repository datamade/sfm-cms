import uuid

import reversion

from django.contrib.gis.db import models
from django.utils.translation import ugettext as _
from django.db.models import Max
from django.contrib.gis import geos

from django_date_extensions.fields import ApproximateDateField

from complex_fields.model_decorators import versioned, translated, sourced, sourced_optional
from complex_fields.models import ComplexField, ComplexFieldContainer, ComplexFieldListContainer
from complex_fields.base_models import BaseModel
from source.models import Source
from person.models import Person
from organization.models import Organization
from geosite.models import Geosite
from sfm_pc.utils import VersionsMixin

VERSION_RELATED_FIELDS = [
    'violationadminlevel1_set',
    'violationadminlevel2_set',
    'violationdescription_set',
    'violationdivisionid_set',
    'violationenddate_set',
    'violationfirstallegation_set',
    'violationlastupdate_set',
    'violationlocation_set',
    'violationlocationdescription_set',
    'violationlocationid_set',
    'violationlocationname_set',
    'violationosmid_set',
    'violationosmname_set',
    'violationperpetrator_set',
    'violationperpetratorclassification_set',
    'violationperpetratororganization_set',
    'violationstartdate_set',
    'violationstatus_set',
    'violationtype_set'
]


@reversion.register(follow=VERSION_RELATED_FIELDS)
class Violation(models.Model, BaseModel, VersionsMixin):
    uuid = models.UUIDField(default=uuid.uuid4,
                            editable=False,
                            db_index=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dates and status
        self.startdate = ComplexFieldContainer(self, ViolationStartDate)
        self.first_allegation = ComplexFieldContainer(self, ViolationFirstAllegation)
        self.enddate = ComplexFieldContainer(self, ViolationEndDate)
        self.last_update = ComplexFieldContainer(self, ViolationLastUpdate)
        self.status = ComplexFieldContainer(self, ViolationStatus)

        # Location fields
        self.locationdescription = ComplexFieldContainer(
            self, ViolationLocationDescription
        )
        self.adminlevel1 = ComplexFieldContainer(self, ViolationAdminLevel1)
        self.adminlevel2 = ComplexFieldContainer(self, ViolationAdminLevel2)
        self.osmname = ComplexFieldContainer(self, ViolationOSMName)
        self.osmid = ComplexFieldContainer(self, ViolationOSMId)
        self.division_id = ComplexFieldContainer(self, ViolationDivisionId)
        self.location = ComplexFieldContainer(self, ViolationLocation)
        self.location_name = ComplexFieldContainer(self, ViolationLocationName)
        self.location_id = ComplexFieldContainer(self, ViolationLocationId)

        # Descriptions and other attributes
        self.description = ComplexFieldContainer(self, ViolationDescription)
        self.perpetrator = ComplexFieldListContainer(self, ViolationPerpetrator)
        self.perpetratororganization = ComplexFieldListContainer(
            self, ViolationPerpetratorOrganization
        )
        self.perpetratorclassification = ComplexFieldContainer(
            self, ViolationPerpetratorClassification
        )
        self.types = ComplexFieldListContainer(self, ViolationType)

        self.complex_fields = [self.startdate, self.first_allegation,
                               self.enddate, self.last_update, self.status,
                               self.locationdescription, self.location,
                               self.description, self.division_id]

        self.complex_lists = [self.perpetrator, self.perpetratororganization, self.types]

        self.required_fields = [self.description, self.startdate, self.enddate]


    def get_value(self):
        return self.description.get_value()


@versioned
@sourced
class ViolationStartDate(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Start date")


@versioned
@sourced
class ViolationFirstAllegation(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("First allegation")


@versioned
@sourced
class ViolationEndDate(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("End date")


@versioned
@sourced
class ViolationLastUpdate(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Last update")


@translated
@versioned
@sourced
class ViolationStatus(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Current status")


@translated
@versioned
@sourced
class ViolationLocationDescription(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Location description")


@versioned
@sourced
class ViolationAdminLevel1(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Admin level 1")


@versioned
@sourced
class ViolationAdminLevel2(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Admin level 2")


@versioned
@sourced
class ViolationOSMName(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("OSM Name")


@versioned
@sourced
class ViolationOSMId(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("OSM ID")


@versioned
@sourced
class ViolationDivisionId(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Division ID")


@versioned
@sourced
class ViolationLocation(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.PointField(default=None, blank=True, null=True)
    objects = models.GeoManager()
    field_name = _("Location")


@versioned
@sourced
class ViolationLocationName(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Exact location name")


@versioned
@sourced
class ViolationLocationId(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Exact location ID")


@versioned
@sourced
class ViolationDescription(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Description")


@versioned
@sourced
class ViolationPerpetrator(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.ForeignKey(Person, default=None, blank=True, null=True)
    field_name = _("Perpetrator")


@versioned
@sourced
class ViolationPerpetratorOrganization(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.ForeignKey(Organization, default=None, blank=True, null=True)
    field_name = _("Perpetrating unit")


@versioned
@sourced
@translated
class ViolationType(ComplexField):
    object_ref = models.ForeignKey('Violation', null=True)
    value = models.TextField(blank=True, null=True)
    field_name = _("Violation type")


@versioned
@sourced
@translated
class ViolationPerpetratorClassification(ComplexField):
    object_ref = models.ForeignKey('Violation', null=True)
    value = models.TextField(blank=True, null=True)
    field_name = _("Perpetrating unit classification")
