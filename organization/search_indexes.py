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
    country = indexes.MultiValueField()
    division_id = indexes.MultiValueField()
    start_date = indexes.DateTimeField(faceted=True)
    end_date = indexes.DateTimeField(faceted=True)

    def prepare_location(self, object):
        return None

    def prepare_entity_id(self, object):
        return object.uuid

    def _prepare_content(self, prepared_data):
        content = []

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


class Organization(SearchEntity, indexes.Indexable):

    '''
    {
        'id': org_id,
        'entity_type': 'Organization',
        'content': content,  # name, aliases, classifications, headquarters, parent names, countries, exact location names, areas
        'location': '',  # disabled until we implement map search
        'published_b': organization.published,
        'country_ss': countries,
        'division_id_ss': division_ids,
        'start_date_dt': first_cited,
        'end_date_dt': last_cited,
        'open_ended_s': open_ended,
        'organization_name_s': name,
        'organization_parent_name_ss': parent_names,
        'organization_parent_count_i': parent_count,
        'organization_membership_ss': memberships,
        'organization_classification_ss': classes,
        'organization_classification_count_i': class_count,
        'organization_alias_ss': aliases,
        'organization_headquarters_s': hq,
        'organization_exact_location_ss': exactloc_names,
        'organization_site_count_i': last_site_exists,
        'organization_country_count_i': country_count,
        'organization_area_ss': areas,
        'organization_start_date_dt': first_cited,
        'organization_end_date_dt': first_cited,
        'organization_adminlevel1_ss': list(admin_l1_names),
        'text': content
    }
    '''

    CONTENT_FIELDS = (
        'name',
        'alias',
        'classification',
        'headquarters',
        'parent_name',
        'country',
        'exact_location',
        'area',
    )

    open_ended = indexes.CharField()
    name = indexes.CharField()
    parent_name = indexes.MultiValueField(faceted=True)
    membership = indexes.MultiValueField(faceted=True)
    classification = indexes.MultiValueField(faceted=True)
    alias = indexes.MultiValueField()
    headquarters = indexes.CharField()
    exact_location = indexes.MultiValueField()
    area = indexes.MultiValueField()
    adminlevel1 = indexes.MultiValueField(faceted=True)

    def get_model(self):
        # For some reason, Haystack doesn't want to discover the index if we
        # import the model into the global namespace for this module. So,
        # import it here.
        from organization.models import Organization

        return Organization

    def prepare(self, object):
        self.prepared_data = super().prepare(object)

        self.prepared_data['content'] = self._prepare_content(self.prepared_data)

        return self.prepared_data

    def prepare_country(self, object):
        ...

    def prepare_published(self, object):
        parents = object.parent_organization.all()

        return all([p.value.published for p in parents])

    def prepare_division_id(self, object):
        division_ids = set()

        # Start by getting the division ID recorded for this org
        org_division_id = object.division_id.get_value()
        if org_division_id:
            division_ids.update([org_division_id.value])

        # Grab foreign key sets
        emplacements = object.emplacementorganization_set.all()

        for emp in emplacements:
            emp = emp.object_ref
            site = emp.site.get_value()

            if site:
                exactloc_name = site.value.name
                emp_division_id = site.value.division_id

                if emp_division_id:
                    division_ids.update([emp_division_id])

        return list(division_ids)

    def prepare_start_date(self, object):
        return self._format_date(object.firstciteddate.get_value())

    def prepare_end_date(self, object):
        return self._format_date(object.lastciteddate.get_value())

    def prepare_open_ended(self, object):
        open_ended = object.open_ended.get_value()

        if open_ended:
            return open_ended.value

    def prepare_name(self, object):
        return object.name.get_value().value

    def prepare_parent_name(self, object):
        parent_names = []

        for parent in object.parent_organization.all():
            # `parent_organization` returns a list of CompositionChilds,
            # so we have to jump through some hoops to get the foreign
            # key value
            composition = parent.object_ref
            parent = composition.parent.get_value().value
            parent_name = parent.name.get_value().value
            parent_names.append(parent_name)

        return parent_names

    def prepare_membership(self, object):
        memberships = []

        for membership in object.membershiporganizationmember_set.all():
            # Similar to parents, we have to traverse the directed graph
            # in order to get the entities we want
            org = membership.object_ref.organization.get_value().value

            if org.name.get_value():
                memberships.append(org.name.get_value())

        return memberships

    def prepare_classification(self, object):
        return [cls.get_value().value for cls in object.classification.get_list()]

    def prepare_alias(self, object):
        return [als.get_value().value for als in object.aliases.get_list()]

    def prepare_headquarters(self, object):
        hq = object.headquarters.get_value()

        if hq:
            return hq.value

    def prepare_exact_location(self, object):
        exactloc_names = set()

        for emp in object.emplacementorganization_set.all():
            emp = emp.object_ref
            site = emp.site.get_value()

            if site:
                exactloc_name = site.value.name
                emp_division_id = site.value.division_id
                exactloc_names.add(exactloc_name)

        return list(exactloc_names)

    def prepare_area(self, object):
        areas = set()

        for assoc in object.associationorganization_set.all():
            area = assoc.object_ref.area.get_value()

            if area:
                area_name = area.value.name
                areas.update([area_name])

        return list(areas)

    def prepare_adminlevel1(self, object):
        admin_l1_names = set()

        for emp in object.emplacementorganization_set.all():
            emp = emp.object_ref
            site = emp.site.get_value()

            if site and site.value.adminlevel1:
                admin_l1_names.add(site.value.adminlevel1.name)

        return list(admin_l1_names)

'''
Person

{
    'id': person_id,
    'entity_type': 'Person',
    'content': content,  # name, aliases, roles, ranks, countries
    'location': '',  # disabled until we implement map search
    'published_b': person.published,
    'country_ss': countries,
    'division_id_ss': division_ids,
    'person_title_ss': titles,
    'person_name_s': name,
    'person_alias_ss': aliases,
    'person_alias_count_i': alias_count,
    'person_role_ss': roles,
    'person_rank_ss': ranks,
    'person_most_recent_rank_s': most_recent_rank,
    'person_most_recent_unit_s': most_recent_unit,
    'person_title_ss': titles,
    'person_current_rank_s': latest_rank,
    'person_current_role_s': latest_role,
    'person_current_title_s': latest_title,
    'person_first_cited_dt': first_cited,
    'person_last_cited_dt': last_cited,
    'start_date_dt': first_cited,
    'end_date_dt': last_cited,
    'text': content
}

-------------

Violation (Incident)

{
    'id': viol_id,
    'entity_type': 'Violation',
    'content': content,
    'location': '',
    'published_b': violation.published,
    'country_ss': country,
    'division_id_ss': division_id,
    'start_date_dt': start_date,
    'end_date_dt': end_date,
    'violation_type_ss': vtypes,
    'violation_type_count_i': vtype_count,
    'violation_description_t': description,
    'violation_start_date_dt': start_date,
    'violation_end_date_dt': end_date,
    'violation_first_allegation_dt': first_allegation,
    'violation_last_update_dt': last_update,
    'violation_status_s': status,
    'violation_location_description_s': location_description,
    'violation_location_name_s': location_name,
    'violation_osmname_s': osmname,
    'violation_adminlevel1_s': admin_l1_name,
    'violation_adminlevel2_s': admin_l2_name,
    'perpetrator_ss': perps,
    'perpetrator_count_i': perp_count,
    'perpetrator_alias_ss': perp_aliases,
    'perpetrator_organization_ss': perp_orgs,
    'perpetrator_organization_count_i': perp_org_count,
    'perpetrator_organization_alias_ss': perp_org_aliases,
    'perpetrator_classification_ss': perp_org_classes,
    'perpetrator_classification_count_i': perp_org_class_count,
    'text': content
}

--------------

BEGIN: Org chart entities
https://github.com/security-force-monitor/sfm-cms/pull/416

--------------

Composition

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

Commmander

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

--------------

Source

{
    'id': source.uuid,
    'entity_type': 'Source',
    'content': content,
    'source_url_t': source.source_url,
    'source_title_t': source.title,
    'start_date_t': source.get_published_date(),
    'end_date_t': source.get_published_date(),
    'publication_s': source.publication,
    'country_s': source.publication_country,
    'country_ss': source.publication_country,
    'text': content
}
'''