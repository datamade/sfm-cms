from uuid import uuid4

from django.contrib import messages
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import redirect
from django.views.generic.edit import FormView
from django.views.generic.edit import ModelFormMixin
from django.views.generic import ListView, DetailView, DeleteView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.cache import cache_page, never_cache
from django.utils.decorators import method_decorator
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse

from reversion.views import RevisionMixin

from countries_plus.models import Country

from extra_views import FormSetView

from source.models import AccessPoint
from association.models import Association
from emplacement.models import Emplacement
from person.models import Person
from organization.models import Organization
from membershipperson.models import MembershipPerson
from membershiporganization.models import MembershipOrganization
from violation.models import Violation


class CacheMixin(object):
    cache_timeout = 60 * 60 * 24

    def get_cache_timeout(self):
        return self.cache_timeout

    def dispatch(self, *args, **kwargs):
        return cache_page(self.get_cache_timeout())(super(CacheMixin, self).dispatch)(*args, **kwargs)


class JSONResponseMixin(object):
    def render_to_json_response(self, context, **response_kwargs):
        return JsonResponse(
            self.get_data(context),
            **response_kwargs
        )

    def get_data(self, context):
        try:
            del context['view']
        except (KeyError, TypeError):
            pass
        # Make sure things are JSON serializable
        return context


class CreateUpdateMixin(object):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countries'] = Country.objects.all()
        return context

    def form_invalid(self, form):
        for field in form.fields.values():
            if hasattr(field, 'new_instances'):
                for model in field.new_instances:
                    model.delete()

        return super().form_invalid(form)


class BaseDetailView(DetailView):
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        # Pass in a dictionary of models so that child views can reference
        # model metadata.
        context['models'] = {
            'Association': Association,
            'Emplacement': Emplacement,
            'MembershipOrganization': MembershipOrganization,
            'Person': Person,
            'MembershipPerson': MembershipPerson,
            'Violation': Violation,
            'Organization': Organization
        }
        return context

    def get_queryset(self):

        queryset = super().get_queryset()

        if self.request.user.is_authenticated:
            return queryset
        else:
            return queryset.filter(published=True)


@method_decorator([never_cache, transaction.atomic], name='dispatch')
class BaseEditView(LoginRequiredMixin,
                   CreateUpdateMixin,
                   ModelFormMixin,
                   RevisionMixin):
    '''
    SubClasses need to implement meta like so:

        model = Person
        slug_field = 'uuid'
        slug_field_kwarg = 'slug'
        context_object_name = 'person'

    They also need to provide a 'get_success_url' method
    '''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['source_info'] = {}

        for form_field in self.request.POST:
            if form_field.endswith('_source'):
                value = self.request.POST.getlist(form_field)
                context['source_info'][form_field] = AccessPoint.objects.filter(uuid__in=value)

        context['confidence_choices'] = {
            '1': _('Low'),
            '2': _('Medium'),
            '3': _('High'),
        }

        return context


class BaseUpdateView(BaseEditView, UpdateView):
    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['post_data'] = self.request.POST
        return form_kwargs


class BaseCreateView(BaseEditView, CreateView):
    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['post_data'] = self.request.POST
        return form_kwargs


class BaseDeleteView(LoginRequiredMixin, DeleteView):
    """
    Base view for deleting objects, providing a little extra context.
    """
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['related_entities'] = self.get_related_entities()
        return context

    def get_cancel_url(self):
        """
        Return the route that the Cancel button should link to in the template.
        """
        raise NotImplementedError('This method must be implemented on children.')

    def get_related_entities(self):
        """
        Return all of the entities that have been linked to this entity. These
        related entities must be deleted before the entity can be deleted.
        """
        # Return nothing by default so that related entities won't block deletion.
        # Leave it up to the child classes to decide whether and how to retrieve
        # related entities.
        return []


class BaseDeleteRelationshipView(BaseDeleteView):
    """
    Base view for deleting a relationship between two entities, e.g. a Composition
    between two Organizations.
    """
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['delete_obj_1'], context['delete_obj_2'] = self.get_objects_to_update()
        return context

    def get_objects_to_update(self):
        """
        Return a tuple of the two objects that are implicated by this deletion.
        For example, if the user is deleting an Organization Composition, this
        method should return the two Organizations that are linked by the
        Composition in question.
        """
        raise NotImplementedError('This method must be implemented on children.')
