from django import forms

from django_date_extensions.fields import ApproximateDateFormField
from complex_fields.models import CONFIDENCE_LEVELS

from composition.models import Classification
from organization.models import Organization


class CompositionForm(forms.Form):
    related_organization = forms.ModelChoiceField(queryset=Organization.objects.all())
    related_org_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    relationship_type = forms.ChoiceField(choices=(('parent', 'Parent',), ('child', 'Child',)))
    relationship_type_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    classification = forms.ModelChoiceField(queryset=Classification.objects.all())
    classification_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    startdate = ApproximateDateFormField(required=False)
    enddate = ApproximateDateFormField(required=False)
    date_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)
