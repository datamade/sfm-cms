from collections import OrderedDict

import djqscsv


class DownloadMixin:
    serializers = {
        'string': lambda x: str(x),
        'identity': lambda x: x,
        'division_id': lambda x: x.split(':')[-1] if x else x,
        'list': lambda x: '; '.join(str(elem) for elem in x if elem),
    }
    published_filters = {'published': True}

    class Meta:
        managed = False

    @classmethod
    def get_model(cls):
        try:
            return cls.model
        except AttributeError:
            raise NotImplementedError(
                'Inheritors of DownloadMixin must implement the model property'
            )

    @classmethod
    def render_to_csv_response(cls, division_id, filename, sources=False, confidences=False):
        # Get the queryset that will be used to write a CSV
        queryset = cls.objects.filter(division_id=division_id)

        # Retrieve the metadata we need for each field
        field_map = cls.get_field_map(sources, confidences)
        field_list = list(field_map.keys())
        qset_values = queryset.values(*field_list)

        # The field header map defines the headers that the CSV will use for
        # each queryset field
        field_header_map = {key: data['header'] for key, data in field_map.items()}

        # The field serializer map defines the serializers that should be used
        # to write each queryset field to a CSV field
        field_serializer_map = {key: data['serializer'] for key, data in field_map.items()}

        return djqscsv.render_to_csv_response(
            qset_values,
            field_header_map=field_header_map,
            field_serializer_map=field_serializer_map,
            field_order=field_list,
            filename=filename
        )

    @classmethod
    def get_materialized_view_sql_with_params(cls):
        Model = cls.get_model()
        queryset = Model.objects.filter(**cls.published_filters)

        field_map = cls.get_field_map(sources=True, confidences=True)
        annotated_qset = queryset.annotate(**{key: data['value'] for key, data in field_map.items()})
        field_list = list(field_map.keys())

        query, params = annotated_qset.values(*field_list).query.sql_with_params()
        query_prefix = 'CREATE MATERIALIZED VIEW {} AS'.format(cls._meta.db_table)
        query = '{} {}'.format(query_prefix, query)
        return query, params

    @classmethod
    def get_field_map(cls, sources=False, confidences=False):
        try:
            field_map = cls._get_field_map()
        except AttributeError:
            raise NotImplementedError(
                'Inheritors of DownloadMixin must implement the _get_field_map method'
            )
        else:
            return cls._filter_field_map(field_map, sources, confidences)

    @classmethod
    def _filter_field_map(cls, field_map, sources=False, confidences=False):
        """Filter sources and confidences from field_map as necessary."""
        fields = field_map.items()
        if sources is False:
            fields = [(key, val) for key, val in fields if not val.get('source')]
        if confidences is False:
            fields = [(key, val) for key, val in fields if not val.get('confidence')]
        return OrderedDict(fields)
