# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext as _

from django_date_extensions.fields import ApproximateDateFormField

from complex_fields.models import CONFIDENCE_LEVELS


class PersonForm(forms.Form):
    name = forms.CharField(error_messages={'required': _('Name is required')})
    name_text = forms.CharField()
    name_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    alias = forms.CharField(required=False)
    alias_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    orgs = forms.CharField(required=False)
    orgs_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    division_id = forms.CharField(error_messages={'required': _('Division ID is required')})
    division_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.empty_permitted = False
