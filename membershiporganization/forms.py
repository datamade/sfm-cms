from django import forms

from django_date_extensions.fields import ApproximateDateFormField
from complex_fields.models import CONFIDENCE_LEVELS

class MembershipOrganizationForm(forms.Form):
    member = forms.CharField()
    organization = forms.CharField()
    organization_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    firstciteddate = ApproximateDateFormField(required=False)
    lastciteddate = ApproximateDateFormField(required=False)
    date_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)
