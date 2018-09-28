# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext as _, get_language

from complex_fields.models import ComplexFieldContainer

from django_date_extensions.fields import ApproximateDateFormField

from source.models import Source
from organization.models import Organization
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

        self.object_ref_pk = kwargs.pop('object_ref_pk')
        self.object_ref_model = kwargs.pop('object_ref_model')
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
                if 'uuid' in object_ref_fields:
                    object_ref = self.object_ref_model.objects.get(uuid=self.object_ref_pk)
                else:
                    object_ref = self.object_ref_model.objects.get(id=self.object_ref_pk)

                # It would seem that if someone tries to save a value in the
                # form that can be cast as an integer, there is a slim chance
                # that it will also resolve to a valid choice in which case the
                # validation error above won't get raised. This might be an
                # issue at some point.

                if e.code == 'invalid_pk_value':
                    value = e.params['pk']
                elif e.code == 'invalid_choice':
                    value = e.params['value']

                instance = self.queryset.model.objects.create(value=value,
                                                              object_ref=object_ref,
                                                              lang=get_language())
                pks.append(instance.id)
                self.new_instances.append(instance)

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

    def __init__(self, *args, **kwargs):
        self.post_data = dict(kwargs.pop('post_data'))

        try:
            del self.post_data['csrfmiddlewaretoken']
        except KeyError:
            pass

        self.object_ref_pk = kwargs.pop('object_ref_pk')
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

            posted_sources = self.post_data.get('{}_source'.format(field))

            if posted_sources:
                posted_sources = set(posted_sources)
            else:
                posted_sources = set()

            try:
                existing_sources = {str(s.uuid) for s in field_instance.get_sources()}
            except AttributeError:
                existing_sources = set()
                for complex_field in field_instance.get_list():
                    existing_sources = existing_sources | {str(s.uuid) for s in complex_field.get_sources()}

            new_sources = posted_sources - existing_sources

            if not field in (self.empty_values | fields_with_errors):

                if not field_instance.field_model.source_required:
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
                        posted_value = set()
                        for value in posted_value:
                            if value.get_value():
                                posted_value.add(value.get_value().value)
                            else:
                                posted_value.add(None)

                    stored_value = {str(v.get_value()) for v in field_instance.get_list()}

                    new_values = getattr(self.fields[field], 'new_instances', [])

                    for value in new_values:
                        stored_value.remove(value.value)

                    # test for some new values
                    if posted_value > stored_value and not new_sources:
                        error = forms.ValidationError(_('"%(field_name)s" has new values so it requires sources'),
                                                    code='invalid',
                                                    params={'field_name': field})
                        self.add_error(field, error)
                        continue

                    # test for all new values
                    if not posted_value & stored_value and not new_sources:
                        error = forms.ValidationError(_('"%(field_name)s" has new values so it requires sources'),
                                                    code='invalid',
                                                    params={'field_name': field})
                        self.add_error(field, error)
                        continue

                else:
                    stored_value = field_instance.get_value()
                    if stored_value:
                        stored_value = stored_value.value

                    if posted_value and not stored_value and not new_sources:
                        error = forms.ValidationError(_('"%(field_name)s" now has a value so it requires sources'),
                                                    code='invalid',
                                                    params={'field_name': field})
                        self.add_error(field, error)
                        continue

                    if (posted_value != stored_value) and not new_sources:
                        error = forms.ValidationError(_('The value of "%(field_name)s" changed so it requires sources'),
                                                    code='invalid',
                                                    params={'field_name': field})
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
                    error = forms.ValidationError(_('Please add some sources to "%(field_name)s"'),
                                                code='invalid',
                                                params={'field_name': field})
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

            if field_name in self.update_fields or self.post_data.get(source_key):

                update_value = self.cleaned_data[field_name]
                update_key = '{0}_{1}'.format(self.instance._meta.object_name,
                                              field_model._meta.object_name)

                update_info[update_key] = {
                    'confidence': field.get_confidence(),
                }

                if field_model.source_required:
                    new_source_ids = self.post_data[source_key]
                    sources = Source.objects.filter(uuid__in=new_source_ids)
                    update_info[update_key]['sources'] = new_source_ids

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
                    update_info[update_key]['value'] = update_value

        if update_info:
            self.instance.update(update_info)

        self.instance.object_ref_saved()
