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
from sfm_pc.forms import MergeForm
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

class EntityMergeView(LoginRequiredMixin, FormView, UtilityMixin):
    template_name = 'sfm/merge.html'
    form_class = MergeForm
    success_url = reverse_lazy('search')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        entity_ids = self.request.GET['entities'].split(',')
        context['entity_type'] = self.request.GET['entity_type']

        if context['entity_type'] == 'organization':
            context['objects'] = Organization.objects.filter(id__in=entity_ids)
        elif context['entity_type'] == 'person':
            context['objects'] = Person.objects.filter(id__in=entity_ids)

        return context

    def form_valid(self, form):
        response = super().form_valid(form)

        entity_ids = self.request.GET['entities'].split(',')
        entity_type = self.request.GET['entity_type']

        canonical_record_id = form.cleaned_data['canonical_record']

        sub_entity_ids = [i for i in entity_ids if i != canonical_record_id]

        if entity_type == 'organization':
            canonical_record = Organization.objects.get(id=canonical_record_id)

            redirect_url = reverse_lazy('view-organization', args=[canonical_record_id])

            other_records = Organization.objects.filter(id__in=sub_entity_ids)

            for record in other_records:
                # Add other record names as aliases
                new_alias, created = OAlias.objects.get_or_create(value=record.name.get_value().value)
                oalias, created = OrganizationAlias.objects.get_or_create(value=new_alias,
                                                                          object_ref=canonical_record,
                                                                          lang=get_language())
                canonical_record.organizationalias_set.add(oalias)

                # Add aliases
                for alias in record.organizationalias_set.all():
                    canonical_record.organizationalias_set.add(alias)

                # Add classifications
                for classification in record.organizationclassification_set.all():
                    canonical_record.organizationclassification_set.add(classification)

                # Add emplacements
                for emplacement in record.emplacementorganization_set.all():
                    canonical_record.emplacementorganization_set.add(emplacement)

                for membership in record.membershippersonorganization_set.all():
                    canonical_record.membershippersonorganization_set.add(membership)

                # Add associations
                for association in record.associationorganization_set.all():
                    canonical_record.associationorganization_set.add(association)

                # Add compositions
                for child in record.child_organization.all():
                    canonical_record.child_organization.add(child)

                for parent in record.parent_organization.all():
                    canonical_record.parent_organization.add(parent)

                # Add violations
                for violation in record.violationperpetratororganization_set.all():
                    canonical_record.violationperpetratororganization_set.add(violation)

                record.delete()

            canonical_record.save()

        elif entity_type == 'person':
            canonical_record = Person.objects.get(id=canonical_record_id)
            other_records = Person.objects.filter(id__in=sub_entity_ids)

            redirect_url = reverse_lazy('detail-person', args=[canonical_record_id])

            for record in other_records:
                palias, created = PersonAlias.objects.get_or_create(value=record.name.get_value(),
                                                                    object_ref=canonical_record,
                                                                    lang=get_language())
                canonical_record.personalias_set.add(palias)

                for alias in record.personalias_set.all():
                    canonical_record.personalias_set.add(alias)

                canonical_member_orgs = set()
                for membership in canonical_record.membershippersonmember_set.all():
                    for member_org in membership.object_ref.membershippersonorganization_set.all():
                        canonical_member_orgs.add(member_org.value)


                record_member_orgs = set()
                for membership in record.membershippersonmember_set.all():
                    for member_org in membership.object_ref.membershippersonorganization_set.all():
                        record_member_orgs.add(member_org.value)

                new_orgs = record_member_orgs - canonical_member_orgs

                for new_org in new_orgs:
                    mem_data = {
                        'MembershipPerson_MembershipPersonMember': {
                            'value': canonical_record,
                            'confidence': 1,
                            'sources': self.sourcesList(canonical_record, 'name'),
                        },
                        'MembershipPerson_MembershipPersonOrganization': {
                            'value': new_org,
                            'confidence': 1,
                            'sources': self.sourcesList(new_org, 'name'),
                        }
                    }
                    MembershipPerson.create(mem_data)


                for violation in record.violationperpetrator_set.all():
                    canonical_record.violationperpetrator_set.add(violation)

                record.delete()

            canonical_record.save()

        return redirect(redirect_url)


class Countries(TemplateView):
    template_name = 'sfm/countries.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['countries_tab'] = 'selected-tab'

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

    valid_countries = [
        'nigeria',
        'mexico',
        'egypt',
        'bangladesh',
        'myanmar',
        'philippines',
        'rwnada',
        'saudiarabia',
        'uganda',
    ]

    try:
        assert country in valid_countries
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
                    'detail_id': composition['composition_{}_pk_i'.format(node)],
                    'url': reverse('view-organization', args=[composition['composition_{}_pk_i'.format(node)]])
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

