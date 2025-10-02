from functools import wraps
from django.utils.decorators import method_decorator
import logging

logger = logging.getLogger(__name__)

def track_page_visit(view_func):
    """
    Decorator to log page visits for specific tracked pages.
    
    Note: Request fingerprinting and tracking is handled by RequestFingerprintMiddleware.
    This decorator provides additional logging for specific views that need explicit tracking.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            # Sanitize user inputs to prevent log injection
            safe_path = request.path.replace('\n', '').replace('\r', '')[:255]
            safe_ip = request.META.get('REMOTE_ADDR', 'unknown').replace('\n', '').replace('\r', '')
            safe_ua = request.META.get('HTTP_USER_AGENT', 'unknown')[:255].replace('\n', '').replace('\r', '')
            logger.info(f"Page visit: {safe_path} | IP: {safe_ip} | Method: {request.method} | User-Agent: {safe_ua}")
        except Exception as e:
            logger.error(f"Error in track_page_visit decorator: {e}", exc_info=True)

        # Always execute the view function, regardless of logging errors
        return view_func(request, *args, **kwargs)
    
    return wrapper

def track_page_visit_cbv(cls):
    """Class-based view decorator for tracking page visits."""
    return method_decorator(track_page_visit, name='dispatch')(cls)
