import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('pages')

class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware to log all HTTP requests for debugging in CapRover."""
    
    def process_request(self, request):
        """Log request details at the start of request processing."""
        request._start_time = time.time()
        
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Log the incoming request
        logger.info(f"Request started: {request.method} {request.path} | IP: {ip_address}")
        
        return None
    
    def process_response(self, request, response):
        """Log response details at the end of request processing."""
        # Calculate request duration
        if hasattr(request, '_start_time'):
            duration = (time.time() - request._start_time) * 1000  # Convert to milliseconds
            
            # Get IP address again for the response log
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR', 'unknown')
            
            # Log the response
            logger.info(
                f"Request completed: {request.method} {request.path} | "
                f"Status: {response.status_code} | "
                f"Duration: {duration:.2f}ms | "
                f"IP: {ip_address}"
            )
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions that occur during request processing."""
        logger.error(
            f"Request failed: {request.method} {request.path} | "
            f"Exception: {type(exception).__name__}: {str(exception)}"
        )
        return None