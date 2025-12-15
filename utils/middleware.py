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

    This middleware creates a TrackedRequest record for each request,
    storing IP address, user agent, headers, and detecting suspicious patterns.
    """

    def __init__(self, get_response):
        """Initialize middleware with error handling."""
        super().__init__(get_response)
        try:
            logger.debug("RequestFingerprintMiddleware initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RequestFingerprintMiddleware: {e}")
            raise MiddlewareNotUsed(f"RequestFingerprintMiddleware disabled: {e}") from e

    def process_request(self, request):
        """
        Track request fingerprint.

        Creates a TrackedRequest record asynchronously to avoid blocking
        the request processing.
        """
        try:
            # Import here to avoid circular imports
            from utils.models import TrackedRequest

            # Create fingerprint record
            tracked_request = TrackedRequest.create_from_request(request)

            # Attach to request for potential use in views
            request.tracked_request = tracked_request

            # Log if suspicious
            if tracked_request.is_suspicious:
                logger.warning(
                    f"Suspicious request detected: {request.method} {request.path} | "
                    f"IP: {tracked_request.ip_address} | Reason: {tracked_request.suspicious_reason}"
                )

        except Exception as e:
            # Don't block requests if fingerprinting fails
            logger.error(f"Error creating request fingerprint: {e}", exc_info=True)

        return None
