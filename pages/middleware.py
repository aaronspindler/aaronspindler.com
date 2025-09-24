import logging
import time
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import MiddlewareNotUsed

logger = logging.getLogger('pages')

class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware to log all HTTP requests for debugging in CapRover."""
    
    def __init__(self, get_response):
        """Initialize middleware with error handling."""
        super().__init__(get_response)
        try:
            logger.debug("RequestLoggingMiddleware initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RequestLoggingMiddleware: {e}")
            raise MiddlewareNotUsed(f"RequestLoggingMiddleware disabled due to initialization error: {e}")
    
    def process_request(self, request):
        """Log request details at the start of request processing."""
        try:
            request._start_time = time.time()
            ip_address = self._get_client_ip(request)
            logger.info(f"Request started: {request.method} {request.path} | IP: {ip_address}")
            
        except Exception as e:
            logger.error(f"Error in process_request for {request.path}: {e}", exc_info=True)
            # Ensure start time is set even if logging fails
            if not hasattr(request, '_start_time'):
                request._start_time = time.time()
        
        return None
    
    def process_response(self, request, response):
        """Log response details at the end of request processing."""
        try:
            if hasattr(request, '_start_time'):
                duration = (time.time() - request._start_time) * 1000  # Convert to milliseconds
                ip_address = self._get_client_ip(request)
                
                logger.info(
                    f"Request completed: {request.method} {request.path} | "
                    f"Status: {response.status_code} | "
                    f"Duration: {duration:.2f}ms | "
                    f"IP: {ip_address}"
                )
        except Exception as e:
            logger.error(f"Error in process_response for {getattr(request, 'path', 'unknown path')}: {e}", exc_info=True)
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions that occur during request processing."""
        try:
            method = getattr(request, 'method', 'UNKNOWN')
            path = getattr(request, 'path', 'unknown path')
            ip_address = self._get_client_ip(request)
            
            duration_str = ""
            if hasattr(request, '_start_time'):
                duration = (time.time() - request._start_time) * 1000
                duration_str = f" | Duration: {duration:.2f}ms"
            
            logger.error(
                f"Request failed: {method} {path} | "
                f"IP: {ip_address}{duration_str} | "
                f"Exception: {type(exception).__name__}: {str(exception)}",
                exc_info=True  # This will include the full traceback
            )
        except Exception as e:
            # Fallback error logging if the enhanced logging fails
            logger.error(f"Error in process_exception: {e}. Original exception: {exception}", exc_info=True)
        
        return None
    
    def _get_client_ip(self, request):
        """
        Extract client IP address from request with error handling.
        Handles X-Forwarded-For header for requests behind proxies.
        """
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                # X-Forwarded-For can contain multiple IPs, get the first one
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR', 'unknown')
            
            return ip_address
        except Exception as e:
            logger.debug(f"Error extracting IP address: {e}")
            return 'unknown'