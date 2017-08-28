import json
import csv
from datetime import date

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.admin.utils import NestedObjects
from django.contrib import messages
from django.views.generic.edit import DeleteView, FormView
from django.views.generic import TemplateView, DetailView
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db import DEFAULT_DB_ALIAS
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import get_language
from django.shortcuts import redirect
from django.conf import settings

from extra_views import FormSetView
from complex_fields.models import CONFIDENCE_LEVELS

from violation.models import Violation, Type, ViolationType, \
    ViolationPerpetrator, ViolationPerpetratorOrganization
from source.models import Source
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

        context['location'] = None

        if context['violation'].location.get_value():
            location = context['violation'].location.get_value()
            if location.value:
                context['location'] = location.value

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
        print('Getting incident context...')

        # Highlight the correct nav tab in the template
        context['violation_tab'] = 'selected-tab'
        context['search_term'] = 'an incident'
        return context


class ViolationCreate(FormSetView):
    template_name = 'violation/create.html'
    form_class = ViolationForm
    success_url = reverse_lazy('set-confidence')
    extra = 1
    max_num = None
   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confidence_levels'] = CONFIDENCE_LEVELS

        organizations = self.request.session.get('organizations')
        people = self.request.session.get('people')
        
        context['types'] = ViolationType.objects.filter(lang=get_language())\
                                                .distinct('value')
        context['people'] = people         
        context['organizations'] = organizations
        context['source'] = Source.objects.get(id=self.request.session['source_id'])

        context['back_url'] = reverse_lazy('create-geography')
        context['skip_url'] = reverse_lazy('set-confidence')

        return context

    def formset_valid(self, formset):
        source = Source.objects.get(id=self.request.session['source_id'])
        num_forms = int(formset.data['form-TOTAL_FORMS'][0])
        for i in range(0, num_forms):
            form_prefix = 'form-{0}-'.format(i)
            
            form_keys = [k for k in formset.data.keys() \
                             if k.startswith(form_prefix)]
            startdate = formset.data[form_prefix + 'startdate']
            enddate = formset.data[form_prefix + 'enddate']
            locationdescription = formset.data[form_prefix + 'locationdescription']
            geoid = formset.data[form_prefix + 'osm_id']
            geotype = formset.data[form_prefix + 'geotype']
            description = formset.data[form_prefix + 'description']
            perpetrators = formset.data.getlist(form_prefix + 'perpetrators')
            orgs = formset.data.getlist(form_prefix + 'orgs')
            vtypes = formset.data.getlist(form_prefix + 'vtype')
            
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
            
            violation_data = {
                'Violation_ViolationDescription': {
                   'value': description,
                   'sources': [source],
                   'confidence': 1
                },
                'Violation_ViolationLocationDescription': {
                    'value': locationdescription,
                    'sources': [source],
                    'confidence': 1
                },
                'Violation_ViolationAdminLevel1': {
                    'value': admin1,
                    'sources': [source],
                    'confidence': 1
                },
                'Violation_ViolationAdminLevel2': {
                    'value': admin2,
                    'sources': [source],
                    'confidence': 1
                },
                'Violation_ViolationOSMname': {
                    'value': geo.name,
                    'sources': [source],
                    'confidence': 1
                },
                'Violation_ViolationOSMId': {
                    'value': geo.id,
                    'sources': [source],
                    'confidence': 1
                },
                'Violation_ViolationDivisionId': {
                    'value': division_id,
                    'sources': [source],
                    'confidence': 1
                },
                'Violation_ViolationLocation': {
                    'value': geo.geometry,
                    'sources': [source],
                    'confidence': 1
                },
                'Violation_ViolationStartDate': {
                    'value': startdate,
                    'sources': [source],
                    'confidence': 1
                },
                'Violation_ViolationEndDate': {
                    'value': enddate,
                    'sources': [source],
                    'confidence': 1
                }
            }
            violation = Violation.create(violation_data)
            
            if vtypes:
                for vtype in vtypes:
                    type_obj = Type.objects.get(id=vtype)
                    vt_obj, created = ViolationType.objects.get_or_create(value=type_obj,
                                                                          object_ref=violation,
                                                                          lang=get_language())
                    vt_obj.sources.add(source)
                    vt_obj.save()

            if perpetrators:
                for perpetrator in perpetrators:
                    
                    try:
                        perp = Person.objects.get(id=perpetrator)
                    except (Person.DoesNotExist, ValueError):
                        info = {
                            'Person_PersonName': {
                                'value': perpetrator,
                                'confidence': 1,
                                'sources': [source],
                            }
                        }
                        perp = Person.create(info)
                    
                    vp_obj, created = ViolationPerpetrator.objects.get_or_create(value=perp,
                                                                                 object_ref=violation)

                    vp_obj.sources.add(source)
                    vp_obj.save()
            
            if orgs:
                for org in orgs:
                    
                    try:
                        organization = Organization.objects.get(id=org)
                    except (Organization.DoesNotExist, ValueError):
                        info = {
                            'Organization_OrganizationName': {
                                'value': org,
                                'confidence': 1,
                                'sources': [source],
                            }
                        }
                        organization = Organization.create(info)

                    vpo_obj, created = ViolationPerpetratorOrganization.objects.get_or_create(value=organization,
                                                                                              object_ref=violation)

                    vpo_obj.sources.add(source)
                    vpo_obj.save()

        response = super().formset_valid(formset)
        return response

class ViolationUpdate(BaseUpdateView):
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


class ViolationDelete(DeleteView):
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

