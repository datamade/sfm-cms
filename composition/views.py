import json

from django.views.generic.base import TemplateView
from django.http import HttpResponse
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import redirect
from complex_fields.models import CONFIDENCE_LEVELS

from source.models import Source
from organization.models import Organization
from composition.models import Composition, Classification
from composition.forms import CompositionForm
from sfm_pc.base_views import BaseFormSetView


class CompositionCreate(BaseFormSetView):
    template_name = 'composition/create.html'
    form_class = CompositionForm
    success_url = reverse_lazy('create-organization-membership')
    extra = 0
    max_num = None

    def get_initial(self):
        data = []
        if self.request.session.get('organizations'):
            for i in self.request.session['organizations']:
                data.append({})
        return data

    def get(self, request, *args, **kwargs):
        if self.request.session.get('organizations'):
            if len(request.session['organizations']) == 1:
                return redirect(reverse_lazy('create-organization-membership'))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['confidence_levels'] = CONFIDENCE_LEVELS

        context['classifications'] = Classification.objects.all()
        context['relationship_types'] = self.form_class().fields['relationship_type'].choices
        context['source'] = Source.objects.get(id=self.request.session['source_id'])
        context['organizations'] = self.request.session.get('organizations')

        context['back_url'] = reverse_lazy('create-organization')
        context['skip_url'] = reverse_lazy('create-organization-membership')

        return context

    def formset_valid(self, formset):
        source = Source.objects.get(id=self.request.session['source_id'])
        num_forms = int(formset.data['form-TOTAL_FORMS'][0])

        for i in range(0, num_forms):
            form_prefix = 'form-{0}-'.format(i)

            composition_info = {}

            if formset.data.get(form_prefix + 'startdate'):
                composition_info['Composition_CompositionStartDate'] = {
                    'value': formset.data[form_prefix + 'startdate'],
                    'confidence': 1,
                    'sources': [source]
                }

            if formset.data.get(form_prefix + 'enddate'):
                composition_info['Composition_CompositionEndDate'] = {
                    'value': formset.data[form_prefix + 'enddate'],
                    'confidence': 1,
                    'sources': [source]
                }

            classification_id = formset.data[form_prefix + 'classification']
            classification = Classification.objects.get(id=classification_id)

            composition_info['Composition_CompositionClassification'] = {
                'value': classification,
                'confidence': 1,
                'sources': [source]
            }

            organization_id = formset.data[form_prefix + 'organization']
            organization = Organization.objects.get(id=organization_id)

            related_organization_id = formset.data[form_prefix + 'related_organization']
            related_organization = Organization.objects.get(id=related_organization_id)

            rel_type = formset.data[form_prefix + 'relationship_type']
            if rel_type == 'child':

                composition, created = Composition.objects.get_or_create(compositionparent__value=related_organization,
                                                                         compositionchild__value=organization)

                if created:
                    sources = [source]

                else:
                    self.source = source
                    sources = self.sourcesList(composition, 'child')

                composition_info['Composition_CompositionChild'] = {
                    'value': organization,
                    'confidence': 1,
                    'sources': sources
                }
                composition_info['Composition_CompositionParent'] = {
                    'value': related_organization,
                    'confidence': 1,
                    'sources': sources
                }

            elif rel_type == 'parent':

                composition, created = Composition.objects.get_or_create(compositionchild__value=related_organization,
                                                                         compositionparent__value=organization)

                if created:
                    sources = [source]

                else:
                    self.source = source
                    sources = self.sourcesList(composition, 'parent')

                composition_info['Composition_CompositionParent'] = {
                    'value': organization,
                    'confidence': 1,
                    'sources': [source]
                }
                composition_info['Composition_CompositionChild'] = {
                    'value': related_organization,
                    'confidence': 1,
                    'sources': [source]
                }

            composition.update(composition_info)

        response = super().formset_valid(formset)
        return response


class CompositionUpdate(TemplateView):
    template_name = 'composition/edit.html'

    def post(self, request, *args, **kwargs):
        data = json.loads(request.POST.dict()['object'])
        try:
            composition = Composition.objects.get(pk=kwargs.get('pk'))
        except Composition.DoesNotExist:
            msg = "This composition does not exist, it should be created " \
                  "before updating it."
            return HttpResponse(msg, status=400)

        (errors, data) = composition.validate(data)
        if len(errors):
            return HttpResponse(
                json.dumps({"success": False, "errors": errors}),
                content_type="application/json"
            )

        composition.update(data)
        return HttpResponse(
            json.dumps({"success": True}),
            content_type="application/json"
        )

    def get_context_data(self, **kwargs):
        context = super(CompositionUpdate, self).get_context_data(**kwargs)
        context['composition'] = Composition.objects.get(pk=context.get('pk'))

        return context
