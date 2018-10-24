import reversion

from django.contrib import admin
from .models import (Organization, OrganizationName, OrganizationAlias,
                     OrganizationClassification)


class OrganizationAdmin(admin.ModelAdmin):
    pass


class OrganizationNameAdmin(reversion.admin.VersionAdmin):
    pass


class OrganizationAliasAdmin(reversion.admin.VersionAdmin):
    pass


class OrganizationClassificationAdmin(reversion.admin.VersionAdmin):
    pass


class ClassificationAdmin(admin.ModelAdmin):
    pass


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(OrganizationName, OrganizationNameAdmin)
admin.site.register(OrganizationAlias, OrganizationAliasAdmin)
admin.site.register(OrganizationClassification, OrganizationClassificationAdmin)
