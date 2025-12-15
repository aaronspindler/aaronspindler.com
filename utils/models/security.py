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
    hash_with_ip = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA256 fingerprint including IP address",
    )
    hash_without_ip = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA256 fingerprint excluding IP (for cross-IP tracking)",
    )

    # Metadata for analytics
    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True)
    request_count = models.PositiveIntegerField(
        default=0,
        help_text="Cached count of requests with this fingerprint",
    )

    class Meta:
        ordering = ["-last_seen"]
        verbose_name = "Fingerprint"
        verbose_name_plural = "Fingerprints"
        indexes = [
            models.Index(fields=["hash_with_ip"]),
            models.Index(fields=["hash_without_ip"]),
            models.Index(fields=["-last_seen"]),
            models.Index(fields=["-request_count"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["hash_with_ip", "hash_without_ip"],
                name="unique_fingerprint_hashes",
            )
        ]

    def __str__(self):
        return f"{self.hash_with_ip[:16]}... (seen {self.request_count} times)"


class RequestFingerprint(models.Model):
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Normalized fingerprint reference
    fingerprint_obj = models.ForeignKey(
        Fingerprint,
        on_delete=models.CASCADE,
        related_name="requests",
        help_text="Normalized fingerprint reference (replaces fingerprint CharField fields)",
    )

    # DEPRECATED: Old fingerprint fields (will be removed after migration verification)
    # These are kept nullable during transition for backward compatibility
    fingerprint = models.CharField(
        max_length=64,
        db_index=True,
        null=True,
        blank=True,
        help_text="[DEPRECATED] SHA256 fingerprint including IP - use fingerprint_obj instead",
    )
    fingerprint_no_ip = models.CharField(
        max_length=64,
        db_index=True,
        null=True,
        blank=True,
        help_text="[DEPRECATED] SHA256 fingerprint excluding IP - use fingerprint_obj instead",
    )

    # Request details - IP address as ForeignKey for normalized geo_data
    ip_address = models.ForeignKey(
        IPAddress,
        on_delete=models.CASCADE,
        related_name="request_fingerprints",
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
        related_name="request_fingerprints",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "fingerprint"]),
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
        Create a RequestFingerprint instance from a Django request object.

        Args:
            request: Django HttpRequest object

        Returns:
            RequestFingerprint instance

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
        from django.db.models import F
        from django.utils import timezone

        fingerprint_obj, fp_created = Fingerprint.objects.get_or_create(
            hash_with_ip=fp_data["fingerprint"],
            hash_without_ip=fp_data["fingerprint_no_ip"],
            defaults={
                "first_seen": timezone.now(),
                "last_seen": timezone.now(),
                "request_count": 0,
            },
        )

        # Update last_seen and increment count if fingerprint already existed
        if not fp_created:
            fingerprint_obj.last_seen = timezone.now()
            fingerprint_obj.request_count = F("request_count") + 1
            fingerprint_obj.save(update_fields=["last_seen", "request_count"])

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
