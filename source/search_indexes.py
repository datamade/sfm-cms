from haystack import indexes

from search.base_search_indexes import SearchEntity
from sfm_pc.templatetags.countries import country_name


class SourceIndex(SearchEntity, indexes.Indexable):

    CONTENT_FIELDS = (
        'title',
    )

    url = indexes.CharField()
    title = indexes.CharField()
    publication = indexes.CharField(faceted=True)

    def get_model(self):
        from source.models import Source

        return Source

    def prepare_countries(self, object):
        return [object.publication_country]

    def prepare_end_date(self, object):
        return self._format_date(object.get_published_date())

    def prepare_publication(self, object):
        return object.publication

    def prepare_start_date(self, object):
        return self._format_date(object.get_published_date())

    def prepare_title(self, object):
        return object.title

    def prepare_url(self, object):
        return object.source_url
