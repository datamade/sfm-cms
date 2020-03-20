from django.contrib.gis.db import models
from django.utils.translation import ugettext as _

from django_date_extensions.fields import ApproximateDateField

from complex_fields.model_decorators import (versioned, translated, sourced,
                                             sourced_optional)
from complex_fields.models import ComplexField, ComplexFieldContainer
from complex_fields.base_models import BaseModel

from sfm_pc.fields import GetComplexFieldNameMixin


class Area(models.Model, BaseModel, GetComplexFieldNameMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = ComplexFieldContainer(self, AreaName)
        self.code = ComplexFieldContainer(self, AreaCode)
        self.osmname = ComplexFieldContainer(self, AreaOSMName)
        self.osmid = ComplexFieldContainer(self, AreaOSMId)
        self.geometry = ComplexFieldContainer(self, AreaGeometry)
        self.division_id = ComplexFieldContainer(self, AreaDivisionId)

        self.complex_fields = [self.name, self.code, self.osmname,
                               self.geometry, self.division_id, self.osmid]

        self.complex_lists = []

        self.required_fields = [
            "Area_AreaName",
        ]

    def get_value(self):
        return self.name.get_value()

    def __str__(self):
        return str(self.name)

    @classmethod
    def from_id(cls, id_):
        try:
            area = cls.objects.get(id=id_)
            return area
        except cls.DoesNotExist:
            return None


@translated
@versioned
@sourced
class AreaName(ComplexField):
    object_ref = models.ForeignKey('Area')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Area of Operations")
    shortcode = 'u_an'
    spreadsheet_field_name = 'unit:area_ops_name'


@versioned
@sourced_optional
class AreaGeometry(ComplexField):
    object_ref = models.ForeignKey('Area')
    value = models.MultiPolygonField(default=None, blank=True, null=True)
    objects = models.GeoManager()
    field_name = _("Location geometry")


@versioned
@sourced
class AreaCode(ComplexField):
    object_ref = models.ForeignKey('Area')
    value = models.ForeignKey('Code', default=None, blank=True, null=True)
    field_name = _("Classification")


@versioned
@sourced
class AreaOSMName(ComplexField):
    object_ref = models.ForeignKey('Area')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("OSM name")

    def __str__(self):
        return self.value


@versioned
@sourced
class AreaOSMId(ComplexField):
    object_ref = models.ForeignKey('Area')
    value = models.BigIntegerField(default=None, blank=True, null=True)
    field_name = _("OSM ID")


class Code(models.Model):
    value = models.TextField()

    @classmethod
    def from_id(cls, id_):
        try:
            code = cls.objects.get(id=id_)
            return code
        except cls.DoesNotExist:
            return None

    def __str__(self):
        return self.value


@versioned
@sourced
class AreaDivisionId(ComplexField):
    object_ref = models.ForeignKey('Area')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Country")
    shortcode = 'u_ac'
    spreadsheet_field_name = 'unit:area_ops_country'
