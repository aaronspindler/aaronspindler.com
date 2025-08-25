from functools import wraps
from django.utils.decorators import method_decorator
from .models import PageVisit
import logging

logger = logging.getLogger(__name__)

def track_page_visit(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
        
        # Log the page visit
        logger.info(f"Page visit: {request.path} | IP: {ip_address} | Method: {request.method} | User-Agent: {user_agent}")
        
        # Store in database
        try:
            PageVisit.objects.create(
                ip_address=ip_address,
                page_name=request.path
            )
            logger.debug(f"Page visit recorded in database for {request.path}")
        except Exception as e:
            logger.error(f"Failed to record page visit in database: {e}")

        return view_func(request, *args, **kwargs)
    
    return wrapper

def track_page_visit_cbv(cls):
    return method_decorator(track_page_visit, name='dispatch')(cls)
