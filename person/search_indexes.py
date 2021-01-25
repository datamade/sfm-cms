from haystack import indexes

from search.base_search_indexes import SearchEntity
from sfm_pc.templatetags.countries import country_name


class PersonIndex(SearchEntity, indexes.Indexable):

    '''
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

    '''

    CONTENT_FIELDS = (
        'aliases',
        'countries',
        'name',
        'ranks',
        'roles',
    )

    aliases = indexes.MultiValueField()
    name = indexes.CharField()
    ranks = indexes.MultiValueField(faceted=True)
    roles = indexes.MultiValueField(faceted=True)
    titles = indexes.MultiValueField()
    start_date_year = indexes.CharField(faceted=True)
    end_date_year = indexes.CharField(faceted=True)

    def get_model(self):
        from person.models import Person

        return Person

    def prepare(self, object):
        self.prepared_data = super().prepare(object)

        self.prepared_data['content'] = self._prepare_content(self.prepared_data)
        self.prepared_data['countries'] = self._prepare_countries(self.prepared_data)

        start_date_year, end_date_year = self._prepare_citation_years(self.prepared_data)

        self.prepared_data.update({
            'start_date_year': start_date_year,
            'end_date_year': end_date_year,
        })

        return self.prepared_data

    def _prepare_citation_years(self, prepared_data):
        start_year, end_year = [None, None]

        if prepared_data['start_date']:
            start_year = prepared_data['start_date'].split('-')[0]

        if prepared_data['end_date']:
            end_year = prepared_data['end_date'].split('-')[0]

        return (start_year, end_year)

    def _prepare_countries(self, prepared_data):
        countries = set()

        for division in prepared_data['division_ids']:
            countries.update([country_name(division)])

        return list(countries)

    def prepare_aliases(self, object):
        return [als.get_value().value for als in object.aliases.get_list()]

    def prepare_division_ids(self, object):
        division_ids = set()

        # Start by getting the division ID recorded for the person
        person_division_id = object.division_id.get_value()

        if person_division_id:
            division_ids.update([person_division_id.value])

        memberships = [mem.object_ref for mem in object.memberships]

        for membership in memberships:
            org = membership.organization.get_value()

            if org:
                org = org.value

                # We also want to index the person based on the countries
                # their member units have operated in
                org_division_id = org.division_id.get_value()

                if org_division_id:
                    division_ids.update([org_division_id.value])

        return list(division_ids)

    def prepare_end_date(self, object):
        last_cited = None

        memberships = [mem.object_ref for mem in object.memberships]

        if memberships:
            for membership in memberships:
                org = membership.organization.get_value()

                if org:
                    org = org.value
                    lcd = membership.lastciteddate.get_value()

                    if lcd:
                        if last_cited:
                            if lcd.value > last_cited.value:
                                last_cited = lcd
                        else:
                            last_cited = lcd

        if last_cited:
            return self._format_date(last_cited)

    def prepare_name(self, object):
        return object.name.get_value().value

    def prepare_published(self, object):
        return object.published

    def prepare_start_date(self, object):
        first_cited = None

        memberships = [mem.object_ref for mem in object.memberships]

        if memberships:
            for membership in memberships:
                org = membership.organization.get_value()

                if org:
                    org = org.value
                    fcd = membership.firstciteddate.get_value()

                    if fcd:
                        if first_cited:
                            if fcd.value < first_cited.value:
                                first_cited = fcd
                        else:
                            first_cited = fcd

        if first_cited:
            return self._format_date(first_cited)

    def prepare_ranks(self, object):
        ranks = set()

        memberships = [mem.object_ref for mem in object.memberships]

        for membership in memberships:
            rank = membership.rank.get_value()

            if rank:
                ranks.add(rank.value.value)

        return list(ranks)

    def prepare_roles(self, object):
        roles = set()

        memberships = [mem.object_ref for mem in object.memberships]

        for membership in memberships:
            role = membership.role.get_value()

            if role:
                roles.add(role.value.value)

        return list(roles)

    def prepare_titles(self, object):
        titles = set()

        memberships = [mem.object_ref for mem in object.memberships]

        for membership in memberships:
            title = membership.title.get_value()

            if title:
                titles.add(title.value)

        return list(titles)
