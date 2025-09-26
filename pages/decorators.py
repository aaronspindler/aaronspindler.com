from functools import wraps
from django.utils.decorators import method_decorator
from django.db import OperationalError, DatabaseError
from .models import PageVisit
import logging
import socket

logger = logging.getLogger(__name__)

def track_page_visit(view_func):
    """
    Decorator to track page visits in the database.
    Continues executing the view even if tracking fails.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            ip_address = _get_client_ip_safe(request)
            user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')[:255]  # Limit length for DB field
            
            # Sanitize user inputs to prevent log injection
            safe_path = request.path.replace('\n', '').replace('\r', '')[:255]
            safe_ip = ip_address.replace('\n', '').replace('\r', '')
            safe_ua = user_agent.replace('\n', '').replace('\r', '')
            logger.info(f"Page visit: {safe_path} | IP: {safe_ip} | Method: {request.method} | User-Agent: {safe_ua}")
            
            # Store in database with specific error handling
            try:
                # Use a valid IP address if 'unknown' is returned (PostgreSQL requirement)
                db_ip_address = ip_address if ip_address != 'unknown' else '127.0.0.1'
                PageVisit.objects.create(
                    ip_address=db_ip_address,
                    page_name=request.path[:255]  # Ensure it fits in DB field
                )
                safe_path = request.path.replace('\n', '').replace('\r', '')[:255]
                logger.debug(f"Page visit recorded in database for {safe_path}")
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
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, get the first one
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        if not ip_address or ip_address == '':
            return 'unknown'
            
        return ip_address
    except Exception as e:
        logger.debug(f"Error extracting IP address in decorator: {e}")
        return 'unknown'

def track_page_visit_cbv(cls):
    """Class-based view decorator for tracking page visits."""
    return method_decorator(track_page_visit, name='dispatch')(cls)
