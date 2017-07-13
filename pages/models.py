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

