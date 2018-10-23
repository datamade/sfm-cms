# -*- coding: utf-8 -*-

import json
from uuid import uuid4
from collections import OrderedDict, namedtuple
from datetime import datetime

from django.conf import settings
from django.views.generic.base import TemplateView
from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.views.generic.edit import FormView
from django.views.decorators.cache import never_cache
from django.forms import formset_factory
from django.core.exceptions import ObjectDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils.translation import get_language
from django.db import connection
from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, UpdateView

from reversion.models import Version
from extra_views import FormSetView

from countries_plus.models import Country

from organization.models import Organization, OrganizationAlias
from person.models import Person, PersonAlias
from violation.models import Violation
from membershipperson.models import MembershipPerson
from sfm_pc.templatetags.render_from_source import get_relations, \
    get_relation_attributes
from sfm_pc.utils import (import_class, get_osm_by_id, get_org_hierarchy_by_id,
                          get_child_orgs_by_id, Downloader)
from sfm_pc.base_views import UtilityMixin
from search.views import get_search_context


class Dashboard(TemplateView):
    template_name = 'sfm/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Clear form cookies
        form_cookies = [
            'forms',
            'memberships',
            'people',
            'organizations',
            'source_id'
        ]

        for cookie in form_cookies:
            if self.request.session.get(cookie):
                del self.request.session[cookie]

        self.request.session.modified = True

        return context


class Countries(TemplateView):
    template_name = 'sfm/countries.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries_tab'] = 'selected-tab'
        context['conjunta'] = Organization.objects.filter(organizationname__value="Operación Conjunta Chihuahua").first()
        context['boyona'] = Organization.objects.filter(organizationname__value="Operation BOYONA").first()

        return context


class About(TemplateView):
    template_name = 'sfm/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['about_tab'] = 'selected-tab'

        return context


class Help(TemplateView):
    template_name = 'sfm/help.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['help_tab'] = 'selected-tab'

        return context


def country_background(request, country):

    try:
        assert country in ('bangladesh', 'egypt', 'mexico', 'myanmar', 'nigeria', 'philippines', 'rwanda', 'saudiarabia', 'uganda')
    except AssertionError:
        raise Http404()

    template = 'sfm/country-background/{country}.html'.format(country=country)

    return render(request, template)


def osm_autocomplete(request):
    term = request.GET.get('q')
    geo_type = request.GET.get('geo_type')

    # Optional request param to search by OSM ID, instead of by text
    search_by_id = request.GET.get('search_by_id')

    q_args = [term]

    query = '''
        SELECT
          *,
          ST_X(ST_Centroid(geometry)) AS longitude,
          ST_Y(ST_Centroid(geometry)) AS latitude,
          ST_asgeojson(ST_Simplify(geometry, 0.01))::json AS geojson
        FROM osm_data
    '''

    if search_by_id:
        # We want to search for text that begins with the query term, which uses
        # SQL "string%" wildcard syntax. But because of the Django DB API's
        # particular string formatting idiosyncracies, we need to append the %
        # directly to the search term before formatting it into the query.
        q_args[0] += '%%'
        query = "{} WHERE id::text LIKE %s".format(query)
    else:
        query = "{} WHERE plainto_tsquery('english', %s) @@ search_index".format(query)

    if geo_type:
        query = '{} AND feature_type = %s'.format(query)
        q_args.append(geo_type)

    query = '{} LIMIT 10'.format(query)

    cursor = connection.cursor()
    cursor.execute(query, q_args)

    columns = [c[0] for c in cursor.description]
    results_tuple = namedtuple('OSMFeature', columns)

    search_results = [results_tuple(*r) for r in cursor]

    results = []

    for result in search_results:
        map_image = None
        if hasattr(result, 'geometry'):
            latlng = '{0},{1}'.format(result.latitude, result.longitude)
            map_image = 'https://maps.googleapis.com/maps/api/staticmap'
            map_image = '{0}?center={1}&zoom=9&size=100x100&key={2}&scale=2'.format(map_image,
                                                                                     latlng,
                                                                                     settings.GOOGLE_MAPS_KEY)
        results.append({
            'text': '{0} (OSM ID: {1})'.format(result.name, result.id),
            'value': result.name,
            'id': result.id,
            'map_image': map_image,
            'type': result.feature_type.capitalize(),
            'admin_level': result.admin_level,
            'lat': result.latitude,
            'long': result.longitude,
            'geojson': result.geojson,
        })

    results.sort(key=lambda x:x['text'])
    return HttpResponse(json.dumps(results),content_type='application/json')

def division_autocomplete(request):
    term = request.GET.get('q')
    countries = Country.objects.filter(name__icontains=term)

    results = []
    for country in countries:
        results.append({
            'text': '{0} (ocd-division/country:{1})'.format(str(country.name), country.iso.lower()),
            'id': 'ocd-division/country:{}'.format(country.iso.lower()),
        })
    return HttpResponse(json.dumps(results), content_type='application/json')

def command_chain(request, org_id='', when=None, parents=True):

    index = request.GET.get('index', '')

    nodes, edges = [], []

    # Add hierarchy to nodelist and edgelist
    if parents:
        hierarchy_list = get_org_hierarchy_by_id(org_id, when=when)
        from_key, to_key = 'child', 'parent'
    else:
        hierarchy_list = get_org_hierarchy_by_id(org_id, when=when, direction='down')
        from_key, to_key = 'parent', 'child'

    organizations = []

    for composition in hierarchy_list:
        node_fmt = 'composition_{}_id_s_fct'
        for node in ['parent', 'child']:
            label = '<b>{}</b>\n'.format(composition['composition_{}_name_s'.format(node)])

            if when:
                commanders = []
                for commander in composition['commanders-{}'.format(node)]:

                    if not commander['label'] in commanders:
                        label += '{}\n'.format(commander['label'])
                        commanders.append(commander['label'])

            node_key = node_fmt.format(node)
            if not composition[node_key] in organizations:

                trimmed = {
                    'id': composition[node_key],
                    'label': label,
                    'detail_id': composition['composition_{}_id_s'.format(node)],
                    'url': reverse('view-organization', args=[composition['composition_{}_id_s'.format(node)]])
                }
                nodes.append(trimmed)
                organizations.append(composition[node_key])

        edges.append({'from': composition[node_fmt.format(from_key)], 'to': composition[node_fmt.format(to_key)]})

    edgelist = {'nodes': nodes, 'edges': edges, 'index': index}

    return HttpResponse(json.dumps(edgelist), content_type='application/json')

@never_cache
def download_zip(request):
    '''
    Pass the user a ZIP archive of CSVs for a search or record view.
    '''
    entity_type = request.GET.get('download_etype')

    downloader = Downloader(entity_type)

    if request.GET.get('entity_id'):
        entity_ids = [request.GET.get('entity_id')]
    else:
        context = get_search_context(request, all_results=True)

        entities = context['results'][entity_type]
        entity_ids = list(str(entity.uuid) for entity in entities)

    zipout = downloader.get_zip(entity_ids)

    resp = HttpResponse(zipout.getvalue(), content_type='application/zip')

    filedate = datetime.now().strftime('%Y-%m-%d')
    filename = 'attachment; filename=wwic_download_{0}.zip'.format(filedate)

    resp['Content-Disposition'] = filename

    return resp

