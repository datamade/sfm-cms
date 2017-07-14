from django.contrib.admin import AdminSite
from django.contrib import admin
from django import forms
from django.db import models
from ckeditor.widgets import CKEditorWidget
from pages.models import About, FAQ, Help, Countries, CountryLink, \
                         CountryOverview


class SFMAdmin(AdminSite):
    site_header = 'Security Force Monitor - Site Administration'
    site_title = 'Admin - Security Force Monitor'


class AboutAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget},
    }


class FAQAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget},
    }


class HelpAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget},
    }


class CountriesAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget},
    }


class CountryLinkAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget},
    }


class CountryOverviewAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget},
    }


admin_site = SFMAdmin()

admin_site.register(About, AboutAdmin)
admin_site.register(FAQ, FAQAdmin)
admin_site.register(Help, HelpAdmin)
admin_site.register(Countries, CountriesAdmin)
admin_site.register(CountryOverview, CountryOverviewAdmin)
admin_site.register(CountryLink, CountryLinkAdmin)
