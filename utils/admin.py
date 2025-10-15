from django.contrib import admin

from .models import (
    Email,
    HTTPStatusCode,
    IPAddress,
    LighthouseAudit,
    NotificationConfig,
    NotificationEmail,
    NotificationPhoneNumber,
    RequestFingerprint,
    TextMessage,
)


@admin.register(NotificationConfig)
class NotificationConfigAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "updated_at",
        "emails_enabled",
        "text_messages_enabled",
    )


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ("recipient", "template", "subject", "created", "sent")
    list_filter = ("template", "sent")
    search_fields = ("recipient", "subject")
    readonly_fields = ("created", "updated", "sent")


@admin.register(TextMessage)
class TextMessageAdmin(admin.ModelAdmin):
    list_display = ("recipient", "message", "created", "sent")
    list_filter = ("sent",)
    search_fields = ("recipient", "message")
    readonly_fields = ("created", "updated", "sent")


@admin.register(NotificationEmail)
class NotificationEmailAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "created_at", "verified", "verified_at")
    list_filter = ("verified",)
    search_fields = ("email", "user__email")
    readonly_fields = ("created_at", "verified_at", "verification_code")


@admin.register(NotificationPhoneNumber)
class NotificationPhoneNumberAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "user", "created_at", "verified", "verified_at")
    list_filter = ("verified",)
    search_fields = ("phone_number", "user__email")
    readonly_fields = ("created_at", "verified_at", "verification_code")


@admin.register(HTTPStatusCode)
class HTTPStatusCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")


@admin.register(IPAddress)
class IPAddressAdmin(admin.ModelAdmin):
    """Admin interface for IPAddress model."""

    list_display = ("ip_address", "location_display", "request_count", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("ip_address", "geo_data__city", "geo_data__country")
    readonly_fields = ("ip_address", "geo_data", "created_at", "updated_at", "request_count")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ["geolocate_selected", "delete_local_ips"]

    def location_display(self, obj):
        """Display geolocation information."""
        if not obj.geo_data:
            return "Not geolocated"
        city = obj.geo_data.get("city", "")
        country = obj.geo_data.get("country", "")
        if city and country:
            return f"{city}, {country}"
        return country or "Unknown"

    location_display.short_description = "Location"

    def request_count(self, obj):
        """Count of RequestFingerprint records using this IP."""
        return obj.request_fingerprints.count()

    request_count.short_description = "Request Count"

    def has_add_permission(self, request):
        """Disable manual creation - IPs created automatically from requests."""
        return False

    def has_change_permission(self, request, obj=None):
        """Make IP addresses read-only."""
        return False

    @admin.action(description="Geolocate selected IP addresses")
    def geolocate_selected(self, request, queryset):
        """Geolocate selected IP addresses."""
        from utils.security import geolocate_ips_batch

        ip_addresses = [ip.ip_address for ip in queryset]
        results = geolocate_ips_batch(ip_addresses, batch_size=100)

        success_count = 0
        for ip_str, geo_data in results.items():
            if geo_data:
                IPAddress.objects.filter(ip_address=ip_str).update(geo_data=geo_data)
                success_count += 1

        self.message_user(request, f"Successfully geolocated {success_count} IP address(es).")

    @admin.action(description="Delete local/private IP addresses")
    def delete_local_ips(self, request, queryset):
        """Delete local and private IP addresses (and all related fingerprints)."""
        from utils.security import is_local_ip

        local_ips = [ip for ip in queryset if is_local_ip(ip.ip_address)]
        count = len(local_ips)

        for ip in local_ips:
            ip.delete()  # Cascade deletes related RequestFingerprints

        self.message_user(request, f"Deleted {count} local/private IP address(es) and their fingerprints.")


@admin.register(RequestFingerprint)
class RequestFingerprintAdmin(admin.ModelAdmin):
    """Admin interface for RequestFingerprint model."""

    list_display = (
        "created_at",
        "ip_display",
        "method",
        "path",
        "browser",
        "os",
        "location_display",
        "is_suspicious",
        "user",
    )
    list_filter = (
        "is_suspicious",
        "method",
        "is_secure",
        "is_ajax",
        "created_at",
    )
    search_fields = (
        "ip_address__ip_address",
        "path",
        "user_agent",
        "fingerprint",
        "fingerprint_no_ip",
        "ip_address__geo_data__city",
        "ip_address__geo_data__country",
    )
    readonly_fields = (
        "created_at",
        "fingerprint",
        "fingerprint_no_ip",
        "ip_address",
        "method",
        "path",
        "is_secure",
        "is_ajax",
        "user_agent",
        "browser",
        "browser_version",
        "os",
        "device",
        "headers",
        "is_suspicious",
        "suspicious_reason",
        "user",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def ip_display(self, obj):
        """Display IP address."""
        return obj.ip_address.ip_address if obj.ip_address else "Unknown"

    ip_display.short_description = "IP Address"
    ip_display.admin_order_field = "ip_address__ip_address"

    def location_display(self, obj):
        """Display geolocation information from related IPAddress."""
        if not obj.ip_address or not obj.ip_address.geo_data:
            return "Not geolocated"
        city = obj.ip_address.geo_data.get("city", "")
        country = obj.ip_address.geo_data.get("country", "")
        if city and country:
            return f"{city}, {country}"
        return country or "Unknown"

    location_display.short_description = "Location"

    def has_add_permission(self, request):
        """Disable manual creation - fingerprints should be created from requests."""
        return False

    def has_change_permission(self, request, obj=None):
        """Make fingerprints read-only."""
        return False


@admin.register(LighthouseAudit)
class LighthouseAuditAdmin(admin.ModelAdmin):
    """Admin interface for viewing Lighthouse audit history."""

    list_display = [
        "url",
        "audit_date",
        "performance_score",
        "accessibility_score",
        "best_practices_score",
        "seo_score",
        "average_score",
    ]
    list_filter = ["audit_date", "url"]
    search_fields = ["url"]
    readonly_fields = [
        "url",
        "performance_score",
        "accessibility_score",
        "best_practices_score",
        "seo_score",
        "audit_date",
        "metadata",
    ]
    date_hierarchy = "audit_date"
    ordering = ["-audit_date"]

    def average_score(self, obj):
        """Display the average score."""
        return obj.average_score

    average_score.short_description = "Average"

    def has_add_permission(self, request):
        """Disable manual adding of audits (should be created via management command)."""
        return False
