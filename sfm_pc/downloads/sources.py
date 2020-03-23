from collections import OrderedDict

from django.db import models
from django.db.models import F
from django_date_extensions.fields import ApproximateDateField

from sfm_pc.downloads import mixins
from source.models import Source, AccessPoint


class SourceDownload(mixins.DownloadMixin, models.Model):
    source_id = models.UUIDField(primary_key=True)
    source_title = models.TextField()
    source_type = models.TextField()
    source_author = models.TextField()
    source_publication = models.TextField()
    source_publication_country = models.TextField()
    source_published_date = ApproximateDateField()
    source_published_timestamp = models.DateTimeField()
    source_created_date = ApproximateDateField()
    source_created_timestamp = models.DateTimeField()
    source_uploaded_date = ApproximateDateField()
    source_uploaded_timestamp = models.DateTimeField()
    source_source_url = models.URLField()
    access_point_id = models.UUIDField()
    access_point_type = models.TextField()
    access_point_trigger = models.TextField()
    access_point_accessed_on = models.DateField()
    access_point_archive_url = models.URLField()

    model = Source
    published_filters = {}

    @classmethod
    def _get_field_map(cls):
        return OrderedDict([
            ('source_id', {
                'header': 'source:id:admin',
                'value': F('uuid'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_title', {
                'header': Source.get_spreadsheet_field_name('title'),
                'value': F('title'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_type', {
                'header': Source.get_spreadsheet_field_name('type'),
                'value': F('type'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_author', {
                'header': Source.get_spreadsheet_field_name('author'),
                'value': F('author'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_publication', {
                'header': Source.get_spreadsheet_field_name('publication'),
                'value': F('publication'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_publication_country', {
                'header': Source.get_spreadsheet_field_name('publication_country'),
                'value': F('publication_country'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_published_date', {
                'header': Source.get_spreadsheet_field_name('published_date'),
                'value': F('published_date'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_published_timestamp', {
                'header': Source.get_spreadsheet_field_name('published_timestamp'),
                'value': F('published_timestamp'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_created_date', {
                'header': Source.get_spreadsheet_field_name('created_date'),
                'value': F('created_date'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_created_timestamp', {
                'header': Source.get_spreadsheet_field_name('created_timestamp'),
                'value': F('created_timestamp'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_uploaded_date', {
                'header': Source.get_spreadsheet_field_name('uploaded_date'),
                'value': F('uploaded_date'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_uploaded_timestamp', {
                'header': Source.get_spreadsheet_field_name('uploaded_timestamp'),
                'value': F('uploaded_timestamp'),
                'serializer': cls.serializers['identity'],
            }),
            ('source_source_url', {
                'header': Source.get_spreadsheet_field_name('source_url'),
                'value': F('source_url'),
                'serializer': cls.serializers['identity'],
            }),
            ('access_point_id', {
                'header': 'source:access_point_id',
                'value': F('accesspoint__uuid'),
                'serializer': cls.serializers['identity'],
            }),
            ('access_point_type', {
                'header': AccessPoint.get_spreadsheet_field_name('type'),
                'value': F('accesspoint__type'),
                'serializer': cls.serializers['identity'],
            }),
            ('access_point_trigger', {
                'header': AccessPoint.get_spreadsheet_field_name('trigger'),
                'value': F('accesspoint__trigger'),
                'serializer': cls.serializers['identity'],
            }),
            ('access_point_accessed_on', {
                'header': AccessPoint.get_spreadsheet_field_name('accessed_on'),
                'value': F('accesspoint__accessed_on'),
                'serializer': cls.serializers['identity'],
            }),
            ('access_point_archive_url', {
                'header': AccessPoint.get_spreadsheet_field_name('archive_url'),
                'value': F('accesspoint__archive_url'),
                'serializer': cls.serializers['identity'],
            }),
        ])
