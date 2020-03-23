import threading
import uuid
import re

import requests

import reversion

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django_date_extensions.fields import ApproximateDateField

from sfm_pc.utils import VersionsMixin

from . import fields as source_fields


def get_deleted_user():
    return get_user_model().objects.get_or_create(username='deleted user')[0]


class GetSpreadsheetFieldNameMixin:
    """
    Mixin to allow models with Django fields to retrieve the
    spreadsheet_field_name for a given field.
    """
    @classmethod
    def get_spreadsheet_field_name(cls, field_name):
        return cls._meta.get_field(field_name).spreadsheet_field_name

    @classmethod
    def get_verbose_field_name(cls, field_name):
        return cls._meta.get_field(field_name).verbose_name.title()


@reversion.register(follow=['accesspoint_set'])
class Source(models.Model, GetSpreadsheetFieldNameMixin, VersionsMixin):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = source_fields.TextField(spreadsheet_field_name='source:title')
    type = source_fields.CharField(max_length=1000, null=True, blank=True, spreadsheet_field_name='source:type')
    author = source_fields.CharField(max_length=1000, null=True, blank=True, spreadsheet_field_name='source:author')
    publication = source_fields.TextField(null=True, spreadsheet_field_name='source:publication_name')
    publication_country = source_fields.CharField(max_length=1000, null=True, spreadsheet_field_name='source:publication_country')
    # We store both date and timestamp fields for the following values because
    # sometimes sources have partial dates and sometimes they have full
    # timestamps. In practice, these fields should be treated as mutually
    # exclusive, and the get_date() methods should be used to retrieve
    # the canonical value.
    published_date = source_fields.ApproximateDateField(
        verbose_name="publication date",
        blank=True,
        default='',
        spreadsheet_field_name='source:published_timestamp'
    )
    published_timestamp = source_fields.DateTimeField(
        verbose_name="publication timestamp",
        blank=True,
        null=True,
        spreadsheet_field_name='source:published_timestamp'
    )
    created_date = source_fields.ApproximateDateField(
        verbose_name="creation date",
        blank=True,
        default='',
        spreadsheet_field_name='source:created_timestamp'
    )
    created_timestamp = source_fields.DateTimeField(
        verbose_name="publication timestamp",
        blank=True,
        null=True,
        spreadsheet_field_name='source:created_timestamp'
    )
    uploaded_date = source_fields.ApproximateDateField(
        verbose_name="upload date",
        blank=True,
        default='',
        spreadsheet_field_name='source:uploaded_timestamp'
    )
    uploaded_timestamp = source_fields.DateTimeField(
        verbose_name="publication timestamp",
        blank=True,
        null=True,
        spreadsheet_field_name='source:uploaded_timestamp'
    )
    source_url = source_fields.URLField(max_length=1000, null=True, blank=True, spreadsheet_field_name='source:url')

    date_updated = models.DateTimeField(auto_now=True)
    date_added = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET(get_deleted_user))

    def __str__(self):
        if self.title is None:
            return ""
        return self.title

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('view-source', args=[self.uuid])

    def _get_date_or_timestamp(self, date_type):
        timestamp = getattr(self, '{}_timestamp'.format(date_type))
        date = getattr(self, '{}_date'.format(date_type))
        return timestamp if timestamp else date

    def get_published_date(self):
        """
        Get the canonical value for the date this Source was published. This
        method is useful because in practice published_date and
        published_timestamp should be mutually exclusive, and at runtime we don't
        necessarily know which one will be set for a given Source.
        """
        return self._get_date_or_timestamp('published')

    def get_created_date(self):
        return self._get_date_or_timestamp('created')

    def get_uploaded_date(self):
        return self._get_date_or_timestamp('uploaded')

    @property
    def related_entities(self):
        """
        Return a list of dicts representing the access points that are linked
        to this source.

        Dicts must include the following metadata:
            - name
            - archive_url
            - page_number
            - access_date
            - url (of the Edit view for the access point)
        """
        related_entities = []
        for point in self.accesspoint_set.all():
            related_entities.append({
                'name': str(point),
                'archive_url': point.archive_url,
                'page_number': point.trigger,
                'accessed_on': point.accessed_on,
                'url': reverse_lazy(
                    'update-access-point',
                    kwargs={'source_id': self.uuid, 'pk': point.uuid}
                )
            })
        return related_entities

    @property
    def revert_url(self):
        from django.core.urlresolvers import reverse
        return reverse('revert-source', args=[self.uuid])


@reversion.register()
class AccessPoint(models.Model, GetSpreadsheetFieldNameMixin, VersionsMixin):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    type = source_fields.CharField(max_length=1000, null=True, blank=True, spreadsheet_field_name='source:access_point_type')
    trigger = source_fields.CharField(max_length=255, null=True, blank=True, spreadsheet_field_name='source:access_point_trigger')
    accessed_on = source_fields.DateField(null=True, verbose_name='access date', spreadsheet_field_name='source:accessed_timestamp')
    archive_url = source_fields.URLField(max_length=1000, null=True, spreadsheet_field_name='source:archive_url')
    source = models.ForeignKey(Source, null=True, to_field='uuid')

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET(get_deleted_user))

    def __str__(self):
        point_name = self.archive_timestamp
        if self.trigger:
            # Check if the page number is a range; if so, indicate to ngettext
            # that the string should be plural. See:
            # https://docs.djangoproject.com/en/2.2/topics/i18n/translation/#pluralization
            is_range = 2 if ('-' in self.trigger or ', ' in self.trigger) else 1
            # Translators: This fragment references to the page numbers in an access point.
            pages_str = ngettext(
                '(Page %(pages)s)',
                '(Pages %(pages)s)',
                is_range
            ) % {
                'pages': self.trigger
            }
            point_name += ' ' + pages_str
        if self.accessed_on:
            point_name += ' - ' + _('Accessed on %(date)s') % {'date': self.accessed_on}
        return point_name

    @property
    def archive_timestamp(self):
        """Given an access point archive_url, parse the timestamp."""
        match = re.search(r"web\.archive\.org/web/(\d{14})/", self.archive_url)
        if match:
            return match.group(1)
        else:
            return _('No timestamp')

    @property
    def related_entities(self):
        """
        Return a list of dicts of all entities that are evidenced by this
        access point.

        Dicts must have the following keys:
            - name
            - entity_type
            - field_name
            - url (a link to edit the entity)
        """
        related_entities = []

        for prop in dir(self):
            if prop.endswith('_related'):
                related = getattr(self, prop).all()
                if related:
                    for entity in related:
                        record_type = entity.object_ref._meta.object_name
                        entity_metadata = {
                            'name': str(entity),
                            'record_type': record_type,
                            'field_name': entity._meta.model_name.replace(record_type.lower(), '').title(),
                            'value': entity.value,
                            'url': None
                        }
                        # Links for top-level entities
                        if record_type in ['Organization', 'Person', 'Violation']:
                            entity_metadata['url'] = reverse_lazy(
                                'edit-{}'.format(record_type.lower()),
                                args=[entity.object_ref.uuid]
                            )
                        # Standardized relationship links
                        elif record_type in ['Emplacement', 'Association']:
                            entity_metadata['url'] = reverse_lazy(
                                'edit-organization-{}'.format(record_type.lower()),
                                kwargs={
                                    'organization_id': entity.object_ref.organization.get_value().value.uuid,
                                    'pk': entity.object_ref.pk
                                }
                            )
                        # Irregular relationship links
                        elif record_type == 'Composition':
                            entity_metadata['url'] = reverse_lazy(
                                'edit-organization-composition',
                                kwargs={
                                    'organization_id': entity.object_ref.parent.get_value().value.uuid,
                                    'pk': entity.object_ref.pk
                                }
                            )
                        elif record_type == 'MembershipPerson':
                            entity_metadata['url'] = reverse_lazy(
                                'edit-organization-personnel',
                                kwargs={
                                    'organization_id': entity.object_ref.organization.get_value().value.uuid,
                                    'pk': entity.pk
                                }
                            )
                        elif record_type == 'MembershipOrganization':
                            entity_metadata['url'] = reverse_lazy(
                                'edit-organization-membership',
                                kwargs={
                                    'organization_id': entity.object_ref.organization.get_value().value.uuid,
                                    'pk': entity.pk
                                }
                            )
                        related_entities.append(entity_metadata)
        return related_entities


def archive_source_url(source):

    if source.source_url:
        wayback_host = 'http://web.archive.org'
        save_url = '{0}/save/{1}'.format(wayback_host, source.source_url)
        archived = requests.get(save_url)
        source.archive_url = '{0}{1}'.format(wayback_host,
                                             archived.headers['Content-Location'])
        source.save()

#@receiver(post_save, sender=Source)
def get_archived_url(sender, **kwargs):

    source = kwargs['instance']

    thread = threading.Thread(target=archive_source_url,
                              args=[source])
    thread.start()
