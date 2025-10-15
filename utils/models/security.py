"""
Security-related models for request fingerprinting and tracking.
"""

from django.db import models


class HTTPStatusCode(models.Model):
    """HTTP status codes for reference."""

    code = models.IntegerField(unique=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.description}"


class RequestFingerprint(models.Model):
    """
    Stores request fingerprint data for security and analytics.
    """

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Request identification
    fingerprint = models.CharField(max_length=64, db_index=True, help_text="SHA256 fingerprint including IP")
    fingerprint_no_ip = models.CharField(max_length=64, db_index=True, help_text="SHA256 fingerprint excluding IP")

    # Request details
    ip_address = models.GenericIPAddressField(db_index=True)
    method = models.CharField(max_length=10, db_index=True)
    path = models.CharField(max_length=2048)
    is_secure = models.BooleanField(default=False)
    is_ajax = models.BooleanField(default=False)

    # User agent information
    user_agent = models.TextField(blank=True)
    browser = models.CharField(max_length=100, blank=True)
    browser_version = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=100, blank=True)
    device = models.CharField(max_length=100, blank=True)

    # Headers (stored as JSON)
    headers = models.JSONField(default=dict, blank=True)

    # Security flags
    is_suspicious = models.BooleanField(default=False, db_index=True)
    suspicious_reason = models.TextField(blank=True)

    # Optional user association
    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="request_fingerprints",
    )

    # Geolocation data (from ip-api.com)
    geo_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Geographic location data for IP address (city, country, lat/lon, etc.)",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "fingerprint"]),
            models.Index(fields=["ip_address", "-created_at"]),
            models.Index(fields=["is_suspicious", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.ip_address} - {self.method} {self.path} - {self.created_at}"

    @classmethod
    def create_from_request(cls, request):
        """
        Create a RequestFingerprint instance from a Django request object.

        Args:
            request: Django HttpRequest object

        Returns:
            RequestFingerprint instance

        Note:
            Geolocation data is not populated during request processing to avoid latency.
            Use the 'geolocate_fingerprints' management command to batch geolocate
            IP addresses after the records are created.
        """
        from utils.security import get_request_fingerprint_data, is_suspicious_request, parse_user_agent

        # Get fingerprint data
        fp_data = get_request_fingerprint_data(request)

        # Parse user agent
        ua_data = parse_user_agent(fp_data["user_agent"])

        # Check if suspicious
        is_susp, susp_reason = is_suspicious_request(request)

        # Get user if authenticated
        user = request.user if request.user.is_authenticated else None

        return cls.objects.create(
            fingerprint=fp_data["fingerprint"],
            fingerprint_no_ip=fp_data["fingerprint_no_ip"],
            ip_address=fp_data["ip_address"],
            method=fp_data["method"],
            path=fp_data["path"],
            is_secure=fp_data["is_secure"],
            is_ajax=fp_data["is_ajax"],
            user_agent=fp_data["user_agent"],
            browser=ua_data["browser"] or "",
            browser_version=ua_data["browser_version"] or "",
            os=ua_data["os"] or "",
            device=ua_data["device"] or "",
            headers=fp_data["headers"],
            is_suspicious=is_susp,
            suspicious_reason=susp_reason or "",
            user=user,
        )
