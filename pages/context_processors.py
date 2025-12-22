from django.conf import settings


def resume_context(request):
    return {
        "RESUME_ENABLED": getattr(settings, "RESUME_ENABLED", False),
        "RESUME_FILENAME": getattr(settings, "RESUME_FILENAME", ""),
    }
