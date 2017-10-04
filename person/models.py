import uuid

from django.db import models, connection
from django.contrib.gis.geos import Point
from django.utils.translation import ugettext as _
from django.db.models import Max
from django.http import HttpResponse

from django_date_extensions.fields import ApproximateDateField

from complex_fields.model_decorators import versioned, translated, sourced
from complex_fields.models import ComplexField, ComplexFieldContainer, \
    ComplexFieldListContainer
from complex_fields.base_models import BaseModel


class Person(models.Model, BaseModel):
    
    uuid = models.UUIDField(default=uuid.uuid4, 
                            editable=False, 
                            db_index=True)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = ComplexFieldContainer(self, PersonName)
        self.aliases = ComplexFieldListContainer(self, PersonAlias)
        self.division_id = ComplexFieldContainer(self, PersonDivisionId)
        
        self.complex_fields = [self.name, self.division_id]

        self.required_fields = [
            "Person_PersonName",
        ]

    def get_value(self):
        return self.name.get_value()

    def __str__(self):
        return str(self.name)

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
    value = models.ForeignKey('Alias', default=None, blank=True, null=True)
    field_name = _("Alias")

class Alias(models.Model):
    value = models.TextField()
    
    def __str__(self):
        return self.value

@versioned
@sourced
class PersonDivisionId(ComplexField):
    object_ref = models.ForeignKey('Person')
    value = models.TextField(default=None, blank=True, null=True)

    field_name = _('Division ID')
