from django import forms

from django.conf import settings
from django_date_extensions.fields import ApproximateDateFormField
from django.utils.translation import ugettext as _

from sfm_pc.forms import BaseUpdateForm, BaseCreateForm, GetOrCreateChoiceField

from person.models import Person
from organization.models import Organization

from location.models import Location

from .models import Violation, ViolationStartDate, ViolationEndDate, \
    ViolationType, ViolationPerpetrator, ViolationPerpetratorOrganization, \
    ViolationPerpetratorClassification, ViolationDescription, ViolationDivisionId, \
    ViolationLocationDescription, ViolationAdminLevel1, ViolationAdminLevel2, \
    ViolationLocation

class ViolationBasicsForm(BaseUpdateForm):
    class Meta:
        model = Violation
        fields = '__all__'

    edit_fields = [
        ('startdate', ViolationStartDate, False),
        ('enddate', ViolationEndDate, False),
        ('types', ViolationType, True),
        ('description', ViolationDescription, False),
        ('perpetrator', ViolationPerpetrator, True),
        ('perpetratororganization', ViolationPerpetratorOrganization, True),
        ('perpetratorclassification', ViolationPerpetratorClassification, True),
        ('division_id', ViolationDivisionId, False),
    ]

    startdate = ApproximateDateFormField(label=_("Start date"), required=False)
    enddate = ApproximateDateFormField(label=_("End date"), required=False)
    description = forms.CharField(label=_("Description"))
    perpetrator = forms.ModelMultipleChoiceField(label=_("Perpetrator"), queryset=Person.objects.all(), required=False)
    perpetratororganization = forms.ModelMultipleChoiceField(label=_("Perpetrator unit"), queryset=Organization.objects.all(), required=False)
    division_id = forms.CharField(label=_("Country"), required=False)

    def __init__(self, *args, **kwargs):
        violation_id = kwargs.pop('violation_id', None)

        super().__init__(*args, **kwargs)

        self.fields['perpetratorclassification'] = GetOrCreateChoiceField(
            label=_("Perpetrator classification"),
            queryset=ViolationPerpetratorClassification.objects.all(),
            object_ref_model=self._meta.model,
            form=self,
            field_name='perpetratorclassification',
            object_ref_pk=violation_id,
            required=False
        )
        self.fields['types'] = GetOrCreateChoiceField(label=_("Violation type"),
                                                              queryset=ViolationType.objects.all(),
                                                              object_ref_model=self._meta.model,
                                                              form=self,
                                                              field_name='types',
                                                              object_ref_pk=violation_id)


class ViolationCreateBasicsForm(BaseCreateForm, ViolationBasicsForm):
    pass


class ViolationLocationsForm(BaseUpdateForm):
    class Meta:
        model = Violation
        fields = '__all__'

    edit_fields = [
        ('locationdescription', ViolationLocationDescription, False),
        ('adminlevel1', ViolationAdminLevel1, False),
        ('adminlevel2', ViolationAdminLevel2, False),
        ('location', ViolationLocation, False),
    ]

    locationdescription = forms.CharField(label=_("Location Description"))
    adminlevel1 = forms.ModelChoiceField(label=_("Settlement administrative area"), queryset=Location.objects.all(), required=False)
    adminlevel2 = forms.ModelChoiceField(label=_("Top administrative area"), queryset=Location.objects.all(), required=False)
    location = forms.ModelChoiceField(label=_("Settlement"), queryset=Location.objects.all(), required=False)
