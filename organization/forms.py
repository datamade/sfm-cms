from django import forms

from django_date_extensions.fields import ApproximateDateFormField
from django.utils.translation import ugettext as _

from complex_fields.models import CONFIDENCE_LEVELS

class OrganizationForm(forms.Form):
    name = forms.CharField(error_messages={'required': _('Unit name is required')})
    name_text = forms.CharField()
    name_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    classification = forms.CharField(error_messages={'required': _('Classification is required')})
    classification_text = forms.CharField()
    classification_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    alias = forms.CharField(required=False)
    alias_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    division_id = forms.CharField(error_messages={'required': _('Division ID is required')})
    division_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.empty_permitted = False


class OrganizationGeographyForm(forms.Form):
    geography_type = forms.ChoiceField(choices=(('Site', 'Site'), ('Area', 'Area'), ),
                                       error_messages={'required': _('Geography type is required')})
    name = forms.CharField(error_messages={'required': _('Name is required')})
    osm_id = forms.CharField(error_messages={'required': _('OSM ID is required')})
    osm_id_text = forms.CharField()
    startdate = ApproximateDateFormField(required=False)
    enddate = ApproximateDateFormField(required=False)
    org = forms.CharField()
    geotype = forms.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.empty_permitted = False
