from haystack import indexes

from search.base_search_indexes import SearchEntity
from sfm_pc.templatetags.countries import country_name


class ViolationIndex(SearchEntity, indexes.Indexable):

    CONTENT_FIELDS = (
        'countries',
        'description',
        'location_name',
        'violation_types',
    )

    description = indexes.CharField()
    end_date_year = indexes.CharField(faceted=True)
    first_allegation = indexes.DateTimeField()
    last_update = indexes.DateTimeField()
    location_name = indexes.CharField(faceted=True)
    perpetrators = indexes.MultiValueField()
    perpetrator_classifications = indexes.MultiValueField(faceted=True)
    start_date_year = indexes.CharField(faceted=True)
    status = indexes.CharField()
    violation_types = indexes.MultiValueField(faceted=True)

    def get_model(self):
        from violation.models import Violation

        return Violation

    def prepare(self, object):
        self.prepared_data = super().prepare(object)

        self.prepared_data['content'] = self._prepare_content(self.prepared_data, object)

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

    def _prepare_content(self, prepared_data, object, **kwargs):
        content = []

        for key in ('perpetrators', 'perpetrator_classifications'):
            if prepared_data[key]:
                content.extend(prepared_data[key])

        for perp in object.perpetrator.get_list():
            aliases = perp.aliases.get_list()

            if aliases:
                content.extend(a.get_value().value for a in aliases)

        perp_orgs = object.perpetratororganization.get_list()

        if perp_orgs:
            # Move from PerpetratorOrganization -> Organization
            perp_orgs = list(perp.get_value().value for perp in perp_orgs)

            for perp in perp_orgs:
                content.append(perp.name.get_value().value)

                org_aliases = perp.aliases.get_list()

                if org_aliases:
                    content.extend(a.get_value().value for a in org_aliases)

        return super()._prepare_content(prepared_data,
                                        initial_content=content)

    def prepare_countries(self, object):
        division_id = object.division_id.get_value()

        if division_id:
            return [country_name(division_id)]

    def prepare_description(self, object):
        description = object.description.get_value()

        if description:
            return description.value

    def prepare_division_ids(self, object):
        division_id = object.division_id.get_value()

        if division_id:
            return [division_id.value]

    def prepare_end_date(self, object):
        return self._format_date(object.enddate.get_value())

    def prepare_first_allegation(self, object):
        return self._format_date(object.first_allegation.get_value())

    def prepare_last_update(self, object):
        return self._format_date(object.last_update.get_value())

    def prepare_location_name(self, object):
        location_description = object.locationdescription.get_value()

        if location_description:
            return location_description.value

    def prepare_perpetrators(self, object):
        perps = object.perpetrator.get_list()

        if perps:
            perp_names = []

            # Move from PerpetratorPerson -> Person
            for perp in list(perp.get_value().value for perp in perps):
                perp_names.append(perp.name.get_value().value)

            return perp_names

    def prepare_perpetrator_classifications(self, object):
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

    def prepare_violation_types(self, object):
        vtypes = object.types.get_list()

        if vtypes:
            return [str(vt.get_value().value) for vt in vtypes]
