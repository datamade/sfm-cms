import json
from uuid import uuid4
import itertools
import sys

import pysolr

from reversion.views import RevisionMixin
import reversion

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, TemplateView
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template

from complex_fields.models import ComplexFieldContainer

from countries_plus.models import Country

from sfm_pc.base_views import BaseDeleteView, JSONResponseMixin
from sfm_pc.utils import VersionsMixin, get_source_context
from sfm_pc.templatetags.citations import get_citation_string

from source.models import Source, AccessPoint
from source.forms import SourceForm


class SourceView(LoginRequiredMixin, DetailView):
    model = Source
    context_object_name = 'source'
    template_name = 'source/view.html'


class SourceEvidenceView(SourceView):
    """
    Detail view for a Source, including a table of records evidenced by a specific
    access point.
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        access_point = get_object_or_404(AccessPoint, uuid=self.kwargs['access_point_id'])
        context['access_point'] = access_point
        context['related_entities'] = access_point.related_entities

        return context


class SourceEditView(LoginRequiredMixin, RevisionMixin):
    fields = [
        'title',
        'publication',
        'publication_country',
        'published_date',
        'source_url',
    ]
    model = Source
    template_name = 'source/edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries'] = Country.objects.all()

        return context

    def get_success_url(self):
        return reverse_lazy('view-source', kwargs={'pk': self.object.uuid})

    def form_valid(self, form):
        self.form = form

        reversion.set_comment(self.request.POST['comment'])

        self.form.instance.user = self.request.user

        return super().form_valid(form)


class SourceUpdate(SourceEditView, UpdateView):
    pass


class SourceCreate(SourceEditView, CreateView):
    fields = [
        'title',
        'publication',
        'publication_country',
        'published_date',
        'source_url',
        'uuid',
    ]
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['source_id'] = str(uuid4())

        return context

    def get_success_url(self):
        return reverse_lazy('update-source', kwargs={'pk': self.object.uuid})


class SourceRevertView(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):

        version_id = request.POST['version_id']

        revision = Version.objects.get(id=version_id).revision

        reversion.set_comment(request.POST['comment'])
        reversion.set_user(request.user)

        revision.revert()

        return HttpResponseRedirect(reverse_lazy('update-source',
                                                 kwargs={'pk': kwargs['pk']}))


class SourceDeleteView(BaseDeleteView):
    model = Source
    template_name = 'source/delete.html'

    def get_cancel_url(self):
        return reverse_lazy('update-source', kwargs={
            'pk': self.object.uuid,
        })

    def get_success_url(self):
        return reverse('search') + '?entity_type=Source'

    def get_related_entities(self):
        return self.object.related_entities


class AccessPointEdit(LoginRequiredMixin,
                      VersionsMixin,
                      RevisionMixin):
    fields = [
        'trigger',
        'accessed_on',
        'archive_url'
    ]
    model = AccessPoint
    template_name = 'source/access-points.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['source'] = Source.objects.get(uuid=self.kwargs['source_id'])
        return context

    def get_success_url(self):
        return reverse_lazy('add-access-point', kwargs={'source_id': self.object.source.uuid})

    def form_valid(self, form):
        self.form = form
        source = Source.objects.get(uuid=self.kwargs['source_id'])

        reversion.set_comment(self.request.POST['comment'])
        reversion.add_to_revision(source)

        self.form.instance.source = source
        self.form.instance.user = self.request.user

        return super().form_valid(form)


class AccessPointDetail(LoginRequiredMixin,
                        VersionsMixin,
                        ListView):
    model = AccessPoint
    template_name = 'source/access-points.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['source'] = Source.objects.get(uuid=self.kwargs['source_id'])
        return context

    def get_queryset(self):
        return AccessPoint.objects.filter(source__uuid=self.kwargs['source_id'])


class AccessPointUpdate(AccessPointEdit, UpdateView):
    pass


class AccessPointCreate(AccessPointEdit, CreateView):
    pass


class AccessPointDelete(BaseDeleteView):
    model = AccessPoint
    template_name = 'source/delete-access-point.html'

    def get_cancel_url(self):
        return reverse_lazy('view-access-point', kwargs={
            'source_id': self.kwargs['source_id'],
        })

    def get_success_url(self):
        return reverse_lazy('view-access-point', kwargs={
            'source_id': self.kwargs['source_id'],
        })

    def get_related_entities(self):
        return self.object.related_entities


class StashSourceView(TemplateView, JSONResponseMixin, LoginRequiredMixin):

    http_method_names = ['get']

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        source_id = self.request.GET['accesspoint_id']
        field_name = self.request.GET['field_name']

        access_point = AccessPoint.objects.get(uuid=source_id)

        context.update(get_source_context(field_name, access_point))

        template = get_template('partials/access_point_input.html')
        context['source_input'] = template.render(context)

        return context


def source_autocomplete(request):
    term = request.GET.get('q')

    response = {
        'results': []
    }

    if term:
        sources = Source.objects.filter(title__icontains=term).order_by('-date_updated')

        for source in sources:

            for access_point in source.accesspoint_set.all():

                result = {
                    'title': source.title,
                    'publication': source.publication,
                    'publication_country': source.publication_country,
                    'page_number': access_point.trigger,
                    'archive_url': access_point.archive_url,
                    'access_point': str(access_point),
                    'accessed_on': None,
                    'text': source.title,
                    'id': str(access_point.uuid),
                }

                if access_point.accessed_on:
                    result['accessed_on'] = access_point.accessed_on.isoformat()

                response['results'].append(result)

    return HttpResponse(json.dumps(response), content_type='application/json')


def extract_source(source, uncommitted=False):
    source_info = {
        'title': source.title,
        'id': str(source.uuid),
        'publication': source.publication,
        'publication_country': source.publication_country,
        'source_url': source.source_url,
        'access_points': [],
        'uncommitted': uncommitted,
    }

    for access_point in source.accesspoint_set.all():
        ap_info = {
            'id': str(access_point.uuid),
            'page_number': access_point.trigger,
            'archive_url': access_point.archive_url,
            'accessed_on': access_point.accessed_on,
        }

        source_info['access_points'].append(ap_info)

    return source_info


def get_sources(request):
    object_type = request.GET['object_type']
    object_id = request.GET['object_id']
    field_name = request.GET['field_name']

    field = ComplexFieldContainer.field_from_str_and_id(
        object_type, object_id, field_name
    )

    sources = field.get_sources()
    sources_json = {
        "confidence": field.get_confidence(),
        "sources": [],
        "field_name": field.field_name,
    }

    for source in sources:
        sources_json['sources'].append(extract_source(source))

    return HttpResponse(json.dumps(sources_json), content_type='application/json')


def get_citation(request):
    object_info = request.GET['object_info']

    field_object_name, object_id = object_info.split('_')

    last_dot = field_object_name.rfind('.')
    classname = field_object_name[last_dot + 1:len(field_object_name)]
    module = __import__(field_object_name[0:last_dot],
                        globals(),
                        locals(),
                        [classname])
    field_object_class = getattr(module, classname)
    field_object = field_object_class.objects.get(id=object_id)
    if classname.startswith('Violation'):
        field_object = field_object.object_ref.description.get_value()

    source_html = get_citation_string(field_object)

    return HttpResponse(source_html)


def publication_autocomplete(request):
    term = request.GET.get('q')
    publications = Source.objects.filter(publication__icontains=term).distinct('publication')

    results = []
    for publication in publications:
        results.append({
            'id': publication.publication,
            'text': publication.publication,
            'country': publication.publication_country,
        })

    return HttpResponse(json.dumps(results), content_type='application/json')
