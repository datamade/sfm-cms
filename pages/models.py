from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.sites.models import Site


class About(models.Model):
    class Meta:  # Override admin page pluralization
        verbose_name_plural = 'About page'

    site = models.OneToOneField(Site)  # We only want there to be one


class FAQ(models.Model):
    class Meta:
        verbose_name_plural = 'FAQ page'

    site = models.OneToOneField(Site)


class Countries(models.Model):
    class Meta:
        verbose_name_plural = 'Countries page'

    site = models.OneToOneField(Site)


class Help(models.Model):
    class Meta:
        verbose_name_plural = 'Help page'

    site = models.OneToOneField(Site)


class CountryLink(models.Model):
    """
    Links to time-based views for a country box.
    """

    title = models.CharField(max_length=100)
    href = models.CharField(max_length=500)


def filepath(instance, filename):
    """
    Callable that returns a filepath for an uploaded image.
    """
    # file will be uploaded to MEDIA_ROOT/<country>/<filename>
    return '{0}/{1}/{2}'.format(instance.name,
                                filename)


class CountryOverview(models.Model):
    """
    Country boxes for the countries page.
    """

    name = models.CharField(max_length=100)

    image = models.FileField(
        upload_to=filepath,
        verbose_name='upload an image for this country',
        blank=True
    )

    background = models.TextField()

    first_link = models.ForeignKey(CountryLink, related_name='first_link')
    second_link = models.ForeignKey(CountryLink, related_name='second_link')
    third_link = models.ForeignKey(CountryLink, related_name='third_link')

    def filepath(instance, filename):
        """
        Callable that returns a filepath for an uploaded image.
        """
        # file will be uploaded to MEDIA_ROOT/<country>/<filename>
        return '{0}/{1}/{2}'.format(instance.name,
                                    filename)

    @property
    def num_persons(self):
        """
        Stub attribute that will eventually query the DB and return the number
        of people associated with this geography.
        """
        return 580

    @property
    def num_units(self):
        """
        Stub attribute that will eventually query the DB and return the number
        of units associated with this geography.
        """
        return 1200

