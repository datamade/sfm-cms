import json
import csv
from datetime import date

from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.management import call_command
from django.core.cache import cache
from django.contrib.admin.utils import NestedObjects
from django.contrib import messages
from django.views.generic.edit import DeleteView, FormView
from django.views.generic import TemplateView, DetailView
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db import DEFAULT_DB_ALIAS
from django.core.urlresolvers import reverse_lazy, reverse
from django.utils.translation import get_language
from django.utils.translation import ugettext as _
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from extra_views import FormSetView

from violation.models import Violation, ViolationType, \
    ViolationPerpetrator, ViolationPerpetratorOrganization
from source.models import Source
from geosite.models import Geosite
from person.models import Person
from organization.models import Organization
from violation.forms import ZoneForm, ViolationForm
from sfm_pc.utils import deleted_in_str, get_osm_by_id, get_hierarchy_by_id
from sfm_pc.base_views import BaseFormSetView, BaseUpdateView, PaginatedList


class ViolationDetail(DetailView):
    model = Violation
    template_name = 'violation/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Generate link to download a CSV of this record
        params = '?download_etype=Violation&entity_id={0}'.format(str(context['violation'].uuid))

        context['download_url'] = reverse('download') + params

        context['location'] = None

        if context['violation'].location.get_value():
            location = context['violation'].location.get_value()
            if location.value:
                context['location'] = location.value

        context['versions'] = context['violation'].getVersions()

        return context

class ViolationList(PaginatedList):
    model = Violation
    template_name = 'violation/list.html'
    orderby_lookup = {
        'start_date': 'violationstartdate__value',
        'end_date': 'violationenddate__value',
        'osmname': 'violationosmname__value',
        'classification': 'violationperpetratorclassification__value__value',
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Highlight the correct nav tab in the template
        context['violation_tab'] = 'selected-tab'
        context['search_term'] = 'an incident'
        return context


class ViolationCreate(LoginRequiredMixin, BaseFormSetView):
    template_name = 'violation/create.html'
    form_class = ViolationForm
    success_url = reverse_lazy('dashboard')
    extra = 1
    max_num = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confidence_levels'] = settings.CONFIDENCE_LEVELS

        organizations = self.request.session.get('organizations')
        people = self.request.session.get('people')

        context['types'] = ViolationType.objects.filter(lang=get_language())\
                                                .distinct('value')
        context['people'] = people
        context['organizations'] = organizations
        context['source'] = Source.objects.get(id=self.request.session['source_id'])

        context['back_url'] = reverse_lazy('create-geography')
        context['skip_url'] = reverse_lazy('set-confidence')

        existing_forms = self.request.session.get('forms', {})

        if existing_forms and existing_forms.get('violations') and not getattr(self, 'formset', False):

            form_data = existing_forms.get('violations')
            self.initFormset(form_data)

            context['formset'] = self.formset
            context['browsing'] = True

        return context

    def formset_valid(self, formset):
        source = Source.objects.get(id=self.request.session['source_id'])
        num_forms = int(formset.data['form-TOTAL_FORMS'][0])

        if not self.request.session.get('forms'):
            self.request.session['forms'] = {}

        self.request.session['forms']['violations'] = formset.data.copy()

        for i in range(0, num_forms):
            form_prefix = 'form-{0}-'.format(i)

            violation_id = int(formset.data.get(form_prefix + 'violation_id', -1))

            startdate = formset.data[form_prefix + 'startdate']
            startdate_confidence = int(formset.data.get(form_prefix +
                                                        'startdate_confidence', 1))
            enddate = formset.data[form_prefix + 'enddate']
            enddate_confidence = int(formset.data.get(form_prefix +
                                                      'enddate_confidence', 1))

            firstallegation = formset.data.get(form_prefix + 'firstallegation')
            firstallegation_confidence = int(formset.data.get(form_prefix +
                                                              'firstallegation_confidence', 1))

            lastupdate = formset.data.get(form_prefix + 'lastupdate')
            lastupdate_confidence = int(formset.data.get(form_prefix +
                                                         'lastupdate_confidence', 1))

            status = formset.data.get(form_prefix + 'status')
            status_confidence = int(formset.data.get(form_prefix +
                                                     'status_confidence', 1))

            locationdescription = formset.data.get(form_prefix + 'locationdescription')
            locationdescription_confidence = int(formset.data.get(form_prefix +
                                                                  'locationdescription_confidence', 1))

            geoid = formset.data.get(form_prefix + 'osm_id')
            osm_confidence = int(formset.data.get(form_prefix +
                                                  'osm_confidence', 1))

            exactloc_id = formset.data.get(form_prefix + 'exactlocation_id')
            exactloc_confidence = formset.data.get(form_prefix + 'exactlocation_confidence')

            description = formset.data[form_prefix + 'description']
            description_confidence = int(formset.data.get(form_prefix +
                                                          'description_confidence', 1))

            perpetrators = formset.data.getlist(form_prefix + 'perpetrators')
            perp_confidence = int(formset.data.get(form_prefix +
                                                   'perp_confidence', 1))

            orgs = formset.data.getlist(form_prefix + 'orgs')
            orgs_confidence = int(formset.data.get(form_prefix +
                                                   'orgs_confidence', 1))

            vtypes = formset.data.getlist(form_prefix + 'vtype')
            type_confidence = int(formset.data.get(form_prefix +
                                                   'type_confidence', 1))

            # Administrative locations
            if geoid:
                geo = get_osm_by_id(geoid)
                geo_id, geo_name, coords = geo.id, geo.name, geo.geometry
                country_code = geo.country_code.lower()
                division_id = 'ocd-division/country:{}'.format(country_code)
                hierarchy = get_hierarchy_by_id(geoid)
            else:
                geo, geo_id, geo_name, coords = None, None, None, None
                country_code = None
                division_id = None
                hierarchy = None

            admin1 = None
            admin2 = None

            if hierarchy:
                for member in hierarchy:
                    if member.admin_level == 6:
                        admin1 = member.name
                    elif member.admin_level == 4:
                        admin2 = member.name

            # Exact location
            if exactloc_id:

                exactloc_geo = get_osm_by_id(exactloc_id)

                # If we don't have higher-order geographic information for
                # this place yet, see if the exact location can help us
                # find it
                if not admin1 and not admin2 and not division_id:
                    hierarchy = get_hierarchy_by_id(geoid)
                    if hierarchy:
                        for member in hierarchy:
                            if member.admin_level == 6:
                                admin1 = member.name
                            elif member.admin_level == 4:
                                admin2 = member.name

                exactloc_name = getattr(exactloc_geo, 'name')

                # Prefer coordinates from the exact location, if exists
                coords = getattr(exactloc_geo, 'geometry')

            else:
                exactloc_name = None

            # Instantiate the data dict with the required fields, which must
            # exist
            violation_data = {
                'Violation_ViolationDescription': {
                   'value': description,
                   'sources': [source],
                   'confidence': description_confidence
                },
                'Violation_ViolationStartDate': {
                    'value': startdate,
                    'sources': [source],
                    'confidence': startdate_confidence
                },
                'Violation_ViolationEndDate': {
                    'value': enddate,
                    'sources': [source],
                    'confidence': enddate_confidence
                },
            }

            # Define optional fields
            optional_fields = {
                'Violation_ViolationFirstAllegation': {
                    'value': firstallegation,
                    'sources': [source],
                    'confidence': firstallegation_confidence
                },
                'Violation_ViolationLastUpdate': {
                    'value': lastupdate,
                    'sources': [source],
                    'confidence': lastupdate_confidence
                },
                'Violation_ViolationStatus': {
                    'value': status,
                    'sources': [source],
                    'confidence': status_confidence
                },
                'Violation_ViolationLocationDescription': {
                    'value': locationdescription,
                    'sources': [source],
                    'confidence': locationdescription_confidence
                },
                'Violation_ViolationAdminLevel1': {
                    'value': admin1,
                    'sources': [source],
                    'confidence': osm_confidence
                },
                'Violation_ViolationAdminLevel2': {
                    'value': admin2,
                    'sources': [source],
                    'confidence': osm_confidence
                },
                'Violation_ViolationOSMname': {
                    'value': geo_name,
                    'sources': [source],
                    'confidence': osm_confidence
                },
                'Violation_ViolationOSMId': {
                    'value': geo_id,
                    'sources': [source],
                    'confidence': osm_confidence
                },
                'Violation_ViolationDivisionId': {
                    'value': division_id,
                    'sources': [source],
                    'confidence': osm_confidence
                },
                'Violation_ViolationLocation': {
                    'value': coords,
                    'sources': [source],
                    'confidence': osm_confidence
                },
                'Violation_ViolationLocationName': {
                    'value': exactloc_name,
                    'sources': [source],
                    'confidence': exactloc_confidence
                },
                'Violation_ViolationLocationId': {
                    'value': exactloc_id,
                    'sources': [source],
                    'confidence': exactloc_confidence
                },
            }

            for field, vals in optional_fields.items():
                # Only add optional fields if they have existent values
                if vals['value']:
                    violation_data[field] = {
                        'value': vals['value'],
                        'sources': vals['sources'],
                        'confidence': vals['confidence']
                    }

            if violation_id == -1:
                violation = Violation.create(violation_data)
                self.request.session['forms']['violations'][form_prefix + 'violation_id'] = violation.id
            else:
                violation = Violation.objects.get(id=int(violation_id))
                violation.update(violation_data)

            # Foreignkey objects
            if vtypes:
                for vtype in vtypes:
                    type_obj = Type.objects.get(id=int(vtype))
                    vt_obj, created = ViolationType.objects.get_or_create(value=type_obj,
                                                                          object_ref=violation,
                                                                          lang=get_language())
                    vt_obj.sources.add(source)
                    vt_obj.confidence = type_confidence
                    vt_obj.save()

            if perpetrators:
                for perpetrator in perpetrators:

                    try:
                        perp = Person.objects.get(id=perpetrator)
                    except (Person.DoesNotExist, ValueError):
                        info = {
                            'Person_PersonName': {
                                'value': perpetrator,
                                'confidence': perp_confidence,
                                'sources': [source],
                            }
                        }
                        perp = Person.create(info)

                    vp_obj, created = ViolationPerpetrator.objects.get_or_create(value=perp,
                                                                                 object_ref=violation)

                    vp_obj.sources.add(source)
                    vp_obj.confidence = perp_confidence
                    vp_obj.save()

            if orgs:
                for org in orgs:

                    try:
                        organization = Organization.objects.get(id=org)
                    except (Organization.DoesNotExist, ValueError):
                        info = {
                            'Organization_OrganizationName': {
                                'value': org,
                                'confidence': orgs_confidence,
                                'sources': [source],
                            }
                        }
                        organization = Organization.create(info)

                    vpo_obj, created = ViolationPerpetratorOrganization.objects.get_or_create(value=organization,
                                                                                              object_ref=violation)

                    vpo_obj.sources.add(source)
                    vpo_obj.confidence = orgs_confidence
                    vpo_obj.save()

            # Queue up to be added to search index
            to_index = self.request.session.get('index')

            if not to_index:
                self.request.session['index'] = {}

            self.request.session['index'][str(violation.uuid)] = 'violations'

        response = super().formset_valid(formset)

        # Clear cache so we can see new search results and detail views
        cache.clear()

        # Refresh materialized views
        call_command('make_flattened_views', refresh=True)

        # Refresh search index with new entities
        to_index = self.request.session.get('index')
        if to_index:
            for uuid, etype in to_index.items():
                call_command('make_search_index', doc_id=uuid, entity_types=etype)

        # Add source to the search index
        call_command('make_search_index', doc_id=source.id, entity_types='sources')

        success_message = _('Thanks for adding a new source! The database and search index have been updated.')
        messages.add_message(self.request, messages.SUCCESS, success_message)

        return response

class ViolationUpdate(LoginRequiredMixin, BaseUpdateView):
    template_name = 'violation/edit.html'
    form_class = ViolationForm
    success_url = reverse_lazy('dashboard')
    sourced = True

    def post(self, request, *args, **kwargs):

        self.checkSource(request)

        return self.validateForm()

    def form_valid(self, form):
        response = super().form_valid(form)

        violation = Violation.objects.get(pk=self.kwargs['pk'])
        startdate = form.cleaned_data['startdate']
        enddate = form.cleaned_data['enddate']
        locationdescription = form.cleaned_data['locationdescription']
        geoid = form.cleaned_data['osm_id']
        description = form.cleaned_data['description']
        perpetrators = form.data.getlist('perpetrators')
        orgs = form.data.getlist('orgs')
        vtypes = form.data.getlist('vtype')

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

        violation_data = {
            'Violation_ViolationDescription': {
               'value': description,
               'sources': self.sourcesList(violation, 'description'),
               'confidence': 1
            },
            'Violation_ViolationLocationDescription': {
                'value': locationdescription,
                'sources': self.sourcesList(violation, 'locationdescription'),
                'confidence': 1
            },
            'Violation_ViolationAdminLevel1': {
                'value': admin1,
                'sources': self.sourcesList(violation, 'adminlevel1'),
                'confidence': 1
            },
            'Violation_ViolationAdminLevel2': {
                'value': admin2,
                'sources': self.sourcesList(violation, 'adminlevel2'),
                'confidence': 1
            },
            'Violation_ViolationOSMName': {
                'value': geo.name,
                'sources': self.sourcesList(violation, 'osmname'),
                'confidence': 1
            },
            'Violation_ViolationOSMId': {
                'value': geo.id,
                'sources': self.sourcesList(violation, 'osmid'),
                'confidence': 1
            },
            'Violation_ViolationLocation': {
                'value': coords,
                'sources': self.sourcesList(violation, 'location'),
                'confidence': 1
            },
            'Violation_ViolationStartDate': {
                'value': startdate,
                'sources': self.sourcesList(violation, 'startdate'),
                'confidence': 1
            },
            'Violation_ViolationEndDate': {
                'value': enddate,
                'sources': self.sourcesList(violation, 'enddate'),
                'confidence': 1
            }
        }
        violation.update(violation_data)

        if vtypes:
            for vtype in vtypes:
                type_obj = Type.objects.get(id=vtype)
                vt_obj, created = ViolationType.objects.get_or_create(value=type_obj,
                                                                      object_ref=violation,
                                                                      lang=get_language())
                vt_obj.sources.add(self.source)
                vt_obj.save()

        if perpetrators:
            for perpetrator in perpetrators:

                perp = Person.objects.get(id=perpetrator)
                vp_obj, created = ViolationPerpetrator.objects.get_or_create(value=perp,
                                                                             object_ref=violation)

                vp_obj.sources.add(self.source)
                vp_obj.save()

        if orgs:
            for org in orgs:

                organization = Organization.objects.get(id=org)
                vpo_obj, created = ViolationPerpetratorOrganization.objects.get_or_create(value=organization,
                                                                                          object_ref=violation)

                vpo_obj.sources.add(self.source)
                vpo_obj.save()

        messages.add_message(self.request,
                             messages.INFO,
                             'Event saved!')

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        violation = Violation.objects.get(pk=self.kwargs['pk'])
        context['violation'] = violation
        context['types'] = ViolationType.objects.filter(lang=get_language())
        context['violation_types'] = []

        for violation_type in violation.types.get_list():
            context['violation_types'].append(violation_type.get_value().value.id)

        if not self.sourced:
            context['source_error'] = 'Please include the source for your changes'

        context['osm'] = get_osm_by_id(violation.osmid.get_value().value)
        context['source'] = Source.objects.filter(id=self.request.GET.get('source_id')).first()

        return context


class ViolationDelete(LoginRequiredMixin, DeleteView):
    model = Violation
    template_name = "delete_confirm.html"

    def get_context_data(self, **kwargs):
        context = super(ViolationDelete, self).get_context_data(**kwargs)
        collector = NestedObjects(using=DEFAULT_DB_ALIAS)
        collector.collect([context['object']])
        deleted_elements = collector.nested()
        context['deleted_elements'] = deleted_in_str(deleted_elements)
        return context

    def get_object(self, queryset=None):
        obj = super(ViolationDelete, self).get_object()

        return obj


class ViolationView(TemplateView):
    template_name = 'violation/search.html'

    def get_context_data(self, **kwargs):
        context = super(ViolationView, self).get_context_data(**kwargs)

        context['year_range'] = range(1950, date.today().year + 1)
        context['day_range'] = range(1, 32)

        return context

def violation_type_autocomplete(request):
    term = request.GET.get('q')
    types = ViolationType.objects.filter(value__code__icontains=term)\
                                 .filter(lang=get_language()).all()

    results = []
    for violation_type in types:
        results.append({
            'text': violation_type.get_value(),
            'id': violation_type.id,
        })

    return HttpResponse(json.dumps(results), content_type='application/json')


def violation_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="violations.csv"'

    terms = request.GET.dict()
    violation_query = Violation.search(terms)

    writer = csv.writer(response)
    for violation in violation_query:
        writer.writerow([
            violation.id,
            violation.description.get_value(),
            repr(violation.startdate.get_value()),
            repr(violation.enddate.get_value()),
            violation.locationdescription.get_value(),
            violation.adminlevel1.get_value(),
            violation.adminlevel2.get_value(),
            violation.osmname.get_value(),
            violation.osmid.get_value(),
            violation.location.get_value(),
            violation.perpetrator.get_value(),
            violation.perpetratororganization.get_value(),
        ])

    return response

