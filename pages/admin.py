from django.contrib.admin import AdminSite
from django.contrib import admin
from django import forms

from .models import About, FAQ, Help, Countries


class SFMAdmin(AdminSite):
    site_header = 'Security Force Monitor - Site Administration'
    site_title = 'Admin - Security Force Monitor'


admin_site = SFMAdmin()

admin_site.register(About)
admin_site.register(FAQ)
admin_site.register(Help)
admin_site.register(Countries)

