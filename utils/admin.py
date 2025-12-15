from django.contrib import admin, messages
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Ban,
    Email,
    Fingerprint,
    IPAddress,
    LighthouseAudit,
    LLMUsage,
    NotificationConfig,
    NotificationEmail,
    NotificationPhoneNumber,
    TextMessage,
    TrackedRequest,
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

    list_display = (
        "ip_address",
        "location_display",
        "request_count",
        "is_banned",
        "view_requests_link",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at", HasGeoDataFilter)
    search_fields = ("ip_address", "geo_data__city", "geo_data__country")
    readonly_fields = ("ip_address", "geo_data", "created_at", "updated_at", "request_count", "view_requests_link")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ["ban_ips", "delete_local_ips"]

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
        return queryset.annotate(num_requests=Count("tracked_requests"))

    @admin.display(description="Request Count", ordering="num_requests")
    def request_count(self, obj):
        """Count of TrackedRequest records using this IP."""
        return obj.num_requests

    @admin.display(description="Banned", boolean=True)
    def is_banned(self, obj):
        """Check if this IP has an active ban."""
        from django.db import models
        from django.utils import timezone

        now = timezone.now()
        return (
            obj.bans.filter(
                is_active=True,
            )
            .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
            .exists()
        )

    @admin.display(description="View Requests")
    def view_requests_link(self, obj):
        """Link to view all requests from this IP address."""
        count = obj.tracked_requests.count()
        if count == 0:
            return "No requests"
        url = reverse("admin:utils_trackedrequest_changelist") + f"?ip_address__id__exact={obj.id}"
        return format_html('<a href="{}">{} request{}</a>', url, count, "s" if count != 1 else "")

    def has_add_permission(self, request):
        """Disable manual creation - IPs created automatically from requests."""
        return False

    def has_change_permission(self, request, obj=None):
        """Make IP addresses read-only."""
        return False

    @admin.action(description="Ban selected IP addresses")
    def ban_ips(self, request, queryset):
        """Create bans for selected IP addresses."""
        created_count = 0
        already_banned = 0

        for ip_obj in queryset:
            # Check if already has an active ban
            existing_ban = ip_obj.bans.filter(is_active=True).first()
            if existing_ban:
                already_banned += 1
                continue

            Ban.objects.create(
                ip_address=ip_obj,
                reason=f"Banned via admin action by {request.user}",
                created_by=request.user,
            )
            created_count += 1

        if created_count:
            messages.success(request, f"Created {created_count} IP ban(s).")
        if already_banned:
            messages.warning(request, f"{already_banned} IP address(es) were already banned.")

    @admin.action(description="Delete local/private IP addresses")
    def delete_local_ips(self, request, queryset):
        """Delete local and private IP addresses (and all related tracked requests)."""
        from utils.security import is_local_ip

        local_ips = [ip for ip in queryset if is_local_ip(ip.ip_address)]
        count = len(local_ips)

        for ip in local_ips:
            ip.delete()  # Cascade deletes related TrackedRequests

        self.message_user(request, f"Deleted {count} local/private IP address(es) and their tracked requests.")


@admin.register(Fingerprint)
class FingerprintAdmin(admin.ModelAdmin):
    """Admin interface for Fingerprint model."""

    list_display = (
        "hash_preview",
        "request_count",
        "is_banned",
        "first_seen",
        "last_seen",
        "view_requests_link",
    )
    list_filter = ("first_seen", "last_seen")
    search_fields = ("hash",)
    readonly_fields = (
        "hash",
        "first_seen",
        "last_seen",
        "view_requests_link",
    )
    date_hierarchy = "first_seen"
    ordering = ("-last_seen",)
    actions = ["ban_fingerprints"]

    def get_queryset(self, request):
        """Annotate queryset with request count for sorting."""
        queryset = super().get_queryset(request)
        return queryset.annotate(num_requests=Count("tracked_requests"))

    @admin.display(description="Fingerprint")
    def hash_preview(self, obj):
        """Display truncated fingerprint hash."""
        return obj.hash[:16] + "..."

    @admin.display(description="Request Count", ordering="num_requests")
    def request_count(self, obj):
        """Count of TrackedRequest records with this fingerprint."""
        return obj.num_requests

    @admin.display(description="Banned", boolean=True)
    def is_banned(self, obj):
        """Check if this fingerprint has an active ban."""
        from django.db import models
        from django.utils import timezone

        now = timezone.now()
        return (
            obj.bans.filter(
                is_active=True,
            )
            .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
            .exists()
        )

    @admin.display(description="View Requests")
    def view_requests_link(self, obj):
        """Link to view all requests with this fingerprint."""
        count = obj.num_requests
        if count == 0:
            return "No requests"
        url = reverse("admin:utils_trackedrequest_changelist") + f"?fingerprint_obj__id__exact={obj.id}"
        return format_html('<a href="{}">{} request{}</a>', url, count, "s" if count != 1 else "")

    @admin.action(description="Ban selected fingerprints")
    def ban_fingerprints(self, request, queryset):
        """Create bans for selected fingerprints."""
        created_count = 0
        already_banned = 0

        for fingerprint in queryset:
            # Check if already has an active ban
            existing_ban = fingerprint.bans.filter(is_active=True).first()
            if existing_ban:
                already_banned += 1
                continue

            Ban.objects.create(
                fingerprint=fingerprint,
                reason=f"Banned via admin action by {request.user}",
                created_by=request.user,
            )
            created_count += 1

        if created_count:
            messages.success(request, f"Created {created_count} ban(s).")
        if already_banned:
            messages.warning(request, f"{already_banned} fingerprint(s) were already banned.")

    def has_add_permission(self, request):
        """Disable manual creation - fingerprints created automatically from requests."""
        return False

    def has_change_permission(self, request, obj=None):
        """Make fingerprints read-only."""
        return False


@admin.register(TrackedRequest)
class TrackedRequestAdmin(admin.ModelAdmin):
    """Admin interface for TrackedRequest model."""

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
        "fingerprint_obj__hash",
        "ip_address__geo_data__city",
        "ip_address__geo_data__country",
    )
    readonly_fields = (
        "created_at",
        "fingerprint_obj",
        "ip_address",
        "method",
        "path",
        "query_params",
        "is_secure",
        "is_ajax",
        "user_agent",
        "browser",
        "browser_version",
        "os",
        "device",
        "headers",
        "referer",
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
        url = reverse("admin:utils_trackedrequest_changelist") + f"?ip_address__id__exact={obj.ip_address.id}"
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
        hash_preview = obj.fingerprint_obj.hash[:16] + "..."
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


class BanStatusFilter(admin.SimpleListFilter):
    """Filter bans by their effective status (active/expired/inactive)."""

    title = "status"
    parameter_name = "ban_status"

    def lookups(self, request, model_admin):
        return (
            ("effective", "Effective (active & not expired)"),
            ("expired", "Expired"),
            ("inactive", "Inactive"),
        )

    def queryset(self, request, queryset):
        from django.db import models
        from django.utils import timezone

        now = timezone.now()

        if self.value() == "effective":
            return queryset.filter(is_active=True).filter(
                models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
            )
        if self.value() == "expired":
            return queryset.filter(is_active=True, expires_at__lt=now)
        if self.value() == "inactive":
            return queryset.filter(is_active=False)
        return queryset


@admin.register(Ban)
class BanAdmin(admin.ModelAdmin):
    """Admin interface for managing bans."""

    list_display = (
        "id",
        "ban_target",
        "reason_preview",
        "is_active",
        "is_effective_display",
        "created_at",
        "expires_at",
        "created_by",
    )
    list_filter = (BanStatusFilter, "is_active", "created_at", "expires_at")
    search_fields = (
        "reason",
        "fingerprint__hash",
        "ip_address__ip_address",
        "user_agent_pattern",
    )
    readonly_fields = ("created_at",)
    raw_id_fields = ("fingerprint", "ip_address", "created_by")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ["activate_bans", "deactivate_bans"]

    fieldsets = (
        (
            "Ban Target",
            {
                "fields": ("fingerprint", "ip_address", "user_agent_pattern"),
                "description": "Specify at least one target for the ban.",
            },
        ),
        (
            "Details",
            {
                "fields": ("reason", "is_active", "expires_at"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "created_by"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Target")
    def ban_target(self, obj):
        """Display the ban target(s)."""
        targets = []
        if obj.fingerprint:
            fp_url = reverse("admin:utils_fingerprint_change", args=[obj.fingerprint.id])
            targets.append(format_html('<a href="{}">FP: {}...</a>', fp_url, obj.fingerprint.hash[:12]))
        if obj.ip_address:
            ip_url = reverse("admin:utils_ipaddress_change", args=[obj.ip_address.id])
            targets.append(format_html('<a href="{}">IP: {}</a>', ip_url, obj.ip_address.ip_address))
        if obj.user_agent_pattern:
            pattern = (
                obj.user_agent_pattern[:30] + "..." if len(obj.user_agent_pattern) > 30 else obj.user_agent_pattern
            )
            targets.append(f"UA: {pattern}")
        return format_html(" | ".join(targets)) if targets else "No target"

    @admin.display(description="Reason")
    def reason_preview(self, obj):
        """Display truncated reason."""
        return obj.reason[:50] + "..." if len(obj.reason) > 50 else obj.reason

    @admin.display(description="Effective", boolean=True)
    def is_effective_display(self, obj):
        """Display if ban is currently in effect."""
        return obj.is_effective()

    @admin.action(description="Activate selected bans")
    def activate_bans(self, request, queryset):
        """Activate selected bans."""
        updated = queryset.update(is_active=True)
        messages.success(request, f"Activated {updated} ban(s).")

    @admin.action(description="Deactivate selected bans")
    def deactivate_bans(self, request, queryset):
        """Deactivate selected bans."""
        updated = queryset.update(is_active=False)
        messages.success(request, f"Deactivated {updated} ban(s).")

    def save_model(self, request, obj, form, change):
        """Set created_by to current user on creation."""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
