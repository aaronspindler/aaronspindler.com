from utils.models import LighthouseAudit


def lighthouse_badge(request):
    """
    Context processor to determine if Lighthouse badge should be displayed.
    Badge only shows when audit data exists.
    """
    has_audit_data = LighthouseAudit.objects.exists()
    return {
        'show_lighthouse_badge': has_audit_data,
    }

