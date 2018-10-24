import json

from django.contrib import messages
from django.views.generic import DetailView
from django.http import HttpResponse
from django.db import connection
from django.utils.translation import get_language
from django.core.urlresolvers import reverse_lazy, reverse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from source.models import Source
from geosite.models import Geosite
from emplacement.models import Emplacement
from area.models import Area
from association.models import Association
from organization.forms import (OrganizationForm, OrganizationGeographyForm,
                                BaseOrganizationFormSet)
from organization.models import Organization, OrganizationAlias, \
    OrganizationClassification

from sfm_pc.utils import (get_osm_by_id, get_hierarchy_by_id,
                          get_org_hierarchy_by_id,  get_command_edges,
                          get_command_nodes, Autofill)
from sfm_pc.base_views import BaseFormSetView, BaseUpdateView, PaginatedList


class OrganizationDetail(DetailView):
    model = Organization
    template_name = 'organization/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Generate link to download a CSV of this record
        params = '?download_etype=Organization&entity_id={0}'.format(str(context['organization'].uuid))

        context['download_url'] = reverse('download') + params

        # Commanders of this unit
        context['person_members'] = []
        person_members = context['organization'].membershippersonorganization_set.all()
        for membership in person_members:
            context['person_members'].append(membership.object_ref)

        # Organizational members of this unit
        context['org_members'] = []
        org_members = context['organization'].membershiporganizationorganization_set.all()
        if org_members:
            org_members = (mem.object_ref for mem in org_members)
            context['org_members'] = org_members

        # Other units that this unit is a member of
        context['memberships'] = []
        memberships = context['organization'].membershiporganizationmember_set.all()
        if memberships:
            memberships = (mem.object_ref for mem in memberships)
            context['memberships'] = memberships

        # Child units
        context['subsidiaries'] = []
        children = context['organization'].child_organization.all()
        for child in children:
            context['subsidiaries'].append(child.object_ref)

        # Incidents that this unit perpetrated
        context['events'] = []
        events = context['organization'].violationperpetratororganization_set.all()
        for event in events:
            context['events'].append(event.object_ref)

        context['sites'] = []
        emplacements = tuple(context['organization'].emplacements)
        context['emplacements'] = (em.object_ref for em in emplacements)
        for emplacement in emplacements:
            if emplacement.object_ref.site.get_value().value.admin_id.get_value():
                context['sites'].append(emplacement.object_ref.site.get_value().value)

        context['areas'] = []
        associations = tuple(context['organization'].associations)
        context['associations'] = (ass.object_ref for ass in associations)
        for association in associations:
            if association.object_ref.area.get_value().value.osmid.get_value():
                geom = association.object_ref.area.get_value().value.geometry
                area = geom.get_value().value.simplify(tolerance=0.01)
                area_obj = {
                    'geom': area,
                    'name': association.object_ref.area.get_value().value.osmname.get_value()
                }
                context['areas'].append(area_obj)

        context['parents'] = []
        context['parents_list'] = []
        parents = context['organization'].parent_organization.all()
        # "parent" is a CompositionChild
        for parent in parents:

            context['parents'].append(parent.object_ref.parent.get_value().value)

            org_data = {'when': '', 'url': ''}

            when = None
            if parent.object_ref.enddate.get_value():
                # Make the query using the raw date string, to accomodate
                # fuzzy dates
                when = repr(parent.object_ref.enddate.get_value().value)
                org_data['when'] = when

                # Display a formatted date
                org_data['display_date'] = str(parent.object_ref.enddate.get_value())

            kwargs = {'org_id': str(context['organization'].uuid)}
            ajax_route = 'command-chain'
            if when:
                kwargs['when'] = when
                ajax_route = 'command-chain-bounded'

            command_chain_url = reverse(ajax_route, kwargs=kwargs)

            org_data['url'] = command_chain_url

            context['parents_list'].append(org_data)

        context['versions'] = context['organization'].getVersions()

        return context


class OrganizationList(PaginatedList):
    model = Organization
    template_name = 'organization/list.html'
    orderby_lookup = {
        'name': 'organizationname__value',
        'parent': 'parent_organization__object_ref__compositionparent__value__organizationname__value',
        'osmname': 'emplacementorganization__object_ref__emplacementsite__value__geositeadminname__value',
        'admin1': 'emplacementorganization__object_ref__emplacementsite__value__geositeadminlevel1__value',
        'classification': 'organizationclassification__value__value'
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Highlight the correct nav tab in the template
        context['organization_tab'] = 'selected-tab'
        context['search_term'] = 'a unit'
        return context


class OrganizationCreate(LoginRequiredMixin, BaseFormSetView):
    template_name = 'organization/create.html'
    form_class = OrganizationForm
    formset_class = BaseOrganizationFormSet
    success_url = reverse_lazy('create-composition')
    extra = 1
    max_num = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['confidence_levels'] = settings.CONFIDENCE_LEVELS
        context['open_ended_choices'] = settings.OPEN_ENDED_CHOICES

        context['classifications'] = Classification.objects.all()
        context['source'] = Source.objects.get(uuid=self.request.session['source_id'])

        context['back_url'] = reverse_lazy('create-source')
        context['skip_url'] = reverse_lazy('create-person')

        existing_forms = self.request.session.get('forms', {})

        if existing_forms and existing_forms.get('organizations') and not getattr(self, 'formset', False):

            form_data = existing_forms.get('organizations')
            self.initFormset(form_data)

            context['formset'] = self.get_formset_context(self.formset)
            context['browsing'] = True

        return context

    def post(self, request, *args, **kwargs):

        form_data = {}

        for key, value in request.POST.items():
            if ('alias' in key or 'classification' in key) and 'confidence' not in key:
                form_data[key] = request.POST.getlist(key)
            else:
                form_data[key] = request.POST.get(key)

        self.initFormset(form_data)

        return self.validateFormSet()

    def get_formset_context(self, formset):

        for index, form in enumerate(formset.forms):

            alias_ids = form.data.get('form-{}-alias'.format(index))
            classification_ids = form.data.get('form-{}-classification'.format(index))

            form.aliases = []
            form.classifications = []

            if alias_ids:

                for alias_id in alias_ids:
                    try:
                        alias_id = int(alias_id)
                        alias = OrganizationAlias.objects.get(id=alias_id)
                    except ValueError:
                        alias = {'id': alias_id, 'value': alias_id}
                    form.aliases.append(alias)

            if classification_ids:

                form.classifications = [int(class_id) for class_id in classification_ids]

        return formset

    def formset_invalid(self, formset):

        formset = self.get_formset_context(formset)

        response = super().formset_invalid(formset)
        return response

    def formset_valid(self, formset):
        forms_added = int(formset.data['form-FORMS_ADDED'][0])

        self.organizations = []

        self.source = Source.objects.get(uuid=self.request.session['source_id'])

        actual_form_index = 0

        for i in range(0, forms_added):

            form_prefix = 'form-{}-'.format(i)

            # Name, division, and headquarters
            name_id = formset.data.get(form_prefix + 'name')
            name_text = formset.data.get(form_prefix + 'name_text')
            name_confidence = int(formset.data.get(form_prefix +
                                                   'name_confidence', 1))

            division_id = formset.data.get(form_prefix + 'division_id')
            division_confidence = int(formset.data.get(form_prefix +
                                                       'division_confidence', 1))

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

            # Headquarters
            headquarters = formset.data.get(form_prefix + 'headquarters')

            if headquarters:

                headquarters_confidence = int(formset.data.get(form_prefix +
                                                               'headquarters_confidence', 1))

                org_info['Organization_OrganizationHeadquarters'] = {
                    'value': headquarters,
                    'confidence': headquarters_confidence,
                    'sources': [self.source]
                }

            # Dates
            firstciteddate = formset.data.get(form_prefix + 'firstciteddate')
            realstart = formset.data.get(form_prefix + 'realstart')

            if realstart:
                realstart = True

            lastciteddate = formset.data.get(form_prefix + 'lastciteddate')
            open_ended = formset.data.get(form_prefix + 'open_ended', 'N')

            firstciteddate_confidence = int(formset.data.get(form_prefix +
                                                              'firstciteddate_confidence', 1))
            lastciteddate_confidence = int(formset.data.get(form_prefix +
                                                            'lastciteddate_confidence', 1))

            if firstciteddate:

                org_info['Organization_OrganizationFirstCitedDate'] = {
                    'value': firstciteddate,
                    'confidence': firstciteddate_confidence,
                    'sources': [self.source]
                }

                if realstart:

                    org_info['Organization_OrganizationRealStart'] = {
                        'value': realstart,
                        'confidence': firstciteddate_confidence,
                        'sources': [self.source]
                    }

            if lastciteddate:

                org_info['Organization_OrganizationLastCitedDate'] = {
                    'value': lastciteddate,
                    'confidence': lastciteddate_confidence,
                    'sources': [self.source]
                }

            org_info['Organization_OrganizationOpenEnded'] = {
                'value': open_ended,
                'confidence': lastciteddate_confidence,
                'sources': [self.source]
            }

            try:
                organization = Organization.objects.get(id=name_id)

                name_sources = self.sourcesList(organization, 'name')
                division_sources = self.sourcesList(organization, 'division_id')

                org_info["Organization_OrganizationName"]['sources'] = name_sources
                org_info["Organization_OrganizationDivisionId"]['sources'] = division_sources

                if headquarters:
                    headquarters_sources = self.sourcesList(organization, 'headquarters')
                    org_info["Organization_OrganizationHeadquarters"]['sources'] = headquarters_sources

                if firstciteddate:
                    firstciteddate_sources = self.sourcesList(organization, 'firstciteddate')
                    org_info["Organization_OrganizationFirstCitedDate"]['sources'] = firstciteddate_sources

                if realstart:
                    realstart_sources = self.sourcesList(organization, 'realstart')
                    org_info["Organization_OrganizationRealStart"]['sources'] = realstart_sources

                if lastciteddate:
                    lastciteddate_sources = self.sourcesList(organization, 'lastciteddate')
                    org_info["Organization_OrganizationLastCitedDate"]['sources'] = lastciteddate_sources

                if open_ended:
                    open_ended_sources = self.sourcesList(organization, 'open_ended')
                    org_info["Organization_OrganizationOpenEnded"]['sources'] = open_ended_sources

            except (Organization.DoesNotExist, ValueError):
                organization = Organization.create(org_info)

            organization.update(org_info)
            formset.data[form_prefix + 'name'] = organization.id

            # Aliases
            aliases = formset.data.get(form_prefix + 'alias')

            if aliases:

                alias_confidence = int(formset.data.get(form_prefix +
                                                        'alias_confidence', 1))

                for alias in aliases:

                    try:
                        # If the `value` property is a string, the alias is new
                        alias_id = int(alias)
                        oa_obj = OrganizationAlias.objects.get(id=alias_id)

                    except ValueError:
                        alias_obj, created = Alias.objects.get_or_create(value=alias)

                        oa_obj, created = OrganizationAlias.objects.get_or_create(value=alias_obj,
                                                                                  object_ref=organization,
                                                                                  lang=get_language())
                    oa_obj.sources.add(self.source)
                    oa_obj.confidence = alias_confidence
                    oa_obj.save()

            # Classifications
            classifications = formset.data.get(form_prefix + 'classification')

            if classifications:

                classification_confidence = int(formset.data.get(form_prefix +
                                                                 'classification_confidence', 1))

                for classification in classifications:

                    class_obj, created = Classification.objects.get_or_create(id=int(classification))

                    oc_obj, created = OrganizationClassification.objects.get_or_create(value=class_obj,
                                                                                       object_ref=organization,
                                                                                       lang=get_language())
                    oc_obj.sources.add(self.source)
                    oc_obj.confidence = classification_confidence
                    oc_obj.save()

            self.organizations.append(organization)

            # Queue up to be added to search index
            to_index = self.request.session.get('index')

            if not to_index:
                self.request.session['index'] = {}

            self.request.session['index'][str(organization.uuid)] = 'organizations'

            actual_form_index += 1

        self.request.session['organizations'] = [{'id': o.id, 'name': o.name.get_value().value}
                                                 for o in self.organizations]

        response = super().formset_valid(formset)

        if not self.request.session.get('forms'):
            self.request.session['forms'] = {}

        self.request.session['forms']['organizations'] = formset.data
        self.request.session.modified = True

        return response


class OrganizationUpdate(LoginRequiredMixin, BaseUpdateView):
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
        context['source'] = Source.objects.filter(uuid=self.request.GET.get('source_id')).first()

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

    simple_attrs = [
        'headquarters',
        'firstciteddate',
        'realstart',
        'lastciteddate',
        'open_ended'
    ]

    complex_attrs = ['division_id']

    list_attrs = ['aliases', 'classification']

    autofill = Autofill(objects=organizations,
                        simple_attrs=simple_attrs,
                        complex_attrs=complex_attrs,
                        list_attrs=list_attrs)

    attrs = autofill.attrs

    return HttpResponse(json.dumps(attrs), content_type='application/json')


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


class OrganizationCreateGeography(LoginRequiredMixin, BaseFormSetView):
    template_name = 'organization/create-geography.html'
    form_class = OrganizationGeographyForm
    success_url = reverse_lazy('create-event')
    extra = 1
    max_num = None
    required_session_data = ['organizations']

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['confidence_levels'] = settings.CONFIDENCE_LEVELS
        context['open_ended_choices'] = settings.OPEN_ENDED_CHOICES

        organizations = self.request.session['organizations']
        memberships = self.request.session.get('memberships', [])

        if len(memberships):
            context['back_url'] = reverse_lazy('create-membership')
            context['skip_url'] = reverse_lazy('create-event')
        else:
            context['back_url'] = reverse_lazy('create-person')
            context['skip_url'] = reverse_lazy('create-event')

        context['organizations'] = organizations
        context['source'] = Source.objects.get(uuid=self.request.session['source_id'])

        form = self.form_class()
        context['geo_types'] = form.fields['geography_type'].choices

        existing_forms = self.request.session.get('forms', {})

        if existing_forms and existing_forms.get('geographies') and not getattr(self, 'formset', False):

            form_data = existing_forms.get('geographies')
            self.initFormset(form_data)

            context['formset'] = self.get_formset_context(self.formset)
            context['browsing'] = True

        return context

    def formset_valid(self, formset):
        source = Source.objects.get(uuid=self.request.session['source_id'])
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

            country_code = geo.country_code.lower()

            division_id = 'ocd-division/country:{}'.format(country_code)

            org_confidence = int(formset.data.get(form_prefix +
                                                  'org_confidence', 1))
            geotype_confidence = int(formset.data.get(form_prefix +
                                                      'geotype_confidence', 1))
            name_confidence = int(formset.data.get(form_prefix +
                                                   'name_confidence', 1))
            osm_id_confidence = int(formset.data.get(form_prefix +
                                                     'osm_id_confidence', 1))
            startdate_confidence = int(formset.data.get(form_prefix +
                                                        'startdate_confidence', 1))
            enddate_confidence = int(formset.data.get(form_prefix +
                                                      'enddate_confidence', 1))

            if formset.data.get(form_prefix + 'geography_type') == 'Site':

                names = [
                    formset.data.get(form_prefix + 'name'),
                    geo.name,
                    admin1,
                ]

                exactloc_id = formset.data.get(form_prefix + 'exactlocation_id')
                # If the Exact Location exists, prefer it to the Admin levels
                if exactloc_id:
                    exactloc_confidence = int(formset.data.get(form_prefix +
                                                               'exactlocation_confidence', 1))
                    exactloc_geo = get_osm_by_id(exactloc_id)

                    names.insert(1, exactloc_geo.name)

                    geosite_id = exactloc_geo.id
                    coords = getattr(exactloc_geo, 'geometry')
                    coord_confidence = exactloc_confidence

                    if not coords:
                        coords = getattr(geo, 'geometry')

                    site, created = Geosite.objects.get_or_create(geositelocationid__value=geosite_id)

                else:
                    geosite_id = geo.id
                    coords = getattr(geo, 'geometry')
                    coord_confidence = osm_id_confidence

                    site, created = Geosite.objects.get_or_create(geositeadminid__value=geosite_id)

                name = ', '.join([n for n in names if n])

                site_data = {
                    'Geosite_GeositeName': {
                        'value': name,
                        'confidence': name_confidence,
                        'sources': [source]
                    },
                    'Geosite_GeositeAdminName': {
                        'value': geo.name,
                        'confidence': osm_id_confidence,
                        'sources': [source]
                    },
                    'Geosite_GeositeAdminId': {
                        'value': geo.id,
                        'confidence': osm_id_confidence,
                        'sources': [source]
                    },
                    'Geosite_GeositeDivisionId': {
                        'value': division_id,
                        'confidence': osm_id_confidence,
                        'sources': [source]
                    },
                    'Geosite_GeositeAdminLevel1': {
                        'value': admin1,
                        'confidence': osm_id_confidence,
                        'sources': [source]
                    },
                    'Geosite_GeositeAdminLevel2': {
                        'value': admin2,
                        'confidence': osm_id_confidence,
                        'sources': [source]
                    },
                    'Geosite_GeositeCoordinates': {
                        'value': coords,
                        'confidence': coord_confidence,
                        'sources': [source]
                    }
                }

                if exactloc_id and exactloc_geo:
                    site_data['Geosite_GeositeLocationId'] = {
                        'value': exactloc_geo.id,
                        'confidence': exactloc_confidence,
                        'sources': [source]
                    }
                    site_data['Geosite_GeositeLocationName'] = {
                        'value': exactloc_geo.name,
                        'confidence': exactloc_confidence,
                        'sources': [source]
                    }

                site.update(site_data)

                emp, created = Emplacement.objects.get_or_create(emplacementorganization__value=org_id,
                                                                 emplacementsite__value=site.id)
                emp_data = {
                    'Emplacement_EmplacementOrganization': {
                        'value': Organization.objects.get(id=org_id),
                        'confidence': org_confidence,
                        'sources': [source]
                    },
                    'Emplacement_EmplacementSite': {
                        'value': site,
                        'confidence': coord_confidence,
                        'sources': [source]
                    },
                }

                if formset.data.get(form_prefix + 'startdate'):
                    emp_data['Emplacement_EmplacementStartDate'] = {
                        'value': formset.data[form_prefix + 'startdate'],
                        'confidence': startdate_confidence,
                        'sources': [source]
                    }

                    if formset.data.get(form_prefix + 'realstart'):
                        emp_data['Emplacement_EmplacementRealStart'] = {
                            'value': formset.data[form_prefix + 'realstart'],
                            'confidence': startdate_confidence,
                            'sources': [source]
                        }

                if formset.data.get(form_prefix + 'enddate'):
                    emp_data['Emplacement_EmplacementEndDate'] = {
                        'value': formset.data[form_prefix + 'enddate'],
                        'confidence': enddate_confidence,
                        'sources': [source]
                    }

                if formset.data.get(form_prefix + 'open_ended'):
                    emp_data['Emplacement_EmplacementOpenEnded'] = {
                        'value': formset.data[form_prefix + 'open_ended'],
                        'confidence': enddate_confidence,
                        'sources': [source]
                    }

                emp.update(emp_data)

            else:

                area, created = Area.objects.get_or_create(areaosmid__value=geo.id)

                if created:

                    area_data = {
                        'Area_AreaName': {
                            'value': formset.data.get(form_prefix + 'name'),
                            'confidence': name_confidence,
                            'sources': [source]
                        },
                        'Area_AreaOSMName': {
                            'value': geo.name,
                            'confidence': osm_id_confidence,
                            'sources': [source]
                        },
                        'Area_AreaOSMId': {
                            'value': geo.id,
                            'confidence': osm_id_confidence,
                            'sources': [source]
                        },
                        'Area_AreaDivisionId': {
                            'value': division_id,
                            'confidence': osm_id_confidence,
                            'sources': [source]
                        },
                        'Area_AreaGeometry': {
                            'value': geo.geometry,
                            'confidence': osm_id_confidence,
                            'sources': [source]
                        }
                    }
                    area.update(area_data)

                assoc, created = Association.objects.get_or_create(associationorganization__value=org_id,
                                                                   associationarea__value=area.id)

                assoc_data = {
                    'Association_AssociationOrganization': {
                        'value': Organization.objects.get(id=org_id),
                        'confidence': org_confidence,
                        'sources': [source]
                    },
                    'Association_AssociationArea': {
                        'value': area,
                        'confidence': osm_id_confidence,
                        'sources': [source]
                    }
                }

                if formset.data.get(form_prefix + 'startdate'):
                    assoc_data['Association_AssociationStartDate'] = {
                        'value': formset.data[form_prefix + 'startdate'],
                        'confidence': startdate_confidence,
                        'sources': [source]
                    }

                    if formset.data.get(form_prefix + 'realstart'):
                        assoc_data['Association_AssociationRealStart'] = {
                            'value': formset.data[form_prefix + 'realstart'],
                            'confidence': startdate_confidence,
                            'sources': [source]
                        }

                if formset.data.get(form_prefix + 'enddate'):
                    assoc_data['Association_AssociationEndDate'] = {
                        'value': formset.data[form_prefix + 'enddate'],
                        'confidence': enddate_confidence,
                        'sources': [source]
                    }

                if formset.data.get(form_prefix + 'open_ended'):
                    assoc_data['Association_AssociationOpenEnded'] = {
                        'value': formset.data[form_prefix + 'open_ended'],
                        'confidence': enddate_confidence,
                        'sources': [source]
                    }

                assoc.update(assoc_data)

        response = super().formset_valid(formset)

        if not self.request.session.get('forms'):
            self.request.session['forms'] = {}

        self.request.session['forms']['geographies'] = formset.data
        self.request.session.modified = True

        return response
