"""
Request fingerprinting middleware for security and analytics.
"""
import logging
from django.core.exceptions import MiddlewareNotUsed
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestFingerprintMiddleware(MiddlewareMixin):
    """
    Middleware to track request fingerprints for security and analytics.
    
    This middleware creates a RequestFingerprint record for each request,
    storing IP address, user agent, headers, and detecting suspicious patterns.
    """
    
    def __init__(self, get_response):
        """Initialize middleware with error handling."""
        super().__init__(get_response)
        try:
            logger.debug("RequestFingerprintMiddleware initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RequestFingerprintMiddleware: {e}")
            raise MiddlewareNotUsed(f"RequestFingerprintMiddleware disabled: {e}")
    
    def process_request(self, request):
        """
        Track request fingerprint.
        
        Creates a RequestFingerprint record asynchronously to avoid blocking
        the request processing.
        """
        try:
            # Import here to avoid circular imports
            from utils.models import RequestFingerprint
            
            # Skip certain paths to avoid excessive logging
            skip_paths = [
                '/static/',
                '/media/',
                '/favicon.ico',
                '/robots.txt',
                '/health',
                '/admin/jsi18n/',
            ]
            
            # Check if we should skip this path
            if any(request.path.startswith(path) for path in skip_paths):
                return None
            
            # Create fingerprint record
            fingerprint = RequestFingerprint.create_from_request(request)
            
            # Attach to request for potential use in views
            request.fingerprint = fingerprint
            
            # Log if suspicious
            if fingerprint.is_suspicious:
                logger.warning(
                    f"Suspicious request detected: {request.method} {request.path} | "
                    f"IP: {fingerprint.ip_address} | Reason: {fingerprint.suspicious_reason}"
                )
            
        except Exception as e:
            # Don't block requests if fingerprinting fails
            logger.error(f"Error creating request fingerprint: {e}", exc_info=True)
        
        return None

