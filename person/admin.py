import reversion

from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from .models import Person, PersonName, PersonAlias


class PersonAdmin(admin.ModelAdmin):
    pass


class PersonNameAdmin(TranslationAdmin):
    group_fieldsets = True


class PersonAliasAdmin(reversion.admin.VersionAdmin):
    pass


admin.site.register(Person, PersonAdmin)
admin.site.register(PersonName, PersonNameAdmin)
admin.site.register(PersonAlias, PersonAliasAdmin)
