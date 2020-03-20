import uuid

import reversion
from django.db import models
from django.utils.translation import ugettext as _
from complex_fields.model_decorators import versioned, translated, sourced
from complex_fields.base_models import BaseModel
from complex_fields.models import ComplexField, ComplexFieldContainer

from sfm_pc.utils import VersionsMixin
from sfm_pc.fields import GetComplexFieldNameMixin


@reversion.register()
class PersonExtra(models.Model, BaseModel, VersionsMixin, GetComplexFieldNameMixin):
    """
    Extra information for Persons, intended to have a many-to-one relationship.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    def __init__(self, *args, **kwargs):
        self.person = ComplexFieldContainer(self, PersonExtraPerson)
        self.account_type = ComplexFieldContainer(self, PersonExtraAccountType)
        self.account = ComplexFieldContainer(self, PersonExtraAccount)
        self.external_link_description = ComplexFieldContainer(self, PersonExtraExternalLinkDescription)
        self.media_description = ComplexFieldContainer(self, PersonExtraMediaDescription)
        self.notes = ComplexFieldContainer(self, PersonExtraNotes)

        self.complex_fields = [
            self.person, self.account_type, self.account,
            self.external_link_description, self.media_description, self.notes
        ]
        self.complex_lists = []

        super().__init__(*args, **kwargs)


@versioned
class PersonExtraPerson(ComplexField):
    object_ref = models.ForeignKey('PersonExtra')
    value = models.ForeignKey('person.Person')
    field_name = _('Person')
    shortcode = 'pe_n'
    spreadsheet_field_name = 'person_extra:name'


@translated
@versioned
@sourced
class PersonExtraAccountType(ComplexField):
    object_ref = models.ForeignKey('PersonExtra')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Online Account Type")
    shortcode = 'pe_at'
    spreadsheet_field_name = 'person_extra:account_type'
    spreadsheet_confidence_field_name = 'person_extra:account:confidence'
    spreadsheet_source_field_name = 'person_extra:account:source'


@versioned
@sourced
class PersonExtraAccount(ComplexField):
    object_ref = models.ForeignKey('PersonExtra')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Online Account Identifier")
    shortcode = 'pe_aid'
    spreadsheet_field_name = 'person_extra:account_id'
    spreadsheet_confidence_field_name = 'person_extra:account:confidence'
    spreadsheet_source_field_name = 'person_extra:account:source'


@translated
@versioned
@sourced
class PersonExtraExternalLinkDescription(ComplexField):
    object_ref = models.ForeignKey('PersonExtra')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("External Link Description")
    shortcode = 'pe_eld'
    spreadsheet_field_name = 'person_extra:external_link_description'
    spreadsheet_confidence_field_name = 'person_extra:external_link:confidence'
    spreadsheet_source_field_name = 'person_extra:external_link:source'


@translated
@versioned
@sourced
class PersonExtraMediaDescription(ComplexField):
    object_ref = models.ForeignKey('PersonExtra')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Media Description")
    shortcode = 'pe_md'
    spreadsheet_field_name = 'person_extra:media_desc'
    spreadsheet_confidence_field_name = 'person_extra:media:confidence'
    spreadsheet_source_field_name = 'person_extra:media:source'


@translated
@versioned
@sourced
class PersonExtraNotes(ComplexField):
    object_ref = models.ForeignKey('PersonExtra')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Notes")
    shortcode = 'pe_n_a'
    spreadsheet_field_name = 'person_extra:notes:admin'
