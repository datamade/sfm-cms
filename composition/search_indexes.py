'''
TODO: Incomplete migration of composition index to Haystack.
'''
from haystack import indexes

from search.base_search_indexes import BaseEntity
from sfm_pc.templatetags.countries import country_name


class CompositionIndex(BaseEntity, indexes.Indexable):
    '''
    {
        'id': 'composition-{}'.format(org_id),
        'composition_parent_id_s': org_id,
        'composition_parent_name_s': name,
        'published_b': published,
        'entity_type': 'Composition',
        'content': 'Composition',
    }

    {
        'id': 'composition-{}'.format(composition.id),
        'composition_parent_id_s': str(parent.uuid),
        'composition_parent_pk_i': parent.id,
        'composition_parent_name_s': parent_name,
        'composition_child_id_s': org_id,
        'composition_child_pk_i': organization.id,
        'composition_child_name_s': name,
        'composition_daterange_dr': composition_daterange,
        'published_b': published,
        'entity_type': 'Composition',
        'content': 'Composition',
    }
    '''
    parent_id = indexes.CharField()
    parent_name = indexes.CharField()
    parent_pk = indexes.IntegerField()
    child_id = indexes.CharField()
    child_name = indexes.CharField()
    child_pk = indexes.IntegerField()
    # Is there an easy way to do DateRangeField in Haystack?
    # date_range = indexes.DateField()

class CommanderIndex(BaseEntity, indexes.Indexable):
    '''
    {
        'id': 'commander-{}'.format(membership.id),
        'commander_person_id_s': person_id,
        'commander_person_name_s': name,
        'commander_org_id_s': org.uuid,
        'commander_org_name_s': org.name.get_value().value,
        'commander_assignment_range_dr': assignment_range,
        'published_b': published,
        'entity_type': 'Commander',
        'content': 'Commander',
    }
    '''
    person_id = indexes.CharField()
    person_name = indexes.CharField()
    organization_id = indexes.CharField()
    organization_name = indexes.CharField()
    # date_range = indexes.DateField()

    def prepare_entity_type(self, object):
        return 'Commander'
