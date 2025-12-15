from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Email,
    Fingerprint,
    IPAddress,
    LighthouseAudit,
    LLMUsage,
    NotificationConfig,
    NotificationEmail,
    NotificationPhoneNumber,
    RequestFingerprint,
    TextMessage,
)


class HasGeoDataFilter(admin.SimpleListFilter):
    """Filter for IPAddress records with/without geo data."""

    title = "geo data"
    parameter_name = "has_geo_data"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Has geo data"),
            ("no", "No geo data"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(geo_data__isnull=True).exclude(geo_data={})
        if self.value() == "no":
            return queryset.filter(geo_data__isnull=True) | queryset.filter(geo_data={})
        return queryset


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


@admin.register(IPAddress)
class IPAddressAdmin(admin.ModelAdmin):
    """Admin interface for IPAddress model."""

    list_display = ("ip_address", "location_display", "request_count", "view_requests_link", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at", HasGeoDataFilter)
    search_fields = ("ip_address", "geo_data__city", "geo_data__country")
    readonly_fields = ("ip_address", "geo_data", "created_at", "updated_at", "request_count", "view_requests_link")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ["geolocate_selected", "delete_local_ips"]

    @admin.display(description="Location")
    def location_display(self, obj):
        """Display geolocation information."""
        if not obj.geo_data:
            return "Not geolocated"
        city = obj.geo_data.get("city", "")
        country = obj.geo_data.get("country", "")
        if city and country:
            return f"{city}, {country}"
        return country or "Unknown"

    def get_queryset(self, request):
        """Annotate queryset with request count for sorting."""
        queryset = super().get_queryset(request)
        return queryset.annotate(num_requests=Count("request_fingerprints"))

    @admin.display(description="Request Count", ordering="num_requests")
    def request_count(self, obj):
        """Count of RequestFingerprint records using this IP."""
        return obj.num_requests

    @admin.display(description="View Requests")
    def view_requests_link(self, obj):
        """Link to view all requests from this IP address."""
        count = obj.request_fingerprints.count()
        if count == 0:
            return "No requests"
        url = reverse("admin:utils_requestfingerprint_changelist") + f"?ip_address__id__exact={obj.id}"
        return format_html('<a href="{}">{} request{}</a>', url, count, "s" if count != 1 else "")

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


@admin.register(Fingerprint)
class FingerprintAdmin(admin.ModelAdmin):
    """Admin interface for Fingerprint model."""

    list_display = (
        "hash_preview",
        "request_count",
        "first_seen",
        "last_seen",
        "view_requests_link",
    )
    list_filter = ("first_seen", "last_seen")
    search_fields = ("hash_without_ip",)
    readonly_fields = (
        "hash_without_ip",
        "first_seen",
        "last_seen",
        "view_requests_link",
    )
    date_hierarchy = "first_seen"
    ordering = ("-last_seen",)

    def get_queryset(self, request):
        """Annotate queryset with request count for sorting."""
        queryset = super().get_queryset(request)
        return queryset.annotate(num_requests=Count("requests"))

    @admin.display(description="Fingerprint")
    def hash_preview(self, obj):
        """Display truncated fingerprint hash."""
        return obj.hash_without_ip[:16] + "..."

    @admin.display(description="Request Count", ordering="num_requests")
    def request_count(self, obj):
        """Count of RequestFingerprint records with this fingerprint."""
        return obj.num_requests

    @admin.display(description="View Requests")
    def view_requests_link(self, obj):
        """Link to view all requests with this fingerprint."""
        count = obj.num_requests
        if count == 0:
            return "No requests"
        url = reverse("admin:utils_requestfingerprint_changelist") + f"?fingerprint_obj__id__exact={obj.id}"
        return format_html('<a href="{}">{} request{}</a>', url, count, "s" if count != 1 else "")

    def has_add_permission(self, request):
        """Disable manual creation - fingerprints created automatically from requests."""
        return False

    def has_change_permission(self, request, obj=None):
        """Make fingerprints read-only."""
        return False


@admin.register(RequestFingerprint)
class RequestFingerprintAdmin(admin.ModelAdmin):
    """Admin interface for RequestFingerprint model."""

    list_display = (
        "created_at",
        "ip_display",
        "fingerprint_preview",
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
        "fingerprint_obj__hash_without_ip",
        "ip_address__geo_data__city",
        "ip_address__geo_data__country",
    )
    readonly_fields = (
        "created_at",
        "fingerprint_obj",
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

    @admin.display(
        description="IP Address",
        ordering="ip_address__ip_address",
    )
    def ip_display(self, obj):
        """Display IP address as a clickable link to filter by this IP."""
        if not obj.ip_address:
            return "Unknown"
        url = reverse("admin:utils_requestfingerprint_changelist") + f"?ip_address__id__exact={obj.ip_address.id}"
        return format_html('<a href="{}">{}</a>', url, obj.ip_address.ip_address)

    @admin.display(description="Location")
    def location_display(self, obj):
        """Display geolocation information from related IPAddress."""
        if not obj.ip_address or not obj.ip_address.geo_data:
            return "Not geolocated"
        city = obj.ip_address.geo_data.get("city", "")
        country = obj.ip_address.geo_data.get("country", "")
        if city and country:
            return f"{city}, {country}"
        return country or "Unknown"

    @admin.display(description="Fingerprint")
    def fingerprint_preview(self, obj):
        """Display clickable fingerprint preview."""
        if not obj.fingerprint_obj:
            return "None"
        hash_preview = obj.fingerprint_obj.hash_without_ip[:16] + "..."
        url = reverse("admin:utils_fingerprint_change", args=[obj.fingerprint_obj.id])
        return format_html('<a href="{}">{}</a>', url, hash_preview)

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

    @admin.display(description="Average")
    def average_score(self, obj):
        """Display the average score."""
        return obj.average_score

    def has_add_permission(self, request):
        """Disable manual adding of audits (should be created via management command)."""
        return False


@admin.register(LLMUsage)
class LLMUsageAdmin(admin.ModelAdmin):
    """Admin interface for viewing LLM usage history."""

    list_display = [
        "created_at",
        "provider",
        "model",
        "prompt_preview",
        "response_preview",
    ]
    list_filter = ["provider", "model", "created_at"]
    search_fields = ["provider", "model", "prompt", "response"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "provider",
        "model",
        "prompt",
        "response",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    @admin.display(description="Prompt")
    def prompt_preview(self, obj):
        """Display truncated prompt."""
        return obj.prompt[:100] + "..." if len(obj.prompt) > 100 else obj.prompt

    @admin.display(description="Response")
    def response_preview(self, obj):
        """Display truncated response."""
        return obj.response[:100] + "..." if len(obj.response) > 100 else obj.response

    def has_add_permission(self, request):
        """Disable manual creation - usage should be tracked automatically."""
        return False

    def has_change_permission(self, request, obj=None):
        """Make LLM usage records read-only."""
        return False
