from django.db import models
from django.utils.translation import ugettext as _
from django.utils.translation import get_language

from django_date_extensions.fields import ApproximateDateField

from source.models import Source
from complex_fields.model_decorators import versioned, translated, sourced
from complex_fields.models import ComplexField, ComplexFieldContainer


class Organization(models.Model):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = ComplexFieldContainer(self, OrganizationName)
        self.alias = ComplexFieldContainer(self, OrganizationAlias)
        self.classification = ComplexFieldContainer(self, OrganizationClassification)
        self.foundingdate = ComplexFieldContainer(self, OrganizationFoundingDate)
        self.dissolutiondate = ComplexFieldContainer(self, OrganizationDissolutionDate)
        self.realfounding = ComplexFieldContainer(self, OrganizationRealFounding)
        self.realdissolution = ComplexFieldContainer(self, OrganizationRealDissolution)

        self.complex_fields = [self.name, self.alias, self.classification,
                               self.foundingdate, self.dissolutiondate,
                               self.realfounding, self.realdissolution]

        self.required_fields = [
            "Organization_OrganizationName",
        ]

    def get_value(self):
        return self.name.get_value()

    @classmethod
    def from_id(cls, id_):
        try:
            membership = cls.objects.get(id=id_)
            return membership
        except cls.DoesNotExist:
            return None

    def validate(self, dict_values, lang):
        errors = {}
        for field in self.complex_fields:
            field_name = field.get_field_str_id()

            if ((field_name not in dict_values or
                 dict_values[field_name]['value'] == "") and
                field_name in self.required_fields):
                errors[field_name] = "This field is required"
            elif field_name in dict_values:
                sources = dict_values[field_name].get('sources', [])
                (error, value) = field.validate(
                    dict_values[field_name]['value'], lang, sources
                )

                if error is not None:
                    errors[field_name] = error
                else:
                    dict_values[field_name]['value'] = value

        return (dict_values, errors)

    def update(self, dict_values, lang=get_language()):
        (dict_values, errors) = self.validate(dict_values, lang)
        if len(errors):
            return errors

        self.save()
        for field in self.complex_fields:
            field_name = field.get_field_str_id()

            if field in dict_values:
                source = Source.create_sources(
                    dict_values[field_name].get('sources', [])
                )
                field.update(dict_values[field_name]['values'], lang, sources)


    @classmethod
    def create(cls, dict_values, lang=get_language()):
        org = cls()
        errors = org.update(dict_values, lang)
        return errors


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
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Alias")


@versioned
@sourced
class OrganizationClassification(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.ForeignKey('Classification', default=None, blank=True,
                              null=True)
    field_name = _("Classification")


@versioned
@sourced
class OrganizationFoundingDate(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Date of creation")


@versioned
@sourced
class OrganizationDissolutionDate(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Date of disbandment")


@versioned
@sourced
class OrganizationRealFounding(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.BooleanField(default=None)
    field_name = _("Real creation")


@versioned
@sourced
class OrganizationRealDissolution(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.BooleanField(default=None)
    field_name = _("Real dissolution")


class Classification(models.Model):
    value = models.TextField()
