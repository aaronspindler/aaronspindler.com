from functools import wraps
from django.utils.decorators import method_decorator
from django.db import OperationalError, DatabaseError
from .models import PageVisit
import logging
import socket

logger = logging.getLogger(__name__)

def track_page_visit(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            # Get IP address with error handling
            ip_address = _get_client_ip_safe(request)
            
            # Get user agent
            user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')[:255]  # Limit length for DB field
            
            # Log the page visit
            logger.info(f"Page visit: {request.path} | IP: {ip_address} | Method: {request.method} | User-Agent: {user_agent}")
            
            # Store in database with specific error handling
            try:
                PageVisit.objects.create(
                    ip_address=ip_address,
                    page_name=request.path[:255]  # Ensure it fits in DB field
                )
                logger.debug(f"Page visit recorded in database for {request.path}")
            except (OperationalError, DatabaseError) as e:
                # Database connection issues (like DNS resolution failures)
                logger.error(f"Database connection error when recording page visit: {e.__class__.__name__}: {e}")
            except socket.gaierror as e:
                # DNS resolution error specifically
                logger.error(f"DNS resolution error when recording page visit: {e}")
            except Exception as e:
                # Other unexpected errors
                logger.error(f"Unexpected error recording page visit: {e.__class__.__name__}: {e}", exc_info=True)
        except Exception as e:
            # Log error but don't break the view
            logger.error(f"Error in track_page_visit decorator: {e}", exc_info=True)

        # Always execute the view function, regardless of tracking errors
        return view_func(request, *args, **kwargs)
    
    return wrapper

def _get_client_ip_safe(request):
    """
    Safely extract client IP address from request.
    Returns 'unknown' if extraction fails.
    """
    try:
        # Check for X-Forwarded-For header (when behind proxy/load balancer)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, get the first one
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            # Fall back to REMOTE_ADDR
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Validate IP address isn't empty
        if not ip_address or ip_address == '':
            return 'unknown'
            
        return ip_address
    except Exception as e:
        logger.debug(f"Error extracting IP address in decorator: {e}")
        return 'unknown'

def track_page_visit_cbv(cls):
    return method_decorator(track_page_visit, name='dispatch')(cls)
