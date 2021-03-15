#from django.contrib.gis.db import models
#
#from django_date_extensions.fields import ApproximateDateField
#
#from django.utils.translation import ugettext as _
#
#from complex_fields.model_decorators import versioned, translated, sourced
#from complex_fields.models import ComplexField, ComplexFieldContainer
#from complex_fields.base_models import BaseModel
#
#
#class Geosite(models.Model, BaseModel):
#    def __init__(self, *args, **kwargs):
#        super().__init__(*args, **kwargs)
#        self.name = ComplexFieldContainer(self, GeositeName)
#
#        # OSM Name/ID of the smallest containing administrative unit
#        self.admin_name = ComplexFieldContainer(self, GeositeAdminName)
#        self.admin_id = ComplexFieldContainer(self, GeositeAdminId)
#
#        # Larger administrative units (name only)
#        self.adminlevel1 = ComplexFieldContainer(self, GeositeAdminLevel1)
#        self.adminlevel2 = ComplexFieldContainer(self, GeositeAdminLevel2)
#
#        # Coordinates and OSM Name/ID of the exact location
#        self.coordinates = ComplexFieldContainer(self, GeositeCoordinates)
#        self.location_name = ComplexFieldContainer(self, GeositeLocationName)
#        self.location_id = ComplexFieldContainer(self, GeositeLocationId)
#
#        self.division_id = ComplexFieldContainer(self, GeositeDivisionId)
#
#        self.complex_fields = [self.name, self.admin_name, self.admin_id,
#                               self.adminlevel1, self.adminlevel2,
#                               self.coordinates, self.location_name,
#                               self.location_id, self.division_id]
#
#        self.complex_lists = []
#
#        self.required_fields = ["Geosite_GeositeName"]
#
#    def get_value(self):
#        return self.name.get_value()
#
#    def __str__(self):
#        return str(self.name)
#
#
#@translated
#@versioned
#@sourced
#class GeositeName(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = models.TextField(default=None, blank=True, null=True)
#    field_name = _("Name")
#
#    def __str__(self):
#        return self.value
#
#
#@versioned
#@sourced
#class GeositeAdminName(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = models.TextField(default=None, blank=True, null=True)
#    field_name = _("OSM name")
#
#
#@versioned
#@sourced
#class GeositeAdminId(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = models.BigIntegerField(default=None, blank=True, null=True)
#    field_name = _("OSM ID")
#
#
#@versioned
#@sourced
#class GeositeAdminLevel1(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = models.TextField(default=None, blank=True, null=True)
#    field_name = _("Admin level 1")
#
#
#@versioned
#@sourced
#class GeositeAdminLevel2(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = models.TextField(default=None, blank=True, null=True)
#    field_name = _("Admin level 2")
#
#
#@versioned
#@sourced
#class GeositeCoordinates(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = models.PointField(default=None, blank=True, null=True)
#    objects = models.GeoManager()
#    field_name = _("Coordinates")
#
#
#@versioned
#@sourced
#class GeositeLocationName(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = models.TextField(default=None, blank=True, null=True)
#    field_name = _("Location name")
#
#
#@versioned
#@sourced
#class GeositeLocationId(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = models.BigIntegerField(default=None, blank=True, null=True)
#    field_name = _("Location ID")
#
#
#@versioned
#@sourced
#class GeositeDivisionId(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = models.TextField(default=None, blank=True, null=True)
#    field_name = _("Division ID")
#
#
#@versioned
#@sourced
#class GeositeFirstCited(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = ApproximateDateField(default=None, blank=True, null=True)
#    field_name = _("First cited")
#
#
#@versioned
#@sourced
#class GeositeLastCited(ComplexField):
#    object_ref = models.ForeignKey('Geosite')
#    value = ApproximateDateField(default=None, blank=True, null=True)
#    field_name = _("Last cited")
