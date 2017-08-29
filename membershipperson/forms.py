from django import forms

from django_date_extensions.fields import ApproximateDateFormField

from membershipperson.models import MembershipPerson

from complex_fields.models import CONFIDENCE_LEVELS


class MembershipPersonForm(forms.Form):
    membership = forms.ModelChoiceField(queryset=MembershipPerson.objects.all())
    first = forms.BooleanField(required=False)

    title = forms.CharField(required=False)
    title_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    role = forms.CharField(required=False)
    rank = forms.CharField(required=False)
    role_rank_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    startcontext = forms.CharField(required=False)
    realstart = forms.BooleanField(required=False)
    startcontext_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    endcontext = forms.CharField(required=False)
    realend = forms.BooleanField(required=False)
    endcontext_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)

    firstciteddate = ApproximateDateFormField(required=False)
    lastciteddate = ApproximateDateFormField(required=False)
    date_confidence = forms.ChoiceField(choices=CONFIDENCE_LEVELS)
