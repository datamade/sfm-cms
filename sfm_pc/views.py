import json
from uuid import uuid4
from collections import OrderedDict, namedtuple

from django.views.generic.base import TemplateView
from django.http import HttpResponse, HttpResponseNotFound
from django.views.generic.edit import FormView
from django.forms import formset_factory
from django.core.exceptions import ObjectDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils.translation import get_language
from django.db import connection
from django.core.urlresolvers import reverse_lazy
from django.conf import settings
from django.contrib.auth.models import User

from reversion.models import Version
from extra_views import FormSetView

from countries_plus.models import Country

from source.models import Source, Publication
from organization.models import Organization, OrganizationAlias, Alias as OAlias
from person.models import Person, PersonAlias, Alias as PAlias
from violation.models import Violation
from membershipperson.models import MembershipPerson
from sfm_pc.templatetags.render_from_source import get_relations, \
    get_relation_attributes
from complex_fields.models import CONFIDENCE_LEVELS
from sfm_pc.utils import import_class, get_osm_by_id
from sfm_pc.forms import MergeForm
from sfm_pc.base_views import UtilityMixin


class Dashboard(TemplateView):
    template_name = 'sfm/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        source_count_q = 'SELECT COUNT(*) AS count, user_id FROM source_source'

        c = connection.cursor()
        c.execute('{} GROUP BY user_id'.format(source_count_q), [])

        for row in c:
            context['count_by_user'] = {
                User.objects.get(id=row[1]): {
                    'all_source_count': row[0],
                },
            }

        c.execute('''
            {} WHERE age(now(), date_added) <= make_interval(weeks := 1)
               GROUP BY user_id
        '''.format(source_count_q), [])

        for row in c:
            user = User.objects.get(id=row[1])
            try:
                context['count_by_user'][user]['last_week_count'] = row[0]
            except KeyError:
                context['count_by_user'][user] = {'last_week_count': row[0]}

        c.execute('''
            {} WHERE age(now(), date_added) <= make_interval(months := 1)
               GROUP BY user_id
        '''.format(source_count_q), [])

        for row in c:
            user = User.objects.get(id=row[1])
            try:
                context['count_by_user'][user]['last_month_count'] = row[0]
            except KeyError:
                context['count_by_user'][user] = {'last_month_count': row[0]}

        entity_type_counts = '''
            SELECT COUNT(*), d.value
            FROM {0}_{0} AS o
            JOIN {0}_{0}divisionid AS d
              ON o.id = d.object_ref_id
            GROUP BY d.value
        '''

        context['counts'] = {}

        for entity_type in ['organization', 'person', 'violation']:
            c.execute(entity_type_counts.format(entity_type), [])

            for row in c:

                try:
                    context['counts'][row[1]][entity_type] = row[0]
                except KeyError:
                    context['counts'][row[1]] = {entity_type: row[0]}

        c.execute('''
            SELECT g.value, array_agg(o.object_ref_id)
            FROM emplacement_emplacementorganization AS o
            JOIN emplacement_emplacement AS e
              ON o.object_ref_id = e.id
            JOIN emplacement_emplacementsite AS s
              ON e.id = s.object_ref_id
            JOIN geosite_geosite AS gs
              ON s.value_id = gs.id
            JOIN geosite_geositeosmid AS g
              ON gs.id = g.object_ref_id
            GROUP BY g.value
            HAVING(COUNT(*)>1)
            ORDER BY COUNT(*) DESC
            LIMIT 5
        ''', [])

        context['org_geo_counts'] = OrderedDict()
        for row in c:
            osm_feature = get_osm_by_id(row[0])
            organizations = [Organization.objects.get(id=i) for i in row[1]]
            context['org_geo_counts'][osm_feature.id] = organizations

        c.execute('''
            SELECT g.value, array_agg(v.id)
            FROM violation_violation AS v
            JOIN violation_violationosmid AS g
              ON v.id = g.object_ref_id
            GROUP BY g.value
            HAVING(COUNT(*)>1)
            ORDER BY COUNT(*) DESC
            LIMIT 5;
        ''')

        context['event_geo_counts'] = OrderedDict()
        for row in c:
            osm_feature = get_osm_by_id(row[0])
            violations = [Violation.objects.get(id=i) for i in row[1]]
            context['event_geo_counts'][osm_feature.id] = violations

        return context

class SetConfidence(TemplateView):
    template_name = 'sfm/set-confidences.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            source_id = self.request.session['source_id']
        except KeyError:
            source_id = self.request.GET['source_id']

        source = Source.objects.get(id=source_id)
        context['source'] = source
        context['relations'] = OrderedDict()

        relation_properties = get_relations(context['source'])

        for rel_prop in relation_properties:
            props = getattr(source, rel_prop).all()

            if props:
                for prop in props:

                    attributes = get_relation_attributes(prop)

                    additional_sources = prop.sources.exclude(id=source_id)
                    for s in additional_sources:
                        revision = Version.objects.get_for_object(s).first()

                        user_data = {}

                        if revision:
                            user_data['user'] = revision.revision.user
                            user_data['source'] = s

                        try:
                            attributes['additional_sources'].append(user_data)
                        except KeyError:
                            attributes['additional_sources'] = [user_data]

                    attributes['relation_id'] = prop.id

                    title = '{0} ({1})'.format(prop.object_ref._meta.object_name,
                                               prop.object_ref.get_value())

                    try:
                        context['relations'][prop.object_ref]['attributes'].append(attributes)
                        context['relations'][prop.object_ref]['title'] = title
                    except KeyError:
                        context['relations'][prop.object_ref] = {
                            'attributes': [attributes],
                            'title': title,
                        }

        context['relations'] = OrderedDict(sorted(context['relations'].items(),
                                           key=lambda x: x[0]._meta.object_name))

        context['confidence_levels'] = CONFIDENCE_LEVELS

        return context

    def post(self, request, *args, **kwargs):

        confidence_keys = [k for k in request.POST.keys() if k.startswith('confidence-')]

        updates = {}
        for key in confidence_keys:
            relation_label, relation_id, object_ref_object, object_ref_id = key.rsplit('-', 3)
            app_name, relation_object = relation_label.replace('confidence-', '').split('.')

            import_path = '{app_name}.models.{obj}'

            relation_path = import_path.format(app_name=app_name,
                                               obj=relation_object)
            relation_model = import_class(relation_path)
            relation_instance = relation_model.objects.get(id=relation_id)

            confidence = int(request.POST[key])
            if relation_instance.confidence != confidence:
                relation_instance.confidence = confidence
                relation_instance.save()

        return redirect(reverse_lazy('dashboard'))

class EntityMergeView(FormView, UtilityMixin):
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

            redirect_url = reverse_lazy('detail_organization', args=[canonical_record_id])

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
                new_alias, created = PAlias.objects.get_or_create(value=record.name.get_value().value)
                palias, created = PersonAlias.objects.get_or_create(value=new_alias,
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


def osm_autocomplete(request):
    term = request.GET.get('q')
    geo_type = request.GET.get('geo_type')

    q_args = [term]

    query = '''
        SELECT
          *,
          ST_X(ST_Centroid(geometry)) AS longitude,
          ST_Y(ST_Centroid(geometry)) AS latitude
        FROM osm_data
        WHERE plainto_tsquery('english', %s) @@ search_index
    '''

    if geo_type:
        query = '{} AND feature_type = %s'.format(query)
        q_args.append(geo_type)

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
            map_image = '{0}?center={1}&zoom=10&size=100x100&key={2}&scale=2'.format(map_image,
                                                                                     latlng,
                                                                                     settings.GOOGLE_MAPS_KEY)
        results.append({
            'text': '{0} (OSM ID: {1})'.format(result.name, result.id),
            'value': result.name,
            'id': result.id,
            'map_image': map_image,
            'type': result.feature_type,
            'admin_level': result.admin_level,
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
