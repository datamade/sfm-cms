# -*- coding: utf-8 -*-
import uuid

from django import forms
from django.utils.translation import ugettext as _, get_language
from django.core.exceptions import ObjectDoesNotExist

from complex_fields.models import ComplexFieldContainer, ComplexFieldListContainer

from django_date_extensions.fields import ApproximateDateFormField

from sfm_pc.templatetags.countries import country_name

from source.models import AccessPoint
from organization.models import Organization, OrganizationDivisionId
from membershipperson.models import \
    MembershipPerson, MembershipPersonRank, MembershipPersonRole, \
    MembershipPersonTitle, MembershipPersonFirstCitedDate, \
    MembershipPersonLastCitedDate, MembershipPersonRealStart, \
    MembershipPersonRealEnd, MembershipPersonStartContext, \
    MembershipPersonEndContext, Rank, Role


class GetOrCreateChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self,
                 queryset,
                 required=True,
                 widget=None,
                 label=None,
                 initial=None,
                 help_text='',
                 *args,
                 **kwargs):

        self.object_ref_model = kwargs.pop('object_ref_model')
        self.object_ref_pk = kwargs.pop('object_ref_pk')
        self.form = kwargs.pop('form')
        self.field_name = kwargs.pop('field_name')
        self.new_instances = []

        super().__init__(queryset,
                         required=required,
                         widget=widget,
                         label=label,
                         initial=initial,
                         help_text=help_text,
                         *args,
                         **kwargs)

    def clean(self, value):
        pks = []

        for v in value:
            try:
                super().clean([v])
                pks.append(v)
            except forms.ValidationError as e:
                # If sources exist for the field, make the object so the rest of
                # the processing will work
                object_ref_fields = [f.column for f in self.object_ref_model._meta.fields]
                pk = self.object_ref_pk
                object_ref_created = False

                if not hasattr(self.form, 'object_ref'):
                    if pk and 'uuid' in object_ref_fields:
                        object_ref = self.object_ref_model.objects.get(uuid=pk)
                    elif 'uuid' in object_ref_fields:
                        object_ref = self.object_ref_model.objects.create(uuid=str(uuid.uuid4()))
                        object_ref_created = True
                    elif pk:
                        object_ref = self.object_ref_model.objects.get(id=pk)
                    else:
                        object_ref = self.object_ref_model.objects.create()
                        object_ref_created = True

                    self.form.object_ref = object_ref

                # It would seem that if someone tries to save a value in the
                # form that can be cast as an integer, there is a slim chance
                # that it will also resolve to a valid choice in which case the
                # validation error above won't get raised. This might be an
                # issue at some point. Perhaps it would be a good idea to use
                # UUIDs universally as pks? This would be a pretty huge lift.

                if e.code == 'invalid_pk_value':
                    value = e.params['pk']
                elif e.code == 'invalid_choice':
                    value = e.params['value']

                instance = self.queryset.model.objects.create(value=value,
                                                              object_ref=self.form.object_ref,
                                                              lang=get_language())
                pks.append(instance.id)
                self.new_instances.append(instance)

                if object_ref_created:
                    self.new_instances.append(object_ref)

        return self.queryset.model.objects.filter(pk__in=pks)


class BaseEditForm(forms.ModelForm):

    # Subclasses need to define Meta like so:
    #
    # class Meta:
    #     model = Person
    #     fields = '__all__'
    #
    # And static properties:
    #
    # edit_fields: 3 tuple of field_name on main entity model, reference to the
    # field model, and whether it expects mutiple values like so:
    #
    # edit_fields = [
    #     ('name', PersonName, False),
    #     ('aliases', PersonAlias, True),
    #     ('gender', PersonGender, False),
    #     ('division_id', PersonDivisionId, False),
    #     ('date_of_birth', PersonDateOfBirth, False),
    #     ('date_of_death', PersonDateOfDeath, False),
    #     ('deceased', PersonDeceased, False),
    #     ('biography', PersonBiography, False),
    #     ('notes', PersonNotes, False),
    #     ('external_links', PersonExternalLink, True),
    # ]

    clone_sources = {}

    def __init__(self, *args, **kwargs):
        self.post_data = dict(kwargs.pop('post_data'))

        try:
            del self.post_data['csrfmiddlewaretoken']
        except KeyError:
            pass

        self.update_fields = set()

        super().__init__(*args, **kwargs)

    @property
    def object_type(self):
        return self._meta.model._meta.model_name

    def _validate_boolean(self):
        boolean_fields = [f for f in self.fields if isinstance(self.fields[f], forms.BooleanField)]

        for field in boolean_fields:

            # If the field isn't in the posted data and there are sources, that
            # means the value should be set to False. If the field isn't in the
            # posted data and there aren't sources, add the field to the empty
            # fields. If the field is in the posted data, set it to True.

            field_sources = self.post_data.get('{}_source'.format(field))

            if not field in self.post_data and not field_sources:
                self.empty_values.add(field)
            elif not field in self.post_data and field_sources:
                self.cleaned_data[field] = False
            elif field in self.post_data:
                self.cleaned_data[field] = True

            # The boolean fields are not actually required but Django
            # forces them to be.
            try:
                self.errors.pop(field)
            except KeyError:
                pass


class BaseUpdateForm(BaseEditForm):

    def clean(self):

        self.empty_values = {k for k,v in self.cleaned_data.items() if not v}

        # Need to validate booleans first cuz Django is being difficult
        self._validate_boolean()

        fields_with_errors = {field for field in self.errors}

        # At this stage it's OK to have empty values. If they were required, the
        # error should already be attached to the field.
        #
        # Sources are required for single value fields if:
        # 1. The value of the field went from blank to not blank
        # 2. The value of the field changed
        #
        # For multiple value fields, these rules also apply:
        # 1. The field has additional values in it.
        #
        # Sources are not required if (but the changes still need to be saved):
        # 1. The value was cleared out
        # 2. For multiple value fields, one or more values was removed.

        for field in self.fields:

            field_instance = getattr(self.instance, field)

            # Sometimes there are fields on the models that are not "complex" so
            # we don't need to worry about sources and stuff

            if not isinstance(field_instance, ComplexFieldContainer) and \
                    not isinstance(field_instance, ComplexFieldListContainer):
                continue

            if self.clone_sources.get(field):
                other_field = self.clone_sources[field]
                self.post_data['{}_source'.format(field)] = self.post_data['{}_source'.format(other_field)]

            posted_sources = self.post_data.get('{}_source'.format(field))

            if posted_sources:
                posted_sources = set(posted_sources)
            else:
                posted_sources = set()

            source_required = getattr(field_instance.field_model, 'source_required', False)
            if source_required and field in self.empty_values and posted_sources:
                error = forms.ValidationError(
                    _('Empty fields should not have sources'),
                    code='invalid')
                self.add_error(field, error)
                continue

            try:
                existing_sources = {str(s.uuid) for s in field_instance.get_sources()}
            except AttributeError:
                existing_sources = set()
                for complex_field in field_instance.get_list():
                    existing_sources = existing_sources | {str(s.uuid) for s in complex_field.get_sources()}

            new_sources = posted_sources - existing_sources

            if not field in (self.empty_values | fields_with_errors):

                if not source_required:
                    self.update_fields.add(field)
                    continue

                posted_value = self.cleaned_data[field]

                if field_instance in self.instance.complex_lists:

                    # Shrug, sometimes the values posted are top level entities
                    # (Person, Organization) so we need to call
                    # .get_value().value

                    try:
                        posted_value = {v.value for v in posted_value}
                    except AttributeError:
                        posted_value_set = set()
                        for value in posted_value:
                            if value.get_value():
                                posted_value_set.add(value.get_value().value)
                            else:
                                posted_value_set.add(None)
                        posted_value = posted_value_set

                    stored_value = {str(v.get_value()) for v in field_instance.get_list()}

                    new_values = getattr(self.fields[field], 'new_instances', [])

                    for value in new_values:
                        stored_value.remove(value.value)

                    # test for some new values
                    if posted_value > stored_value and not new_sources:
                        error = forms.ValidationError(_('This field has new values so it requires sources'),
                                                    code='invalid')
                        self.add_error(field, error)
                        continue

                    # test for all new values
                    if not posted_value & stored_value and not new_sources:
                        error = forms.ValidationError(_('This field has new values so it requires sources'),
                                                    code='invalid')
                        self.add_error(field, error)
                        continue

                else:
                    stored_value = field_instance.get_value()
                    if stored_value:
                        stored_value = stored_value.value

                    if posted_value and not stored_value and not new_sources:
                        error = forms.ValidationError(_('This field now has a value so it requires sources'),
                                                    code='invalid')
                        self.add_error(field, error)
                        continue

                    if (posted_value != stored_value) and not new_sources:
                        error = forms.ValidationError(_('This field changed so it requires sources'),
                                                    code='invalid')
                        self.add_error(field, error)
                        continue

                # Sometimes there are fields that ended up without any sources
                # associated with them. This is probaby due to a bug in the
                # importer script that we used to get the data from the Google
                # spreadsheets. All this code above assumes that if a field has
                # a value in the database, it has sources associated with it.
                # Because of this importer bug, this is not always the case.
                # This is an attempt to handle those cases.

                if (stored_value is not None or stored_value != set()) and not (existing_sources | posted_sources):
                    error = forms.ValidationError(_('Please add some sources to this field'),
                                                code='invalid')
                    self.add_error(field, error)

                self.update_fields.add(field)

        sources_sent = {k.replace('_source', '') for k in self.post_data.keys() if '_source' in k}

        self.update_fields = self.update_fields | sources_sent

    def save(self, commit=True):

        update_info = {}

        for field_name, field_model, multiple_values in self.edit_fields:

            # Somehow when the field is a ComplexFieldListContainer
            # this method is only ever returning the first one which is OK
            # unless we are deleting in which case we need all of the associated
            # fields
            field = ComplexFieldContainer.field_from_str_and_id(
                self.object_type, self.instance.id, field_name
            )

            if field_name in self.empty_values and multiple_values:
                field_models = getattr(self.instance, field_name)

                for field in field_models.get_list():
                    field_model = field.get_value()
                    field_model.delete()

            elif field_name in self.empty_values:
                field_model = field.get_value()

                if field_model:
                    field_model.delete()

            source_key = '{}_source'.format(field_name)
            confidence_key = '{}_confidence'.format(field_name)

            if field_name in self.update_fields or self.post_data.get(source_key):

                update_value = self.cleaned_data[field_name]
                update_key = '{0}_{1}'.format(self.instance._meta.object_name,
                                              field_model._meta.object_name)

                confidence = field.get_confidence()
                if self.post_data.get(confidence_key):
                    confidence = self.post_data[confidence_key][0]

                update_info[update_key] = {
                    'confidence': confidence,
                }

                if getattr(field_model, 'source_required', False):
                    new_source_ids = self.post_data[source_key]
                    sources = AccessPoint.objects.filter(uuid__in=new_source_ids)
                    update_info[update_key]['sources'] = sources

                if multiple_values:
                    update_info[update_key]['values'] = update_value
                    # Sometimes the object that we want the values to normalize
                    # to are not the complex field containers. For instance, we
                    # want the violation perpetrators to normalize to a Person
                    # object for the form, not a ViolationPerpetrator object so
                    # that we can search across all the people, not just the
                    # ones who have committed violations. So, if the values in
                    # update_value are not instances of the field_model, we need
                    # to get or create those and replace the values with the
                    # instances of the field_model so that the validation, etc
                    # works under the hood.

                    new_values = []

                    for value in update_value:
                        if not isinstance(value, field_model):
                            value, _ = field_model.objects.get_or_create(value=value,
                                                                         object_ref=self.instance,
                                                                         lang=get_language())
                            new_values.append(value)

                    if new_values:
                        update_info[update_key]['values'] = new_values
                else:
                    # When we are allowing for new values to be created for
                    # a field where we expect only a single value, we need to
                    # clean up older values so that there is only ever one
                    # related object. This is partially because it's good to be
                    # clean and partially because it sometimes ends up looking
                    # like nothing has changed since Django might always fetch
                    # older items when it's building the objects that get
                    # displayed.

                    existing_values = field_model.objects.filter(object_ref=self.instance)

                    for value in existing_values:
                        if value.value != self.post_data[field_name][0]:
                            value.delete()

                    update_info[update_key]['value'] = update_value

        if update_info:
            self.instance.update(update_info)

        if self.post_data.get('published'):
            self.instance.published = True
        else:
            self.instance.published = False

        self.instance.save()

        self.instance.object_ref_saved()

        return self.instance


class BaseCreateForm(BaseEditForm):

    def clean(self):

        self.empty_values = {k for k,v in self.cleaned_data.items() if not v}

        # Need to validate booleans first cuz Django is being difficult
        self._validate_boolean()

        fields_with_errors = {field for field in self.errors}

        for field_name, field_model, multiple_values in self.edit_fields:

            if self.clone_sources.get(field_name):
                other_field = self.clone_sources[field_name]
                self.post_data['{}_source'.format(field_name)] = self.post_data.get('{}_source'.format(other_field), [])

            posted_sources = self.post_data.get('{}_source'.format(field_name))

            if posted_sources:
                posted_sources = set(posted_sources)
            else:
                posted_sources = set()

            source_required = getattr(field_model, 'source_required', False)
            if source_required and field_name in self.empty_values and posted_sources:
                error = forms.ValidationError(
                    _('Empty fields should not have sources'),
                    code='invalid')
                self.add_error(field_name, error)
                continue

            if not field_name in (self.empty_values | fields_with_errors):

                if not source_required:
                    self.update_fields.add(field_name)
                    continue

                posted_value = self.cleaned_data[field_name]

                if posted_value and not posted_sources:
                    error = forms.ValidationError(_('This field requires sources'),
                                                    code='invalid')
                    self.add_error(field_name, error)
                    continue

                self.update_fields.add(field_name)

        sources_sent = {k.replace('_source', '') for k in self.post_data.keys() if '_source' in k}

        self.update_fields = self.update_fields | sources_sent

    def save(self, commit=True):

        update_info = {}

        if not hasattr(self, 'object_ref'):
            object_ref_fields = [f.column for f in self._meta.model._meta.fields]

            if 'uuid' in object_ref_fields:
                self.object_ref = self._meta.model.objects.create(uuid=str(uuid.uuid4()))
            else:
                self.object_ref = self._meta.model.objects.create()

        for field_name, field_model, multiple_values in self.edit_fields:

            # Somehow when the field is a ComplexFieldListContainer
            # this method is only ever returning the first one which is OK
            # unless we are deleting in which case we need all of the associated
            # fields
            field = ComplexFieldContainer.field_from_str_and_id(
                self.object_type, self.object_ref.id, field_name
            )

            source_key = '{}_source'.format(field_name)
            confidence_key = '{}_confidence'.format(field_name)

            if field_name in self.update_fields or self.post_data.get(source_key):

                update_value = self.cleaned_data[field_name]
                update_key = '{0}_{1}'.format(self._meta.model._meta.object_name,
                                              field_model._meta.object_name)

                confidence = field.get_confidence()
                if self.post_data.get(confidence_key):
                    confidence = self.post_data[confidence_key][0]

                update_info[update_key] = {
                    'confidence': confidence,
                }

                if getattr(field_model, 'source_required', False):
                    new_source_ids = self.post_data[source_key]
                    sources = AccessPoint.objects.filter(uuid__in=new_source_ids)
                    update_info[update_key]['sources'] = sources

                if multiple_values:
                    update_info[update_key]['values'] = update_value

                    new_values = []

                    for value in update_value:
                        if not isinstance(value, field_model):
                            value, _ = field_model.objects.get_or_create(value=value,
                                                                         object_ref=self.object_ref,
                                                                         lang=get_language())
                            new_values.append(value)

                    if new_values:
                        update_info[update_key]['values'] = new_values
                else:
                    update_info[update_key]['value'] = update_value

        if update_info:
            self.object_ref.update(update_info)

        self.object_ref.object_ref_saved()

        return self.object_ref


def division_choices():
    division_ids = OrganizationDivisionId.objects.distinct('value').order_by('value')
    return [(r.value, country_name(r.value)) for r in division_ids]


def download_types():
    return [
        ('basic', _("Basic")),
        ('parentage', _("Parentage")),
        ('memberships', _("Memberships")),
        ('areas', _("Areas of operation")),
        ('sites', _("Sites")),
        ('personnel', _("Personnel")),
        ('sources', _("Sources")),
    ]


class DownloadForm(forms.Form):
    download_type = forms.ChoiceField(label=_("Choose a download type"), choices=download_types)
    division_id = forms.ChoiceField(label=_("Country"), choices=division_choices)
    sources = forms.BooleanField(label=_("Include sources"), required=False)
    confidences = forms.BooleanField(label=_("Include confidence scores"), required=False)


class ChangeLogForm(forms.Form):
    from_date = forms.DateTimeField(label=_("Start date"), required=False)
    to_date = forms.DateTimeField(label=_("End date"), required=False)
