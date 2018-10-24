import threading
import uuid

import requests

import reversion

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django_date_extensions.fields import ApproximateDateField

from sfm_pc.utils import VersionsMixin


def get_deleted_user():
    return get_user_model().objects.get_or_create(username='deleted user')[0]


@reversion.register()
class Source(models.Model, VersionsMixin):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.TextField()
    publication = models.TextField(null=True)
    publication_country = models.CharField(max_length=1000, null=True)
    published_on = ApproximateDateField()
    source_url = models.URLField(max_length=1000, null=True, blank=True)

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

    def get_evidenced(self):
        evidenced = []

        for prop in dir(self):

            if prop.endswith('_related'):
                related = getattr(self, prop).all()

                if related:

                    for rel in related:
                        evidenced.append(rel)

        return evidenced

    @property
    def archive_urls(self):
        return ' | '.join(a.archive_url for a in self.accesspoint_set.all())

    @property
    def revert_url(self):
        from django.core.urlresolvers import reverse
        return reverse('revert-source', args=[self.uuid])

@reversion.register()
class AccessPoint(models.Model, VersionsMixin):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    page_number = models.CharField(max_length=255, null=True, blank=True)
    accessed_on = models.DateField(null=True, blank=True)
    archive_url = models.URLField(max_length=1000, null=True, blank=True)
    source = models.ForeignKey(Source, null=True, to_field='uuid')

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET(get_deleted_user))

    def __str__(self):
        return '{0} {1}'.format(self.source, self.archive_url)


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
