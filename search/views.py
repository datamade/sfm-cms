from datetime import datetime

from django.core.urlresolvers import reverse

from haystack.forms import FacetedSearchForm
from haystack.generic_views import SearchMixin, FacetedSearchView
from haystack.inputs import Raw
from haystack.query import SearchQuerySet, SQ

from source.models import Source
from organization.models import Organization
from emplacement.models import Emplacement
from person.models import Person
from membershipperson.models import MembershipPerson
from violation.models import Violation


class WWICSearchForm(FacetedSearchForm):

    def _make_fuzzy_query(self):
        illegal_chars = '''|&*/\!{[]}"'~-+()^:'''

        clean_q = self.cleaned_data['q'].strip()

        for char in illegal_chars:
            clean_q.replace(char, '')

        return ' '.join(term + '~' for term in clean_q.split())

    def no_query_found(self):
        return self.searchqueryset.load_all()

    def search(self):
        sqs = super().search()

        fuzzy_query = self._make_fuzzy_query()

        if fuzzy_query:
            return sqs.filter(content=Raw(self._make_fuzzy_query()))

        return self.no_query_found()


class HaystackSearchView(FacetedSearchView):

    context_object_name = 'results'

    facet_fields = [
        'adminlevel1s',
        'classifications',
        'countries',
        'end_date_year',
        'location_name',
        'memberships',
        'parent_names',
        'perpetrator_classifications',
        'publication',
        'ranks',
        'roles',
        'start_date_year',
        'violation_types',
    ]

    form_class = WWICSearchForm
    load_all = True
    template_name = 'search/search.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context['models'] =  {
            'Person': Person,
            'MembershipPerson': MembershipPerson,
            'Organization': Organization,
            'Emplacement': Emplacement,
            'Violation': Violation,
            'Source': Source
        }

        context.update({
            'user_query': self.request.GET.get('q'),
            'entity_type': self.request.GET.get('entity_type', 'Organization'),
            'location': self.request.GET.get('osm_id'),
            'radius': self.request.GET.get('radius'),
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
            'suggested_terms': self.queryset.spelling_suggestion(),  # omit query
            'q_filters': self.get_search_string(),
            'results_per_page': [5, 10, 15, 20, 25, 50],
            'download_urls': self.get_download_urls(),
        })

        context.update(self.get_facet_context())

        return context

    def get_paginate_by(self, queryset):
        return self.request.GET.get('rows', 25)

    def get_queryset(self):
        '''
        Fully override the get_queryset() method in order to pass additional
        parameters (mincount) to the facet() call.
        '''
        sqs = SearchQuerySet()

        for field in self.facet_fields:
            sqs = sqs.facet(field, mincount=1)

        entity_type = self.request.GET.get('entity_type', 'Organization')
        sort = self.request.GET.get('sort', None)

        search_filter = SQ(entity_type=entity_type)

        for bound, filter_kwarg in (
            ('start_date', 'start_date__gte'),
            ('end_date', 'end_date__lte')
        ):
            if self.request.GET.get(bound, None):
                formatted_date = parse_solr_date(self.request.GET[bound])
                search_filter &= SQ(**{filter_kwarg: formatted_date})

        sqs = sqs.filter(search_filter)

        if not self.request.user.is_authenticated:
            sqs = sqs.filter(published=True)

        if sort:
            sqs = sqs.order_by(sort)

        return sqs

    def get_search_string(self):
        params = self.request.GET.copy()

        for param in ('page', 'rows'):
            params.pop(param, None)

        return params.urlencode()

    def get_facet_context(self):
        selected_facets, selected_facet_values = [], {}

        for facet in self.request.GET.getlist('selected_facets'):
            facet, *value = facet.split(':')
            selected_facets.append(facet)

            if facet not in selected_facet_values:
                selected_facet_values[facet] = []

            selected_facet_values[facet].append(':'.join(value))

        return {
            'selected_facets': selected_facets,
            'selected_facet_values': selected_facet_values,
        }

    def get_download_urls(self):
        params = self.request.GET.urlencode()

        download_url = reverse('download')

        if params:
            download_url += '?' + params + '&'
        else:
            download_url += '/?'

        download_urls = {}

        for etype in ('Person', 'Organization', 'Violation'):
            download_urls[etype] = download_url + 'download_etype={0}'.format(etype)

        return download_urls


def parse_solr_date(value):
    # Set the default to a wildcard search
    parsed = '*'

    # Map legal input formats to the way that we want to
    # feed them into solr
    formats = {
        '%Y-%m-%d': '%Y-%m-%d',
        '%Y-%m': '%Y-%m-01',
        '%Y': '%Y-01-01',
        '%B %Y': '%Y-%m-01',
        '%b %Y': '%Y-%m-01',
        '%m/%Y': '%Y-%m-01',
        '%m/%d/%Y': '%Y-%m-%d',
    }

    for in_format, out_format in formats.items():
        try:
            parsed_input = datetime.strptime(value, in_format)
            parsed = datetime.strftime(parsed_input, out_format)
            parsed += 'T00:00:00Z'
            break

        except ValueError:
            pass

    return parsed
