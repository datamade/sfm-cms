import json
import csv
from datetime import date

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.admin.utils import NestedObjects
from django.contrib import messages
from django.views.generic.edit import DeleteView, FormView
from django.views.generic.base import TemplateView
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db import DEFAULT_DB_ALIAS
from django.utils.translation import get_language
from django.core.urlresolvers import reverse_lazy

from extra_views import FormSetView
from cities.models import Place, City, Country, Region, Subregion, District

from source.models import Source
from geosite.models import Geosite
from emplacement.models import Emplacement
from area.models import Area
from association.models import Association
from organization.forms import OrganizationForm, OrganizationGeographyForm
from organization.models import Organization, OrganizationName, \
    OrganizationAlias, Alias as OrganizationAliasObject, Classification
from sfm_pc.utils import deleted_in_str

class OrganizationCreate(FormSetView):
    template_name = 'organization/create.html'
    form_class = OrganizationForm
    success_url = reverse_lazy('create-people')
    extra = 1
    max_num = None

    def dispatch(self, *args, **kwargs):
        # Redirect to source creation page if no source in session
        if not self.request.session.get('source_id'):
            messages.add_message(self.request, 
                                 messages.INFO, 
                                 "Before adding an organization, please tell us about your source.",
                                 extra_tags='alert alert-info')
            return redirect(reverse_lazy('create-source'))
        else:
            return super().dispatch(*args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classifications'] = Classification.objects.all()

        context['source'] = Source.objects.get(id=self.request.session['source_id'])
        
        return context

    def post(self, request, *args, **kwargs):
        
        OrgFormSet = self.get_formset()
        
        management_keys = [
            'form-MAX_NUM_FORMS', 
            'form-MIN_NUM_FORMS', 
            'form-INITIAL_FORMS', 
            'form-TOTAL_FORMS', 
            'form-FORMS_ADDED'
        ]

        form_data = {}
        
        for key, value in request.POST.items():
            if 'alias' in key:
                form_data[key] = request.POST.getlist(key)
            else:
                form_data[key] = request.POST.get(key)
        
        formset = OrgFormSet(form_data)
        
        if formset.is_valid():
            return self.formset_valid(formset)
        else:
            return self.formset_invalid(formset)
    
    def formset_invalid(self, formset):
        response = super().formset_invalid(formset)
        
        for index, form in enumerate(formset.forms):
            alias_ids = formset.data.get('form-{}-alias'.format(index))
            if alias_ids:
                for alias_id in alias_ids:
                    try:
                        org_alias = OrganizationAlias.objects.get(id=alias_id)
                    except ValueError:
                        org_alias = None
                    
                    if org_alias:
                        try:
                            form.aliases.append(org_alias)
                        except AttributeError:
                            form.aliases = [org_alias]
            else:
                form.aliases = None
        
        return response

    def formset_valid(self, formset):
        forms_added = int(formset.data['form-FORMS_ADDED'][0])     
        
        self.organizations = []
        
        source = Source.objects.get(id=self.request.session['source_id'])

        actual_form_index = 0
        
        for i in range(0, forms_added):

            form_prefix = 'form-{0}-'.format(i)
            actual_form_prefix = 'form-{0}-'.format(actual_form_index)

            form_key_mapper = {k: k.replace(str(i), str(actual_form_index)) \
                                   for k in formset.data.keys() \
                                       if k.startswith(form_prefix)}
            
            name_id_key = 'form-{0}-name'.format(i)
            name_text_key = 'form-{0}-name_text'.format(i)
            
            try:
                name_id = formset.data[name_id_key]
            except MultiValueDictKeyError:
                continue
            
            name_text = formset.data[name_text_key]
            
            org_info = {
                'Organization_OrganizationName': {
                    'value': name_text, 
                    'confidence': 1,
                    'sources': [source]
                },
            }
            
            try:
                organization = Organization.objects.get(id=name_id)
                existing_sources = organization.organizationname_set.all()[0].sources.all()
                
                org_info["Organization_OrganizationName"]['sources'].extend(existing_sources)
            
            except (Organization.DoesNotExist, ValueError):
                organization = Organization.create(org_info)

            # Save aliases first
            alias_id_key = 'form-{0}-alias'.format(i)
            alias_text_key = 'form-{0}-alias_text'.format(i)
            
            aliases = formset.data.get(alias_text_key)
            
            if aliases:
                
                for alias in aliases:
                    
                    alias_obj, created = OrganizationAliasObject.objects.get_or_create(value=alias)

                    oa_obj, created = OrganizationAlias.objects.get_or_create(value=alias_obj,
                                                                              object_ref=organization,
                                                                              lang=get_language())
                    oa_obj.sources.add(source)
                    oa_obj.save()

            # Next do classification
            classification = formset.data.get(form_prefix + 'classification')
            
            if classification:
                
                classification_obj = Classification.objects.get(id=classification)
                org_info['Organization_OrganizationClassification'] = {
                    'value': classification_obj,
                    'confidence': 1,
                    'sources': [source]
                }

            # Now do dates
            realfounding = form_prefix + 'realfounding' in formset.data.keys()

            # Add to dict used to update org
            org_info.update({
                'Organization_OrganizationFoundingDate': {
                    'value': formset.data.get(form_prefix + 'foundingdate'),
                    'confidence': 1,
                    'sources': [source],
                },
                'Organization_OrganizationRealFounding': {
                    'value': realfounding,
                    'confidence': 1,
                    'sources': [source],
                },
            })
            
            # Now update org
            organization.update(org_info)
 
            self.organizations.append(organization)
            
            actual_form_index += 1
        
        self.request.session['organizations'] = [{'id': o.id, 'name': o.name.get_value().value} \
                                                     for o in self.organizations]
        
        response = super().formset_valid(formset)
        return response



class OrganizationUpdate(FormView):
    template_name = 'organization/edit.html'
    form_class = OrganizationForm
    success_url = reverse_lazy('dashboard')
    sourced = True

    def post(self, request, *args, **kwargs):
        
        form = OrgForm(request.POST)
        
        if not request.POST.get('source'):
            self.sourced = False
            return self.form_invalid(form)
        else:
            self.source = Source.objects.get(id=request.POST.get('source'))
        
        self.aliases = request.POST.getlist('alias')

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        organization = Organization.objects.get(pk=self.kwargs['pk'])
        
        org_info = {
            'Organization_OrganizationName': {
                'value': form.cleaned_data['name_text'],
                'confidence': 1,
                'source': list(set(list(organization.name.get_sources()) + [self.source]))
            },
            'Organization_OrganizationClassification': {
                'value': form.cleaned_data['classification'],
                'confidence': 1,
                'source': list(set(list(organization.classification.get_sources()) + [self.source])),
            },
            'Organization_OrganizationFoundingDate': {
                'value': form.cleaned_data['foundingdate'],
                'confidence': 1,
                'sources': list(set(list(organization.foundingdate.get_sources()) + [self.source])),
            },
            'Organization_OrganizationRealFounding': {
                'value': form.cleaned_data['realfounding'],
                'confidence': 1,
                'sources': list(set(list(organization.realfounding.get_sources()) + [self.source])),
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
                    alias_obj, created = OrganizationAliasObject.objects.get_or_create(value=alias)

                    oa_obj = OrganizationAlias.objects.create(value=alias_obj,
                                                              object_ref=organization,
                                                              lang=get_language())
                    oa_obj.sources.add(self.source)
                    oa_obj.save()

            organization.organizationalias_set = aliases
            organization.save()

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = Organization.objects.get(pk=self.kwargs['pk'])
        
        form_data = {
            'name': organization.name.get_value(),
            'classification': organization.classification.get_value(),
            'alias': [i.get_value() for i in organization.aliases.get_list()],
            'foundingdate': organization.foundingdate.get_value(),
            'realfounding': organization.realfounding.get_value(),
        }

        context['form_data'] = form_data
        context['title'] = 'Organization'
        context['organization'] = organization
        context['classifications'] = Classification.objects.all()
        
        if not self.sourced:
            context['source_error'] = 'Please include the source for your changes'

        return context

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

class OrganizationCreateGeography(FormSetView):
    template_name = 'organization/create-geography.html'
    form_class = OrganizationGeographyForm
    success_url = reverse_lazy('create-event')
    extra = 1
    max_num = None

    def dispatch(self, *args, **kwargs):
        # Redirect to source creation page if no source in session
        if not self.request.session.get('source_id'):
            messages.add_message(self.request, 
                                 messages.INFO, 
                                 "Before adding geographies, please tell us about your source.",
                                 extra_tags='alert alert-info')
            return redirect('/create-source/')
        else:
            return super().dispatch(*args, **kwargs)

   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        organizations = self.request.session['organizations']
        people = self.request.session['people']
  
        context['people'] = people 
        context['organizations'] = organizations
        context['source'] = Source.objects.get(id=self.request.session['source_id'])
        
        form = self.form_class()
        context['geo_types'] = form.fields['geography_type'].choices
        
        return context

    def post(self, request, *args, **kwargs):
        organizations = self.request.session['organizations']

        OrganizationGeographyFormset = self.get_formset()
        formset = OrganizationGeographyFormset(request.POST)
 
        if formset.is_valid():
            return self.formset_valid(formset)
        else:
            return self.formset_invalid(formset)
    
    def formset_valid(self, formset):
        source = Source.objects.get(id=self.request.session['source_id'])
        num_forms = int(formset.data['form-TOTAL_FORMS'][0])
        
        for i in range(0, num_forms):
            form_prefix = 'form-{0}-'.format(i)
            
            form_keys = [k for k in formset.data.keys() \
                             if k.startswith(form_prefix)]
            startdate = formset.data[form_prefix + 'startdate']
            enddate = formset.data[form_prefix + 'enddate']
            org_id = formset.data[form_prefix + 'org']
            geoid = formset.data[form_prefix + 'geoname']
            geotype = formset.data[form_prefix + 'geotype']
            
            if geotype == 'country':
                geo = Country.objects.get(id=geoid)
                admin1 = None
                admin2 = None
                coords = None
                code = geo.code
                geometry = None 
            
            elif geotype == 'region':
                geo = Region.objects.get(id=geoid)
                admin1 = geo.parent.name
                admin2 = geo.parent.parent.name
                coords = None
                code = geo.code
                geometry = None
            
            elif geotype == 'subregion':
                geo = Subregion.objects.get(id=geoid)
                admin1 = geo.parent.name
                admin2 = geo.parent.parent.name
                coords = None
                code = geo.code
                geometry = None
            
            elif geotype == 'city':
                geo = City.objects.get(id=geoid)
                admin1 = geo.parent.name
                admin2 = geo.parent.parent.name
                coords = geo.location
                code = None
                geometry = None
            
            else:
                geo = District.objects.get(id=geoid)
                admin1 = geo.parent.name
                admin2 = geo.parent.parent.name
                coords = geo.location
                code = None
                geometry = None
            
            if formset.data[form_prefix + 'geography_type'] == 'Site':
                get_site = Geosite.objects.filter(geositegeonameid__value=geo.id)
                if len(get_site) == 0:
                    site_data = {
                        'Geosite_GeositeName': {
                            'value': formset.data[form_prefix + 'name'],
                            'confidence': 1,
                            'source': [source]
                        },
                        'Geosite_GeositeGeoname': {
                            'value': geo.name,
                            'confidence': 1,
                            'source': [source]
                        },
                        'Geosite_GeositeGeonameId': {
                            'value': geo.id,
                            'confidence': 1,
                            'source': [source]
                        },
                        'Geosite_GeositeAdminLevel1': {
                            'value': admin1,
                            'confidence': 1,
                            'source': [source]
                        },
                        'Geosite_GeositeAdminLevel2': {
                            'value': admin2,
                            'confidence': 1,
                            'source': [source]
                        },
                        'Geosite_GeositeCoordinates': {
                            'value': coords,
                            'confidence': 1,
                            'source': [source]
                        }
                    }
                    site = Geosite.create(site_data)
                else:
                    site = get_site[0]
                get_emp = Emplacement.objects.filter(emplacementorganization__value=org_id).filter(emplacementsite__value=site.id).first()
                if get_emp:
                    # update dates?
                    # add sources
                    emp_data = {
                        'Emplacement_EmplacementStartDate': {
                            'value': formset.data[form_prefix + 'startdate'],
                            'confidence': 1,
                            'source': [source]
                        },
                        'Emplacement_EmplacementEndDate': {
                            'value': formset.data[form_prefix + 'enddate'],
                            'confidence': 1,
                            'source': [source]
                        } 
                    } 
                    get_emp.update(emp_data)
                else:
                    emp_data = {
                        'Emplacement_EmplacementOrganization': {
                            'value': Organization.objects.get(id=org_id),
                            'confidence': 1,
                            'source': [source]
                        },
                        'Emplacement_EmplacementSite': {
                            'value': site,
                            'confidence': 1,
                            'source': [source]
                        },
                        'Emplacement_EmplacementStartDate': {
                            'value': formset.data[form_prefix + 'startdate'],
                            'confidence': 1,
                            'source': [source]
                        },
                        'Emplacement_EmplacementEndDate': {
                            'value': formset.data[form_prefix + 'enddate'],
                            'confidence': 1,
                            'source': [source]
                        }
                    }
                    Emplacement.create(emp_data)
            else:
                get_area = Area.objects.filter(areageonameid__value = geo.id)
                if len(get_area) == 0:
                    code_obj = Code.objects.create(value=code)
                    area_data = {
                        'Area_AreaName': {
                            'value': formset.data[form_prefix + 'name'],
                            'confidence': 1,
                            'source': [source]
                        },
                        'Area_AreaGeoname': {
                            'value': geo.name,
                            'confidence': 1,
                            'source': [source]
                        },
                        'Area_AreaGeonameId': {
                            'value': geo.id,
                            'confidence': 1,
                            'source': [source]
                        },
                        'Area_AreaCode': {
                            'value': code_obj,
                            'confidence': 1,
                            'source': [source]
                        },
                        'Area_AreaGeometry': {
                            'value': geometry,
                            'confidence': 1,
                            'source': [source]
                        }
                    }
                    area = Area.create(area_data)
                else:
                    area = get_area[0]
                get_assoc = Association.objects.filter(associationorganization__value=org_id).filter(associationarea__value=area.id).first()
                if get_assoc:
                    # update dates?
                    # add sources
                    assoc_data = {
                        'Association_AssociationStartDate': {
                            'value': formset.data[form_prefix + 'startdate'],
                            'confidence': 1,
                            'source': [source]
                        },
                        'Association_AssociationEndDate': {
                            'value': formset.data[form_prefix + 'enddate'],
                            'confidence': 1,
                            'source': [source]
                        } 
                    } 
                    get_assoc.update(assoc_data)
                else:
                    assoc_data = {
                        'Association_AssociationOrganization': {
                            'value': Organization.objects.get(id=org_id),
                            'confidence': 1,
                            'source': [source]
                        },
                        'Association_AssociationArea': {
                            'value': area,
                            'confidence': 1,
                            'source': [source]
                        },
                        'Association_AssociationStartDate': {
                            'value': formset.data[form_prefix + 'startdate'],
                            'confidence': 1,
                            'source': [source]
                        },
                        'Association_AssociationEndDate': {
                            'value': formset.data[form_prefix + 'enddate'],
                            'confidence': 1,
                            'source': [source]
                        }
                    }
                    Association.create(assoc_data)
        response = super().formset_valid(formset)
        
        return response


#############################################
###                                       ###
### Below here are currently unused views ###
### which we'll probably need eventually  ###
###                                       ###
#############################################

class OrganizationDelete(DeleteView):
    model = Organization
    template_name = "delete_confirm.html"

    def get_context_data(self, **kwargs):
        context = super(OrganizationDelete, self).get_context_data(**kwargs)
        collector = NestedObjects(using=DEFAULT_DB_ALIAS)
        collector.collect([context['object']])
        deleted_elements = collector.nested()
        context['deleted_elements'] = deleted_in_str(deleted_elements)
        context['title'] = _("Organization")
        context['model'] = "organization"
        return context

    def get_object(self, queryset=None):
        obj = super(OrganizationDelete, self).get_object()

        return obj

def organization_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="organizations.csv"'

    terms = request.GET.dict()
    organization_query = Organization.search(terms)

    writer = csv.writer(response)
    for organization in organization_query:
        writer.writerow([
            organization.id,
            organization.name.get_value(),
            organization.alias.get_value(),
            organization.classification.get_value(),
            repr(organization.foundingdate.get_value()),
            organization.realfounding.get_value(),
        ])

    return response

def classification_autocomplete(request):
    data = request.GET.dict()['term']

    classifications = Classification.objects.filter(
        value__icontains=data
    )

    classifications = [
        {"value": classif.id, "label": _(classif.value)}
        for classif in classifications
    ]

    return HttpResponse(json.dumps(classifications))
