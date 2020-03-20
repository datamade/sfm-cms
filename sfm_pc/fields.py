from django.contrib.postgres.aggregates import ArrayAgg
from complex_fields.models import ComplexFieldContainer


class GetComplexFieldNameMixin:
    """
    Mixin to allow models with ComplexFields to retrieve the different types of
    field names for a given ComplexField.
    """
    @classmethod
    def get_field_model(cls, field_name):
        """
        Return the ComplexField model corresponding to a field on this model.
        """
        # Get the 0th ID instance, to indicate that we don't want a specific instance
        # (for more information on these methods, see the source code in the
        # complex_fields app)
        container = ComplexFieldContainer.field_from_str_and_id(
            cls.__name__.lower(), '0', field_name
        )
        return container.field_model()

    @classmethod
    def get_verbose_field_name(cls, field_name):
        """
        Get the canonical verbose name for a given field_name. For instance,
        the verbose name for Person.aliases would be 'Other names'.
        """
        field_model = cls.get_field_model(field_name)
        return field_model.field_name

    @classmethod
    def get_shortcode(cls, field_name):
        """
        Get the shortcode for a given field_name. For instance, the shortcode
        for Person.aliases would be 'p_on'.
        """
        field_model = cls.get_field_model(field_name)
        return field_model.shortcode

    @classmethod
    def get_spreadsheet_field_name(cls, field_name):
        """
        Get the spreadsheet field name for a given field_name. For instance,
        the spreadsheet field name for Person.name would be 'person:name'.
        """
        field_model = cls.get_field_model(field_name)
        return field_model.spreadsheet_field_name

    @classmethod
    def get_spreadsheet_confidence_field_name(cls, field_name):
        """
        Get the spreadsheet confidence field name for a given field_name. For
        instance, the spreadsheet confidence field name for Person.name would
        be 'person:name:confidence'.
        """
        field_model = cls.get_field_model(field_name)
        if hasattr(field_model, 'spreadsheet_confidence_field_name'):
            return getattr(field_model, 'spreadsheet_confidence_field_name')
        else:
            # If no confidence field name is specified, the default is usually
            # the spreadsheet field name with ":confidence" appended on
            return cls.get_spreadsheet_field_name(field_name) + ':confidence'

    @classmethod
    def get_spreadsheet_source_field_name(cls, field_name):
        """
        Get the spreadsheet source field name for a given field_name. For
        instance, the spreadsheet source field name for Person.name would
        be 'person:name:source'.
        """
        field_model = cls.get_field_model(field_name)
        if hasattr(field_model, 'spreadsheet_source_field_name'):
            return getattr(field_model, 'spreadsheet_source_field_name')
        else:
            # If no source field name is specified, the default is usually
            # the spreadsheet field name with ":source" appended on
            return cls.get_spreadsheet_field_name(field_name) + ':source'


class DistinctArrayAgg(ArrayAgg):
    # Allow ArrayAgg queries to optionally filter duplicate values.
    # This change was introduced in Django 2.0, which we are not yet supporting.
    # See: https://github.com/django/django/commit/b5393028bfc939adf14d0fa5e4088cddd3b9dfa1
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, **extra):
        super().__init__(expression, distinct='DISTINCT ' if distinct else '', **extra)
