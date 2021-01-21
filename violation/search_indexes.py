from haystack import indexes

from search.base_search_indexes import SearchEntity
from sfm_pc.templatetags.countries import country_name


class ViolationIndex(SearchEntity, indexes.Indexable):

    '''
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
    '''

    description = indexes.CharField()
    end_date_year = indexes.CharField(faceted=True)
    first_allegation = indexes.DateTimeField()
    last_update = indxes.DateTimeField()
    location = indexes.CharField(faceted=True)
    perpetrator = indexes.MultiValueField()
    perpetrator_classification = indexes.MultiValueField(faceted=True)
    start_date_year = indexes.CharField(faceted=True)
    status = indexes.CharField()
    violation_type = indexes.MultiValueField(faceted=True)

    def get_model(self):
        from violation.models import Violation

        return Violation

    def prepare(self, object):
        self.prepared_data = super().prepare(object)

        self.prepared_data['content'] = self._prepare_content(self.prepared_data)
        self.prepared_data['country'] = self._prepare_country(self.prepared_data)

        start_date_year, end_date_year = self._prepare_citation_years(self.prepared_data)

        self.prepared_data.update({
            'start_date_year': start_date_year,
            'end_date_year': end_date_year,
        })

        return self.prepared_data

    def _prepare_citation_years(self, prepared_data):
        return (
            prepared_data['start_date'].split('-')[0],
            prepared_data['end_date'].split('-')[0],
        )

    def _prepare_content(self, prepared_data):
        '''
        perp_names, perp_aliases, perp_org_names, perp_org_aliases,
        perp_org_classes, vtypes, country, description, location_description,
        location_name, osmname, admin_l1_name, admin_l2_name
        '''
        ...

    def _prepare_country(self, prepared_data):
        division_id = object.division_id.get_value()

        if division_id:
            return [country_name(division_id)]

    def prepare_description(self, object):
        description = object.description.get_value()

        if description:
            return description.value

    def prepare_division_id(self, object):
        division_id = object.division_id.get_value()

        if division_id:
            return [division_id.value]

    def prepare_end_date(self, object):
        return self._format_date(object.enddate.get_value())

    def prepare_first_allegation(self, object):
        return self._format_date(object.first_allegation.get_value())

    def prepare_last_update(self, object):
        return self._format_date(object.last_update.get_value())

    def prepare_location(self, object):
        location_description = object.locationdescription.get_value()

        if location_description:
            return location_description.value

    def prepare_perpetrator(self, object):
        perps = object.perpetrator.get_list()

        if perps:
            perp_names = []

            # Move from PerpetratorPerson -> Person
            for perp in list(perp.get_value().value for perp in perps):
                perp_names.append(perp.name.get_value().value)

            return perp_names

    def prepare_perpetrator_classification(self, object):
        pcs = object.violationperpetratorclassification_set.all()

        if pcs:
            return [cls.value for cls in pcs]

    def prepare_published(self, object):
        return object.published

    def prepare_start_date(self, object):
        return self._format_date(object.startdate.get_value())

    def prepare_status(self, object):
        status = object.status.get_value()

        if status:
            return status.value

    def prepare_violation_type(self, object):
        vtypes = object.types.get_list()

        if vtypes:
            return [str(vt.get_value().value) for vt in vtypes]
