from django.conf import settings

from utils.models import LighthouseAudit


def lighthouse_badge(request):
    has_audit_data = LighthouseAudit.objects.exists()
    return {
        "show_lighthouse_badge": has_audit_data,
    }


def account_settings(request):
    return {
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
    }
