import re
import zipfile
import json
from io import BytesIO

import requests

from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView, DeleteView, TemplateView
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q

from countries_plus.models import Country

from sfm_pc.templatetags.countries import country_name
from sfm_pc.base_views import BaseDeleteView, JSONResponseMixin

from .models import Location
from .forms import LocationForm

class OverpassException(Exception):
    def __init__(self, status_code):
        self.status_code = status_code

    @property
    def message(self):
        if 400 < self.status_code < 500:
            return 'Could not find that relation in Overpass'
        elif 500 < self.status_code:
            return 'Overpass returned an error. Try again later.'


class LocationView(LoginRequiredMixin, DetailView):
    model = Location
    template_name = 'location/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        location = context['location']
        context['related_entities'] = location.related_entities

        return context


class LocationDelete(BaseDeleteView):
    model = Location
    success_url = reverse_lazy('list-location')
    template_name = 'location/delete.html'

    def get_cancel_url(self):
        return reverse_lazy('view-location', kwargs={'pk': self.kwargs['pk']})

    def get_related_entities(self):
        return self.object.related_entities


class LocationCreate(LoginRequiredMixin, CreateView):
    form_class = LocationForm
    template_name = 'location/create.html'

    def get_success_url(self):
        return reverse('view-location', kwargs={'pk' : self.object.id})

    def queryOverpass(self, location_type, location_id):
        # search by location ID
        query_fmt = '[out:json];{location_type}({location_id});(._;>;);out;'

        overpass_endpoint = 'https://overpass.kumi.systems/api/interpreter'

        post_data = {
            'data': query_fmt.format(location_type=location_type,
                                     location_id=location_id)
        }

        response = requests.post(overpass_endpoint, data=post_data)

        if response.status_code != 200:
            elements = {
                'elements': [],
            }
        else:
            elements = response.json()

        all_ids = []

        if location_type == 'node':

            nodes = [e for e in elements['elements'] if e['type'] == 'node']
            all_ids.extend([f['id'] for f in nodes])

        if location_type == 'way':
            ways = [e for e in elements['elements'] if e['type'] == 'way']
            all_ids.extend([f['id'] for f in ways])

        if location_type == "relation":
            relations = [e for e in elements['elements'] if e['type'] == 'relation']
            all_ids.extend([f['id'] for f in relations])

        saved_location_ids = [l.id for l in Location.objects.filter(id__in=all_ids)]

        for feature in elements['elements']:

            if feature['type'] == location_type:
                feature['tags'] = feature.get('tags', {})
                feature['tags']['saved'] = 'no'

                if int(feature['id']) in saved_location_ids:
                    feature['tags']['saved'] = 'yes'

                feature['form_tags'] = json.dumps(feature['tags'])

        return elements

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = Country.objects.all()

        if self.request.method == 'GET':
            location_type = self.request.GET.get('location_type')
            location_id = self.request.GET.get('location_id')

            if location_id and location_type:
                context['features'] = self.queryOverpass(location_type,
                                                         location_id)
                context['json_features'] = json.dumps(context['features'])
                context['feature_count'] = len(context['features']['elements'])

                context['location_type'] = location_type
                try:
                    context['location_id'] = int(location_id)
                except ValueError:
                    context['location_id'] = location_id

        return context


class LocationList(LoginRequiredMixin, ListView):
    model = Location
    template_name = 'location/list.html'
    per_page = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['results'] = Location.objects.order_by('name')

        context['feature_type_facets'] = {
            'node': 0,
            'relation': 0,
            'way': 0
        }

        if self.request.method == 'GET':
            query = self.request.GET.get('q')
            sort = self.request.GET.get('sort')
            page = self.request.GET.get('page', default=1)
            feature_type = self.request.GET.get('feature_type')

            if query:
                context['results'] = Location.objects.filter(Q(name__icontains=query) | Q(id__startswith=query))
                context['query'] = query
                context['feature_type_facets']['node'] = context['results'].filter(feature_type='node').count()
                context['feature_type_facets']['relation'] = context['results'].filter(feature_type='relation').count()
                context['feature_type_facets']['way'] = context['results'].filter(feature_type='way').count()

            if feature_type:
                context['results'] = context['results'].filter(feature_type=feature_type)

            if sort:
                context['results'] = context['results'].order_by(sort)
                context['sort'] = sort

            paginator = Paginator(context['results'], self.per_page)
            context['page'] = int(page)
            context['pages'] = int(paginator.num_pages)

            try:
                context['results'] = paginator.page(page)
            except PageNotAnInteger:
                context['results'] = paginator.page(1)
            except EmptyPage:
                context['results'] = paginator.page(paginator.num_pages)

        context['paginator'] = paginator
        context['hits'] = paginator.count
        return context


class LocationAutoComplete(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        query = self.request.GET.get('q')

        results = Location.objects.filter(Q(name__icontains=query) | Q(id__startswith=query))

        if self.request.GET.get('feature_type'):
            feature_type = self.request.GET['feature_type']
            results = results.filter(feature_type=feature_type)

        context = {
            'results': []
        }

        for result in results[:10]:
            location = {
                'id': result.id,
                'text': '{}, {} ({} - {})'.format(result.name,
                                                  country_name(result.division_id),
                                                  result.feature_type,
                                                  result.id),
                'geometry': json.loads(result.geometry.simplify(tolerance=0.01).geojson),
            }
            context['results'].append(location)

        return context
