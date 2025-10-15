from django.conf import settings


def resume_context(request):
    """Add resume settings to the template context."""
    return {
        "RESUME_ENABLED": getattr(settings, "RESUME_ENABLED", False),
        "RESUME_FILENAME": getattr(settings, "RESUME_FILENAME", ""),
    }
