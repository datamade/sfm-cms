import uuid

import reversion
from django.db import models
from django.utils.translation import ugettext as _
from django_date_extensions.fields import ApproximateDateField
from complex_fields.model_decorators import versioned, translated, sourced
from complex_fields.base_models import BaseModel
from complex_fields.models import ComplexField, ComplexFieldContainer

from sfm_pc.utils import VersionsMixin
from sfm_pc.fields import GetComplexFieldNameMixin


@reversion.register()
class PersonBiography(models.Model, BaseModel, VersionsMixin, GetComplexFieldNameMixin):
    """
    Extra biographical metadata for Persons.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        verbose_name_plural = 'person biographies'

    def __init__(self, *args, **kwargs):
        self.person = ComplexFieldContainer(self, PersonBiographyPerson)
        self.gender = ComplexFieldContainer(self, PersonBiographyGender)
        self.date_of_birth = ComplexFieldContainer(self, PersonBiographyDateOfBirth)
        self.date_of_death = ComplexFieldContainer(self, PersonBiographyDateOfDeath)
        self.deceased = ComplexFieldContainer(self, PersonBiographyDeceased)

        self.complex_fields = [
            self.person, self.gender, self.date_of_birth, self.date_of_death,
            self.deceased,
        ]
        self.complex_lists = []

        super().__init__(*args, **kwargs)


@versioned
class PersonBiographyPerson(ComplexField):
    object_ref = models.ForeignKey('PersonBiography')
    value = models.ForeignKey('person.Person')
    field_name = _('Person')
    shortcode = 'pe_n'
    spreadsheet_field_name = 'person_extra:name'


@translated
@versioned
@sourced
class PersonBiographyGender(ComplexField):
    object_ref = models.ForeignKey('PersonBiography')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Gender")
    shortcode = 'pe_g'
    spreadsheet_field_name = 'person_extra:gender'


@versioned
@sourced
class PersonBiographyDateOfBirth(ComplexField):
    object_ref = models.ForeignKey('PersonBiography')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Date of Birth")
    shortcode = 'pe_dob'
    spreadsheet_field_name = 'person_extra:date_of_birth'


@versioned
@sourced
class PersonBiographyDateOfDeath(ComplexField):
    object_ref = models.ForeignKey('PersonBiography')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Date Deceased")
    shortcode = 'pe_dd'
    spreadsheet_field_name = 'person_extra:deceased_date'


@versioned
@sourced
class PersonBiographyDeceased(ComplexField):
    object_ref = models.ForeignKey('PersonBiography')
    value = models.BooleanField(default=False)
    field_name = _("Deceased")
    shortcode = 'pe_d'
    spreadsheet_field_name = 'person_extra:deceased'
