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
from django.db.models import Q
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext as _
from django.utils.translation import get_language

from extra_views import FormSetView
from complex_fields.models import CONFIDENCE_LEVELS

from person.models import Person, PersonName, PersonAlias, Alias
from person.forms import PersonForm
from organization.models import Organization
from source.models import Source
from membershipperson.models import MembershipPerson, Role
from sfm_pc.utils import deleted_in_str, chain_of_command
from sfm_pc.base_views import BaseFormSetView, BaseUpdateView, PaginatedList

class PersonDetail(DetailView):
    model = Person
    template_name = 'person/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        last_cited_attr = '-object_ref__membershippersonlastciteddate'
        memberships = context['person'].membershippersonmember_set\
                        .order_by(last_cited_attr)

        # Start by getting the most recent membership for the "Last seen as"
        # description
        if len(memberships) > 0:
            last_membership = memberships[0]

            context['last_seen_as'] = last_membership.object_ref.short_description

        context['memberships'] = []
        context['chain_of_command'] = []
        context['subordinates'] = []
        for membership in memberships:

            # Store the raw memberships for use in the template
            context['memberships'].append(membership.object_ref)

            # Grab the org object
            org = membership.object_ref.organization.get_value().value

            # Get the chain of command
            command = chain_of_command(org.uuid)
            context['chain_of_command'].append(json.dumps(command))

            # Next, get some info about subordinates

            # Start by getting all child organizations for the member org
            child_compositions = org.child_organization.all()

            # Start and end date for this membership
            mem_start = membership.object_ref.firstciteddate.get_value()
            no_start = False
            if mem_start is None:
                # Make a bogus date that everything will be greater than
                mem_start = date(1000, 1, 1)
                no_start = True
            else:
                mem_start = mem_start.value

            mem_end = membership.object_ref.lastciteddate.get_value()
            no_end = False
            if mem_end is None:
                mem_end = date.today()
                no_end = True
            else:
                mem_end = mem_end.value

            # Get the commanders of each child organization
            # (Unfortunately, this requires two more iterations)
            if child_compositions:
                for composition in child_compositions:
                    child = composition.object_ref.child.get_value().value

                    # Start and end date attributes for filtering:
                    # We want only the personnel who were commanders of child
                    # organizations during this membership
                    # (also allowing for null dates)
                    commander_start = Q(object_ref__membershippersonfirstciteddate__value__lte=mem_end)
                    start_is_null = Q(object_ref__membershippersonfirstciteddate__value__isnull=True)

                    commander_end = Q(object_ref__membershippersonlastciteddate__value__gte=mem_start)
                    end_is_null = Q(object_ref__membershippersonlastciteddate__value__isnull=True)

                    commanders = child.membershippersonorganization_set\
                                      .filter(commander_start |\
                                              start_is_null)\
                                      .filter(commander_end |\
                                              end_is_null)\
                                      .order_by(last_cited_attr)

                    for commander in commanders:
                        # We need to calculate time overlap, so use a dict to
                        # stash information about this commander
                        info = {}
                        info['commander'] = commander.object_ref
                        info['organization'] = child

                        # Get start of the overlap between these two people,
                        # being sensitive to nulls

                        # First, try to get the commander of the child unit's
                        # start/end dates
                        c_start = commander.object_ref.firstciteddate.get_value()
                        c_end = commander.object_ref.lastciteddate.get_value()

                        if c_start and not no_end:
                            overlap_start = c_start.value
                        else:
                            # Once we have "ongoing" attributes, we'll be able to
                            # determine ongoing overlap; for now, mark it as
                            # "unknown"
                            overlap_start = 'Unknown'

                        if c_end and not no_start:
                            overlap_end = c_end.value
                        else:
                            # Ditto about "ongoing" attributes above
                            overlap_end = 'Unknown'

                        if overlap_start != 'Unknown' and overlap_end != 'Unknown':
                            # Convert to date objects to calculate delta
                            start = date(overlap_start.year,
                                         overlap_start.month,
                                         overlap_start.day)

                            end = date(overlap_end.year,
                                       overlap_end.month,
                                       overlap_end.day)

                            overlap_duration = (str((end - start).days) + ' days')
                        else:
                            overlap_duration = 'Unknown'

                        info['overlap_start'] = overlap_start
                        info['overlap_end'] = overlap_end
                        info['overlap_duration'] = overlap_duration

                        context['subordinates'].append(info)

        context['events'] = []
        events = context['person'].violationperpetrator_set.all()
        for event in events:
            context['events'].append(event.object_ref)

        return context


class PersonList(PaginatedList):
    model = Person
    template_name = 'person/list.html'
    orderby_lookup = {
        'name': 'personname__value',
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Highlight the correct nav tab in the template
        context['person_tab'] = 'selected-tab'
        context['search_term'] = 'a person'
        return context

class PersonCreate(BaseFormSetView):
    template_name = 'person/create.html'
    form_class = PersonForm
    success_url = reverse_lazy('create-membership')
    extra = 1
    max_num = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confidence_levels'] = CONFIDENCE_LEVELS

        context['organizations'] = self.request.session.get('organizations')
        context['source'] = Source.objects.get(id=self.request.session['source_id'])

        context['back_url'] = reverse_lazy('create-organization')
        context['skip_url'] = reverse_lazy('create-geography')

        return context

    def formset_invalid(self, formset):
        response = super().formset_invalid(formset)

        for index, form in enumerate(formset.forms):
            alias_ids = formset.data.get('form-{}-alias'.format(index))
            if alias_ids:
                for alias_id in alias_ids:
                    try:
                        person_alias = PersonAlias.objects.get(id=alias_id)
                    except ValueError:
                        person_alias = None
                    
                    if person_alias:
                        try:
                            form.aliases.append(org_alias)
                        except AttributeError:
                            form.aliases = [org_alias]
            else:
                form.aliases = None
        
        return response

    def formset_valid(self, formset):
        response = super().formset_valid(formset)
        num_forms = int(formset.data['form-TOTAL_FORMS'][0])

        self.people = []
        self.memberships = []

        self.source = Source.objects.get(id=self.request.session['source_id'])

        for i in range(0,num_forms):
            first = True

            form_prefix = 'form-{0}-'.format(i)

            form_keys = [k for k in formset.data.keys() \
                             if k.startswith(form_prefix)]

            name_id_key = 'form-{0}-name'.format(i)
            name_text_key = 'form-{0}-name_text'.format(i)
            division_id_key = 'form-{}-division_id'.format(i)

            name_id = formset.data[name_id_key]
            name_text = formset.data[name_text_key]
            division_id = formset.data[division_id_key]

            name_confidence = int(formset.data.get(form_prefix +
                                                   'name_confidence', 1))
            division_confidence = int(formset.data.get(form_prefix +
                                                       'division_confidence', 1))

            person_info = {
                'Person_PersonName': {
                    'value': name_text,
                    'confidence': name_confidence,
                    'sources': [self.source],
                },
                'Person_PersonDivisionId': {
                    'value': division_id,
                    'confidence': division_confidence,
                    'sources': [self.source],
                }
            }

            if name_id == 'None':
                return self.formset_invalid(formset)

            elif name_id == '-1':
                person = Person.create(person_info)

            else:
                person = Person.objects.get(id=name_id)
                person_info['Person_PersonName']['sources'] = self.sourcesList(person, 'name')
                person.update(person_info)

            alias_id_key = 'form-{0}-alias'.format(i)
            alias_text_key = 'form-{0}-alias_text'.format(i)
            alias_confidence = int(formset.data.get(form_prefix +
                                                    'alias_confidence', 1))

            aliases = formset.data.getlist(alias_text_key)

            for alias in aliases:

                alias_obj, created = Alias.objects.get_or_create(value=alias)

                pa_obj, created = PersonAlias.objects.get_or_create(object_ref=person,
                                                                    value=alias_obj,
                                                                    lang=get_language(),
                                                                    confidence=alias_confidence)

                pa_obj.sources.add(self.source)
                pa_obj.save()

            self.people.append(person)

            orgs_key = 'form-{0}-orgs'.format(i)
            orgs = formset.data.getlist(orgs_key)
            orgs_confidence = int(formset.data.get(form_prefix +
                                                   'orgs_confidence', 1))

            for org in orgs:
                mem_data = {
                    'MembershipPerson_MembershipPersonMember': {
                        'value': person,
                        'confidence': orgs_confidence,
                        'sources': [self.source],
                    },
                    'MembershipPerson_MembershipPersonOrganization': {
                        'value': Organization.objects.get(id=org),
                        'confidence': orgs_confidence,
                        'sources': [self.source],
                    }
                }
                membership = MembershipPerson.create(mem_data)
                self.memberships.append({
                    'person': str(person.name),
                    'organization': str(Organization.objects.get(id=org).name),
                    'membership': membership.id,
                    'first': first
                })
                first = False

        self.request.session['people'] = [{'id': p.id, 'name': p.name.get_value().value} \
                                                     for p in self.people]
        self.request.session['memberships'] = self.memberships
        return response

def person_autocomplete(request):
    term = request.GET.get('q')
    people = Person.objects.filter(personname__value__icontains=term).all()
    results = []
    for person in people:
        results.append({
            'text': str(person.name),
            'id': person.id,
        })
    return HttpResponse(json.dumps(results), content_type='application/json')

def alias_autocomplete(request):
    term = request.GET.get('q')
    alias_query = PersonAlias.objects.filter(value__value__icontains=term)
    results = []
    for alias in alias_query:
        results.append({
            'text': alias.value.value,
            'id': alias.value.id
        })
    return HttpResponse(json.dumps(results), content_type='application/json')

class PersonUpdate(BaseUpdateView):
    template_name = 'person/edit.html'
    form_class = PersonForm
    success_url = reverse_lazy('dashboard')
    sourced = True

    def post(self, request, *args, **kwargs):

        self.checkSource(request)
        
        self.aliases = request.POST.getlist('alias')

        return self.validateForm()
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        person = Person.objects.get(pk=self.kwargs['pk'])
        
        person_info = {
            'Person_PersonName': {
                'value': form.cleaned_data['name_text'],
                'confidence': 1,
                'sources': self.sourcesList(person, 'name'),
            },
            'Person_PersonDivisionId': {
                'value': form.cleaned_data['division_id'],
                'confidence': 1,
                'sources': self.sourcesList(person, 'division_id')
            }
        }
        
        person.update(person_info)

        if self.aliases:
            for alias in self.aliases:
                
                alias_obj, created = Alias.objects.get_or_create(value=alias)

                pa_obj, created = PersonAlias.objects.get_or_create(object_ref=person,
                                                                    value=alias_obj,
                                                                    lang=get_language())
                
                pa_obj.sources.add(self.source)
                pa_obj.save()
        
        messages.add_message(self.request, 
                             messages.INFO, 
                             'Person {} saved!'.format(form.cleaned_data['name_text']))

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = Person.objects.get(pk=self.kwargs['pk'])
        
        form_data = {
            'name': person.name.get_value(),
            'aliases': [i.get_value() for i in person.aliases.get_list()],
            'division_id': person.division_id.get_value(),
        }
        
        context['form_data'] = form_data
        context['title'] = _('Person')
        context['source_object'] = person
        context['memberships'] = MembershipPerson.objects.filter(
            membershippersonmember__value=person
        ).filter(membershippersonorganization__value__isnull=False)
        context['source'] = Source.objects.filter(id=self.request.GET.get('source_id')).first()

        if not self.sourced:
            context['source_error'] = 'Please include the source for your changes'


        return context

#############################################
###                                       ###
### Below here are currently unused views ###
### which we'll probably need eventually  ###
###                                       ###
#############################################

class PersonDelete(DeleteView):
    model = Person
    template_name = "delete_confirm.html"

    def get_context_data(self, **kwargs):
        context = super(PersonDelete, self).get_context_data(**kwargs)
        collector = NestedObjects(using=DEFAULT_DB_ALIAS)
        collector.collect([context['object']])
        deleted_elements = collector.nested()
        context['deleted_elements'] = deleted_in_str(deleted_elements)
        return context

    def get_object(self, queryset=None):
        obj = super(PersonDelete, self).get_object()

        return obj

def person_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="persons.csv"'

    terms = request.GET.dict()
    person_query = Person.search(terms)

    writer = csv.writer(response)
    for person in person_query:
        writer.writerow([
            person.id,
            person.name.get_value(),
            person.alias.get_value(),
            repr(person.deathdate.get_value())
        ])

    return response


