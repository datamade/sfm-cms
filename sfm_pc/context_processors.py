from django.conf import settings


def enable_analytics(request):
    return {'ENABLE_ANALYTICS': not settings.DEBUG}
