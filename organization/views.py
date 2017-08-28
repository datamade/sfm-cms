import json

from django.contrib import messages
from django.views.generic import DetailView
from django.http import HttpResponse
from django.db import connection
from django.utils.translation import get_language
from django.core.urlresolvers import reverse_lazy
from complex_fields.models import CONFIDENCE_LEVELS

from source.models import Source
from geosite.models import Geosite
from emplacement.models import Emplacement
from area.models import Area
from association.models import Association
from organization.forms import OrganizationForm, OrganizationGeographyForm
from organization.models import Organization, OrganizationAlias, Alias, \
    OrganizationClassification, Classification

from sfm_pc.utils import get_osm_by_id, get_hierarchy_by_id
from sfm_pc.base_views import BaseFormSetView, BaseUpdateView, PaginatedList


class OrganizationDetail(DetailView):
    model = Organization
    template_name = 'organization/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['person_members'] = []
        memberships = context['organization'].membershippersonorganization_set.all()
        for membership in memberships:
            context['person_members'].append(membership.object_ref)

        context['events'] = []
        events = context['organization'].violationperpetratororganization_set.all()
        for event in events:
            context['events'].append(event.object_ref)

        context['sites'] = []
        emplacements = context['organization'].emplacementorganization_set.all()
        for emplacement in emplacements:
            if emplacement.object_ref.site.get_value().value.osmid.get_value():
                context['sites'].append(emplacement.object_ref.site.get_value().value)

        context['areas'] = []
        associations = context['organization'].associationorganization_set.all()
        for association in associations:
            if association.object_ref.area.get_value().value.osmid.get_value():
                context['areas'].append(association.object_ref.area.get_value().value)

        context['parents'] = []
        parents = context['organization'].parent_organization.all()
        for parent in parents:
            context['parents'].append(parent.object_ref.parent.get_value().value)

        context['subsidiaries'] = []
        children = context['organization'].child_organization.all()
        for child in children:
            context['subsidiaries'].append(child.object_ref.child.get_value().value)

        member_of_orgs = '''
            SELECT
              org_o.id,
              MAX(org.name) AS name,
              array_agg(DISTINCT TRIM(org.alias))
                FILTER (WHERE TRIM(org.alias) IS NOT NULL) AS aliases,
              array_agg(DISTINCT TRIM(org.classification))
                FILTER (WHERE TRIM(org.classification) IS NOT NULL) AS classifications,
              MAX(mo.first_cited) AS first_cited,
              MAX(mo.last_cited) AS last_cited
            FROM membershiporganization AS mo
            JOIN organization AS member
              ON mo.member_id = member.id
            JOIN organization_organization AS member_o
              ON member.id = member_o.uuid
            JOIN organization AS org
              ON mo.organization_id = org.id
            JOIN organization_organization AS org_o
              ON org.id = org_o.uuid
            WHERE member_o.id = %s
            GROUP BY org_o.id
        '''

        cursor = connection.cursor()
        cursor.execute(member_of_orgs, [self.kwargs['pk']])

        columns = [c[0] for c in cursor.description]

        context['memberships'] = [dict(zip(columns, r)) for r in cursor]

        org_members = '''
            SELECT
              member_o.id,
              MAX(member.name) AS name,
              array_agg(DISTINCT TRIM(member.alias))
                FILTER (WHERE TRIM(member.alias) IS NOT NULL) AS aliases,
              array_agg(DISTINCT TRIM(member.classification))
                FILTER (WHERE TRIM(member.classification) IS NOT NULL) AS classifications,
              MAX(mo.first_cited) AS first_cited,
              MAX(mo.last_cited) AS last_cited
            FROM membershiporganization AS mo
            JOIN organization AS member
              ON mo.member_id = member.id
            JOIN organization_organization AS member_o
              ON member.id = member_o.uuid
            JOIN organization AS org
              ON mo.organization_id = org.id
            JOIN organization_organization AS org_o
              ON org.id = org_o.uuid
            WHERE org_o.id = %s
            GROUP BY member_o.id
        '''

        cursor.execute(org_members, [self.kwargs['pk']])

        columns = [c[0] for c in cursor.description]

        context['org_members'] = [dict(zip(columns, r)) for r in cursor]

        return context


class OrganizationList(PaginatedList):
    model = Organization
    template_name = 'organization/list.html'
    orderby_lookup = {
        'name': 'organizationname__value',
        'parent': 'parent_organization__object_ref__compositionparent__value__organizationname__value',
        'osmname': 'emplacementorganization__object_ref__emplacementsite__value__geositeosmname__value',
        'admin1': 'emplacementorganization__object_ref__emplacementsite__value__geositeadminlevel1__value',
        'classification': 'organizationclassification__value__value'
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Highlight the correct nav tab in the template
        context['organization_tab'] = 'selected-tab'
        context['search_term'] = 'a unit'
        return context


class OrganizationCreate(BaseFormSetView):
    template_name = 'organization/create.html'
    form_class = OrganizationForm
    success_url = reverse_lazy('create-composition')
    extra = 1
    max_num = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confidence_levels'] = CONFIDENCE_LEVELS

        context['source'] = Source.objects.get(id=self.request.session['source_id'])

        context['back_url'] = reverse_lazy('create-source')
        context['skip_url'] = reverse_lazy('create-person')

        return context

    def post(self, request, *args, **kwargs):

        form_data = {}

        for key, value in request.POST.items():
            if 'alias' in key or 'classification' in key:
                form_data[key] = request.POST.getlist(key)
            else:
                form_data[key] = request.POST.get(key)

        self.initFormset(form_data)

        return self.validateFormSet()

    def formset_invalid(self, formset):
        response = super().formset_invalid(formset)

        for index, form in enumerate(formset.forms):
            alias_ids = formset.data.get('form-{}-alias'.format(index))
            classification_ids = formset.data.get('form-{}-classification'.format(index))

            form.aliases = []
            form.classifications = []

            if alias_ids:

                actual_ids = []

                for alias_id in alias_ids:
                    try:
                        actual_ids.append(int(alias_id))
                    except ValueError:
                        pass

                form.aliases = OrganizationAlias.objects.filter(id__in=actual_ids)

            if classification_ids:
                form.classifications = OrganizationClassification.objects.filter(id__in=classification_ids)

        return response

    def formset_valid(self, formset):
        forms_added = int(formset.data['form-FORMS_ADDED'][0])

        self.organizations = []

        self.source = Source.objects.get(id=self.request.session['source_id'])

        actual_form_index = 0

        for i in range(0, forms_added):

            form_prefix = 'form-{}-'.format(i)

            name_id_key = 'form-{}-name'.format(i)
            name_text_key = 'form-{}-name_text'.format(i)
            name_confidence_key = 'form-{}-name_confidence'.format(i)

            division_id_key = 'form-{}-division_id'.format(i)
            division_confidence_key = 'form-{}-division_confidence'.format(i)

            classification_confidence_key = 'form-{}-classification_confidence'.format(i)

            try:
                name_id = formset.data[name_id_key]
            except KeyError:
                continue

            name_text = formset.data[name_text_key]
            name_confidence = formset.data.get(name_confidence_key, 1)

            division_id = formset.data[division_id_key]
            division_confidence = formset.data.get(division_confidence_key, 1)

            org_info = {
                'Organization_OrganizationName': {
                    'value': name_text,
                    'confidence': name_confidence,
                    'sources': [self.source]
                },
                'Organization_OrganizationDivisionId': {
                    'value': division_id,
                    'confidence': division_confidence,
                    'sources': [self.source],
                }
            }

            try:
                organization = Organization.objects.get(id=name_id)
                sources = self.sourcesList(organization, 'name')

                org_info["Organization_OrganizationName"]['sources'] = sources

            except (Organization.DoesNotExist, ValueError):
                organization = Organization.create(org_info)

            organization.update(org_info)

            # Save aliases first

            aliases = formset.data.get(form_prefix + 'alias_text')

            if aliases:

                alias_confidence_key = 'form-{}-alias_confidence'.format(i)
                alias_confidence = formset.data.get(alias_confidence_key, 1)

                for alias in aliases:

                    alias_obj, created = Alias.objects.get_or_create(value=alias)

                    oa_obj, created = OrganizationAlias.objects.get_or_create(value=alias_obj,
                                                                              object_ref=organization,
                                                                              lang=get_language(),
                                                                              confidence=alias_confidence)
                    oa_obj.sources.add(self.source)
                    oa_obj.save()

            # Next do classifications

            classifications = formset.data.get(form_prefix + 'classification_text')

            if classifications:

                classification_confidence_key = 'form-{}-classification_confidence'.format(i)
                classification_confidence = formset.data.get(classification_confidence_key, 1)

                for classification in classifications:

                    class_obj, created = Classification.objects.get_or_create(value=classification)

                    oc_obj, created = OrganizationClassification.objects.get_or_create(value=class_obj,
                                                                                       object_ref=organization,
                                                                                       lang=get_language(),
                                                                                       confidence=classification_confidence)
                    oc_obj.sources.add(self.source)
                    oc_obj.save()

            self.organizations.append(organization)

            actual_form_index += 1

        self.request.session['organizations'] = [{'id': o.id, 'name': o.name.get_value().value}
                                                 for o in self.organizations]

        response = super().formset_valid(formset)

        return response


class OrganizationUpdate(BaseUpdateView):
    template_name = 'organization/edit.html'
    form_class = OrganizationForm
    success_url = reverse_lazy('dashboard')
    sourced = True

    def post(self, request, *args, **kwargs):

        self.checkSource(request)

        self.aliases = request.POST.getlist('alias')
        self.classifications = request.POST.getlist('classification')

        return self.validateForm()

    def form_valid(self, form):
        response = super().form_valid(form)

        organization = Organization.objects.get(pk=self.kwargs['pk'])

        org_info = {
            'Organization_OrganizationName': {
                'value': form.cleaned_data['name_text'],
                'confidence': 1,
                'sources': self.sourcesList(organization, 'name'),
            },
            'Organization_OrganizationDivisionId': {
                'value': form.cleaned_data['division_id'],
                'confidence': 1,
                'sources': self.sourcesList(organization, 'division_id'),
            },
        }

        organization.update(org_info)

        if self.aliases:

            aliases = []

            for alias in self.aliases:

                try:
                    # try to get an object based on ID
                    oa_obj = OrganizationAlias.objects.get(id=alias)
                    oa_obj.sources.add(self.source)
                    oa_obj.save()

                    aliases.append(oa_obj)
                except ValueError:
                    alias_obj, created = Alias.objects.get_or_create(value=alias)

                    oa_obj = OrganizationAlias.objects.create(value=alias_obj,
                                                              object_ref=organization,
                                                              lang=get_language())
                    oa_obj.sources.add(self.source)
                    oa_obj.save()

                    aliases.append(oa_obj)

            organization.organizationalias_set = aliases
            organization.save()

        if self.classifications:

            classifications = []
            for classification in self.classifications:

                class_obj, created = Classification.objects.get_or_create(value=classification)

                oc_obj, created = OrganizationClassification.objects.get_or_create(value=class_obj,
                                                                                   object_ref=organization,
                                                                                   lang=get_language())
                oc_obj.sources.add(self.source)
                oc_obj.save()

                classifications.append(oc_obj)

            organization.organizationclassification_set = classifications
            organization.save()

        messages.add_message(self.request,
                             messages.INFO,
                             'Organization {} saved!'.format(form.cleaned_data['name_text']))

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        organization = Organization.objects.get(pk=self.kwargs['pk'])

        form_data = {
            'name': organization.name.get_value(),
            'classification': [i.get_value() for i in organization.classification.get_list()],
            'alias': [i.get_value() for i in organization.aliases.get_list()],
            'division_id': organization.division_id.get_value(),
        }

        context['form_data'] = form_data
        context['title'] = 'Organization'
        context['source_object'] = organization
        context['source'] = Source.objects.filter(id=self.request.GET.get('source_id')).first()

        if not self.sourced:
            context['source_error'] = 'Please include the source for your changes'

        return context


def classification_autocomplete(request):
    term = request.GET.get('q')

    classifications = '''
        SELECT DISTINCT TRIM(value) AS value
    '''

    classifications = Classification.objects.filter(value__icontains=term).all()

    results = []
    for classification in classifications:
        results.append({
            'text': classification.value,
            'id': classification.id,
        })

    return HttpResponse(json.dumps(results), content_type='application/json')


def organization_autocomplete(request):
    term = request.GET.get('q')
    organizations = Organization.objects.filter(organizationname__value__icontains=term).all()

    results = []
    for organization in organizations:
        results.append({
            'text': str(organization.name),
            'id': organization.id,
        })
    return HttpResponse(json.dumps(results), content_type='application/json')


def alias_autocomplete(request):
    term = request.GET.get('q')
    alias_query = OrganizationAlias.objects.filter(value__value__icontains=term)
    results = []
    for alias in alias_query:
        results.append({
            'text': alias.value.value,
            'id': alias.id
        })
    return HttpResponse(json.dumps(results), content_type='application/json')


class OrganizationCreateGeography(BaseFormSetView):
    template_name = 'organization/create-geography.html'
    form_class = OrganizationGeographyForm
    success_url = reverse_lazy('create-event')
    extra = 1
    max_num = None
    required_session_data = ['organizations']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confidence_levels'] = CONFIDENCE_LEVELS

        organizations = self.request.session['organizations']

        context['organizations'] = organizations
        context['source'] = Source.objects.get(id=self.request.session['source_id'])

        form = self.form_class()
        context['geo_types'] = form.fields['geography_type'].choices

        return context

    def formset_valid(self, formset):
        source = Source.objects.get(id=self.request.session['source_id'])
        num_forms = int(formset.data['form-TOTAL_FORMS'][0])

        for i in range(0, num_forms):
            form_prefix = 'form-{0}-'.format(i)

            org_id = formset.data[form_prefix + 'org']
            geoid = formset.data[form_prefix + 'osm_id']

            geo = get_osm_by_id(geoid)
            hierarchy = get_hierarchy_by_id(geoid)

            admin1 = None
            admin2 = None

            if hierarchy:
                for member in hierarchy:
                    if member.admin_level == 6:
                        admin1 = member.name
                    elif member.admin_level == 4:
                        admin2 = member.name

            coords = getattr(geo, 'geometry')
            country_code = geo.country_code.lower()

            division_id = 'ocd-division/country:{}'.format(country_code)

            if formset.data[form_prefix + 'geography_type'] == 'Site':

                site, created = Geosite.objects.get_or_create(geositeosmid__value=geo.id)

                names = [
                    formset.data[form_prefix + 'name'],
                    geo.name,
                    admin1,
                ]

                name = ', '.join([n for n in names if n])

                site_data = {
                    'Geosite_GeositeName': {
                        'value': name,
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Geosite_GeositeOSMName': {
                        'value': geo.name,
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Geosite_GeositeOSMId': {
                        'value': geo.id,
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Geosite_GeositeDivisionId': {
                        'value': division_id,
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Geosite_GeositeAdminLevel1': {
                        'value': admin1,
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Geosite_GeositeAdminLevel2': {
                        'value': admin2,
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Geosite_GeositeCoordinates': {
                        'value': coords,
                        'confidence': 1,
                        'sources': [source]
                    }
                }
                site.update(site_data)

                emp, created = Emplacement.objects.get_or_create(emplacementorganization__value=org_id,
                                                                 emplacementsite__value=site.id)
                emp_data = {
                    'Emplacement_EmplacementOrganization': {
                        'value': Organization.objects.get(id=org_id),
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Emplacement_EmplacementSite': {
                        'value': site,
                        'confidence': 1,
                        'sources': [source]
                    },
                }

                if formset.data[form_prefix + 'startdate']:
                    emp_data['Emplacement_EmplacementStartDate'] = {
                        'value': formset.data[form_prefix + 'startdate'],
                        'confidence': 1,
                        'sources': [source]
                    }

                if formset.data[form_prefix + 'enddate']:
                    emp_data['Emplacement_EmplacementEndDate'] = {
                        'value': formset.data[form_prefix + 'enddate'],
                        'confidence': 1,
                        'sources': [source]
                    }

                emp.update(emp_data)

            else:

                area, created = Area.objects.get_or_create(areaosmid__value=geo.id)

                if created:

                    area_data = {
                        'Area_AreaName': {
                            'value': formset.data[form_prefix + 'name'],
                            'confidence': 1,
                            'sources': [source]
                        },
                        'Area_AreaOSMName': {
                            'value': geo.name,
                            'confidence': 1,
                            'sources': [source]
                        },
                        'Area_AreaOSMId': {
                            'value': geo.id,
                            'confidence': 1,
                            'sources': [source]
                        },
                        'Area_AreaDivisionId': {
                            'value': division_id,
                            'confidence': 1,
                            'sources': [source]
                        },
                        'Area_AreaGeometry': {
                            'value': geo.geometry,
                            'confidence': 1,
                            'sources': [source]
                        }
                    }
                    area.update(area_data)

                assoc, created = Association.objects.get_or_create(associationorganization__value=org_id,
                                                                   associationarea__value=area.id)

                assoc_data = {
                    'Association_AssociationStartDate': {
                        'value': formset.data[form_prefix + 'startdate'],
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Association_AssociationEndDate': {
                        'value': formset.data[form_prefix + 'enddate'],
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Association_AssociationOrganization': {
                        'value': Organization.objects.get(id=org_id),
                        'confidence': 1,
                        'sources': [source]
                    },
                    'Association_AssociationArea': {
                        'value': area,
                        'confidence': 1,
                        'sources': [source]
                    }
                }
                assoc.update(assoc_data)

        response = super().formset_valid(formset)

        return response
