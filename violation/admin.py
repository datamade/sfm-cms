import reversion

from django.contrib import admin

from .models import Violation, ViolationStartDate, ViolationEndDate, \
    ViolationLocationDescription, ViolationDescription, ViolationPerpetrator, \
    ViolationPerpetratorOrganization, ViolationType, ViolationLocationName, \
    ViolationLocationId


class ViolationAdmin(admin.ModelAdmin):
    pass


class ViolationStartDateAdmin(reversion.admin.VersionAdmin):
    pass


class ViolationEndDateAdmin(reversion.admin.VersionAdmin):
    pass


class ViolationDescriptionAdmin(reversion.admin.VersionAdmin):
    pass


class ViolationLocationDescriptionAdmin(reversion.admin.VersionAdmin):
    pass


class ViolationLocationNameAdmin(reversion.admin.VersionAdmin):
    pass


class ViolationLocationIdAdmin(reversion.admin.VersionAdmin):
    pass


class ViolationPerpetratorAdmin(reversion.admin.VersionAdmin):
    pass


class ViolationPerpetratorOrganizationAdmin(reversion.admin.VersionAdmin):
    pass


class ViolationTypeAdmin(reversion.admin.VersionAdmin):
    pass


admin.site.register(ViolationType, ViolationTypeAdmin)
admin.site.register(ViolationPerpetratorOrganization, ViolationPerpetratorOrganizationAdmin)
admin.site.register(ViolationPerpetrator, ViolationPerpetratorAdmin)
admin.site.register(ViolationDescription, ViolationDescriptionAdmin)
admin.site.register(ViolationLocationDescription, ViolationLocationDescriptionAdmin)
admin.site.register(ViolationLocationName, ViolationLocationNameAdmin)
admin.site.register(ViolationLocationId, ViolationLocationIdAdmin)
admin.site.register(ViolationEndDate, ViolationEndDateAdmin)
admin.site.register(ViolationStartDate, ViolationStartDateAdmin)
