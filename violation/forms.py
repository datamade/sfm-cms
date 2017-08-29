from django import forms

from django_date_extensions.fields import ApproximateDateFormField
from complex_fields.models import CONFIDENCE_LEVELS

from leaflet.forms.widgets import LeafletWidget
from .models import ViolationLocation


class ViolationForm(forms.Form):
    startdate = ApproximateDateFormField(required=True)
    enddate = ApproximateDateFormField(required=True)
    date_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    locationdescription = forms.CharField(required=False)
    locationdescription_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    geotype = forms.CharField(required=False)
    osm_id = forms.CharField(required=False)
    osm_id_text = forms.CharField(required=False)
    osm_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    description = forms.CharField(required=True)
    description_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    perpetrators = forms.CharField(required=False)
    perp_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    orgs = forms.CharField(required=False)
    orgs_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    vtype = forms.CharField(required=False)
    type_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)


class ZoneForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ZoneForm, self).__init__(*args, **kwargs)
        self.fields['value'].widget = LeafletWidget(attrs={
            "id": "Violation_ViolationLocation"
        })

    class Meta:
        model = ViolationLocation
        fields = ('value',)
        widgets = {'value': LeafletWidget()}
