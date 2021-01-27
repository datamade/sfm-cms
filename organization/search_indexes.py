from haystack import indexes

from search.base_search_indexes import SearchEntity
from sfm_pc.templatetags.countries import country_name


class OrganizationIndex(SearchEntity, indexes.Indexable):

    CONTENT_FIELDS = (
        'name',
        'aliases',
        'classifications',
        'headquarters',
        'parent_names',
        'countries',
        'exact_locations',
        'areas',
    )

    open_ended = indexes.CharField()
    name = indexes.CharField()
    parent_names = indexes.MultiValueField(faceted=True)
    memberships = indexes.MultiValueField(faceted=True)
    classifications = indexes.MultiValueField(faceted=True)
    aliases = indexes.MultiValueField()
    headquarters = indexes.CharField()
    exact_locations = indexes.MultiValueField()
    areas = indexes.MultiValueField()
    adminlevel1s = indexes.MultiValueField(faceted=True)

    def get_model(self):
        # For some reason, Haystack doesn't want to discover the index if we
        # import the model into the global namespace for this module. So,
        # import it here.
        from organization.models import Organization

        return Organization

    def prepare(self, object):
        self.prepared_data = super().prepare(object)

        self.prepared_data['content'] = self._prepare_content(self.prepared_data)
        self.prepared_data['countries'] = self._prepare_countries(self.prepared_data)

        return self.prepared_data

    def _prepare_countries(self, prepared_data):
        countries = {country_name(division) for division in prepared_data['division_ids']}

        return list(countries)

    def prepare_published(self, object):
        parents = object.parent_organization.all()

        return all(p.value.published for p in parents)

    def prepare_division_ids(self, object):
        division_ids = set()

        # Start by getting the division ID recorded for this org
        org_division_id = object.division_id.get_value()
        if org_division_id:
            division_ids.add(org_division_id.value)

        # Grab foreign key sets
        emplacements = object.emplacementorganization_set.all()

        for emp in emplacements:
            emp = emp.object_ref
            site = emp.site.get_value()

            if site:
                exactloc_name = site.value.name
                emp_division_id = site.value.division_id

                if emp_division_id:
                    division_ids.add(emp_division_id)

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

    def prepare_parent_names(self, object):
        parent_names = []

        for parent in object.parent_organization.all():
            # `parent_organization` returns a list of CompositionChilds,
            # so we have to jump through some hoops to get the foreign
            # key value
            parent_obj = parent.object_ref.parent.get_value().value
            parent_name = parent_obj.name.get_value().value
            parent_names.append(parent_name)

        return parent_names

    def prepare_memberships(self, object):
        memberships = []

        for membership in object.membershiporganizationmember_set.all():
            # Similar to parents, we have to traverse the directed graph
            # in order to get the entities we want
            org = membership.object_ref.organization.get_value().value

            if org.name.get_value():
                memberships.append(org.name.get_value())

        return memberships

    def prepare_classifications(self, object):
        return [cls.get_value().value for cls in object.classification.get_list()]

    def prepare_aliases(self, object):
        return [als.get_value().value for als in object.aliases.get_list()]

    def prepare_headquarters(self, object):
        hq = object.headquarters.get_value()

        if hq:
            return hq.value

    def prepare_exact_locations(self, object):
        exactloc_names = set()

        for emp in object.emplacementorganization_set.all():
            site = emp.object_ref.site.get_value()

            if site:
                exactloc_name = site.value.name
                emp_division_id = site.value.division_id
                exactloc_names.add(exactloc_name)

        return list(exactloc_names)

    def prepare_areas(self, object):
        areas = set()

        for assoc in object.associationorganization_set.all():
            area = assoc.object_ref.area.get_value()

            if area:
                area_name = area.value.name
                areas.add(area_name)

        return list(areas)

    def prepare_adminlevel1s(self, object):
        admin_l1_names = set()

        for emp in object.emplacementorganization_set.all():
            site = emp.object_ref.site.get_value()

            if site and site.value.adminlevel1:
                admin_l1_names.add(site.value.adminlevel1.name)

        return list(admin_l1_names)
