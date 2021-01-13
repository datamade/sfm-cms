from haystack import indexes

from organization.models import Organization
from person.models import Person
from source.models import Source
from violation.models import Violation


class OrganizationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
#    classification
#    membership
#    parent_name
#    adminlevel1
#    start_date
#    end_date

    def build_queryset(self, **kwargs):
        '''
        TODO: Potentially select some related objects
        '''
        return super().build_queryset(**kwargs)

    def _get_value(self, attr):
        val = attr.get_value()

        if val:
            return val.value

    def _get_list(self, attr):
        all_vals = [self_get_value(item) for item in attr.get_list()]
        not_null_vals = list(filter(None, all_vals))

        if not_null_vals:
            return not_null_vals

    def prepare_text(self, obj):
        name = self._get_value(obj.name)
        aliases = self._get_list(obj.aliases)
        classifications = self._get_list(obj.classifications)
        headquarters = self._get_list(obj.headquarters)
