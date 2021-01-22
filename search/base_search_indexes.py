from django.db import models
from django.utils import dateformat
from haystack import indexes


class BaseEntity(indexes.SearchIndex):

    entity_id = indexes.CharField()
    entity_type = indexes.CharField()
    content = indexes.CharField(document=True, use_template=False)
    published = indexes.BooleanField()

    def index_queryset(self, using=None):
        return self.get_model().objects.all()

    def prepare_entity_type(self, object):
        return self.get_model().__name__


class SearchEntity(BaseEntity):

    location = indexes.LocationField()
    countries = indexes.MultiValueField(faceted=True)
    division_id = indexes.MultiValueField()
    start_date = indexes.DateTimeField(faceted=True)
    end_date = indexes.DateTimeField(faceted=True)

    def prepare_location(self, object):
        return None

    def prepare_entity_id(self, object):
        return object.uuid

    def _prepare_content(self, prepared_data, initial_content=[]):
        content = initial_content

        for field in self.CONTENT_FIELDS:
            field_value = prepared_data[field]

            if not field_value:
                continue

            if any(isinstance(field_value, cls) for cls in (str, models.Model)):
                field_value = [field_value]

            content.extend(field_value)

        return '; '.join(content)

    def _format_date(self, date):
        '''
        Format an ApproximateDateField for use in the Solr index.
        '''
        if date:
            # For now, we assign fuzzy dates bogus values for month/day if
            # they don't exist, but we should explore to see if Solr has better
            # ways of handling fuzzy dates
            date = dateformat.format(date.value, 'Y-m-d')
            date = date.replace('-00', '-01')
            date += 'T00:00:00Z'

        return date
