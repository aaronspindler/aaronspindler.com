"""
Security-related models for request fingerprinting and tracking.
"""

from django.db import models


class IPAddress(models.Model):
    """
    Stores unique IP addresses with their geolocation data.

    Normalized design: geo_data is stored once per IP address, not per request.
    This reduces storage and allows efficient batch geolocation updates.
    """

    ip_address = models.GenericIPAddressField(unique=True, db_index=True)
    geo_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Geographic location data for IP address (city, country, lat/lon, etc.)",
    )

    # Timestamps for tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "IP Address"
        verbose_name_plural = "IP Addresses"

    def __str__(self):
        if self.geo_data:
            city = self.geo_data.get("city", "")
            country = self.geo_data.get("country", "")
            if city and country:
                return f"{self.ip_address} ({city}, {country})"
            return f"{self.ip_address} ({country})" if country else self.ip_address
        return self.ip_address


class Fingerprint(models.Model):
    hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA256 fingerprint excluding IP (for cross-IP tracking)",
    )

    # Metadata for analytics
    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen"]
        verbose_name = "Fingerprint"
        verbose_name_plural = "Fingerprints"
        indexes = [
            models.Index(fields=["hash"]),
        ]

    def __str__(self):
        return f"{self.hash[:16]}..."


class TrackedRequest(models.Model):
    """Tracks individual HTTP requests with fingerprinting and security analysis."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Normalized fingerprint reference
    fingerprint_obj = models.ForeignKey(
        Fingerprint,
        on_delete=models.CASCADE,
        related_name="tracked_requests",
        help_text="Normalized fingerprint reference",
    )

    # Request details - IP address as ForeignKey for normalized geo_data
    ip_address = models.ForeignKey(
        IPAddress,
        on_delete=models.CASCADE,
        related_name="tracked_requests",
        help_text="IP address (with shared geolocation data)",
    )
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
        related_name="tracked_requests",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tracked Request"
        verbose_name_plural = "Tracked Requests"
        indexes = [
            models.Index(fields=["ip_address", "-created_at"]),
            models.Index(fields=["is_suspicious", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.ip_address.ip_address} - {self.method} {self.path} - {self.created_at}"

    @property
    def geo_data(self):
        """Access geo_data from related IPAddress for backward compatibility."""
        return self.ip_address.geo_data if self.ip_address else None

    @classmethod
    def create_from_request(cls, request):
        """
        Create a TrackedRequest instance from a Django request object.

        Args:
            request: Django HttpRequest object

        Returns:
            TrackedRequest instance

        Note:
            Geolocation data is stored in the IPAddress model (one per IP).
            Only global/routable IPs are stored (middleware filters non-global IPs).
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

        # Get or create IPAddress record (normalized storage for geo_data)
        ip_address_obj, created = IPAddress.objects.get_or_create(
            ip_address=fp_data["ip_address"],
            defaults={"geo_data": None},  # geo_data populated later via management command
        )

        # Get or create Fingerprint record (normalized storage)
        from django.utils import timezone

        fingerprint_obj, fp_created = Fingerprint.objects.get_or_create(
            hash=fp_data["fingerprint_no_ip"],
            defaults={
                "first_seen": timezone.now(),
                "last_seen": timezone.now(),
            },
        )

        # Update last_seen if fingerprint already existed
        if not fp_created:
            Fingerprint.objects.filter(pk=fingerprint_obj.pk).update(
                last_seen=timezone.now(),
            )

        return cls.objects.create(
            fingerprint_obj=fingerprint_obj,
            ip_address=ip_address_obj,
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
