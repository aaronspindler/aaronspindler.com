from django.contrib import admin

from django.contrib import admin
from .models import (
    Email, NotificationConfig, TextMessage, NotificationEmail, 
    NotificationPhoneNumber, HTTPStatusCode, RequestFingerprint, LighthouseAudit
)

@admin.register(NotificationConfig)
class NotificationConfigAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'updated_at', 'emails_enabled', 'text_messages_enabled')

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'template', 'subject', 'created', 'sent')
    list_filter = ('template', 'sent')
    search_fields = ('recipient', 'subject')
    readonly_fields = ('created', 'updated', 'sent')

@admin.register(TextMessage)
class TextMessageAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'created', 'sent')
    list_filter = ('sent',)
    search_fields = ('recipient', 'message')
    readonly_fields = ('created', 'updated', 'sent')


@admin.register(NotificationEmail)
class NotificationEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'created_at', 'verified', 'verified_at')
    list_filter = ('verified',)
    search_fields = ('email', 'user__email')
    readonly_fields = ('created_at', 'verified_at', 'verification_code')

@admin.register(NotificationPhoneNumber)
class NotificationPhoneNumberAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user', 'created_at', 'verified', 'verified_at')
    list_filter = ('verified',)
    search_fields = ('phone_number', 'user__email')
    readonly_fields = ('created_at', 'verified_at', 'verification_code')

@admin.register(HTTPStatusCode)
class HTTPStatusCodeAdmin(admin.ModelAdmin):
    list_display = ('code','description')
    search_fields = ('code', 'description')


@admin.register(RequestFingerprint)
class RequestFingerprintAdmin(admin.ModelAdmin):
    """Admin interface for RequestFingerprint model."""
    list_display = (
        'created_at',
        'ip_address',
        'method',
        'path',
        'browser',
        'os',
        'is_suspicious',
        'user',
    )
    list_filter = (
        'is_suspicious',
        'method',
        'is_secure',
        'is_ajax',
        'created_at',
    )
    search_fields = (
        'ip_address',
        'path',
        'user_agent',
        'fingerprint',
        'fingerprint_no_ip',
    )
    readonly_fields = (
        'created_at',
        'fingerprint',
        'fingerprint_no_ip',
        'ip_address',
        'method',
        'path',
        'is_secure',
        'is_ajax',
        'user_agent',
        'browser',
        'browser_version',
        'os',
        'device',
        'headers',
        'is_suspicious',
        'suspicious_reason',
        'user',
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    actions = ['delete_local_records']
    
    def has_add_permission(self, request):
        """Disable manual creation - fingerprints should be created from requests."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make fingerprints read-only."""
        return False
    
    @admin.action(description='Delete local (localhost/127.0.0.1) records')
    def delete_local_records(self, request, queryset):
        """Delete all RequestFingerprint records from localhost or 127.0.0.1."""
        local_ips = ['127.0.0.1', '::1']
        deleted_count, _ = RequestFingerprint.objects.filter(
            ip_address__in=local_ips
        ).delete()
        
        self.message_user(
            request,
            f'Successfully deleted {deleted_count} local record(s).',
        )


@admin.register(LighthouseAudit)
class LighthouseAuditAdmin(admin.ModelAdmin):
    """Admin interface for viewing Lighthouse audit history."""
    list_display = [
        'url',
        'audit_date',
        'performance_score',
        'accessibility_score',
        'best_practices_score',
        'seo_score',
        'average_score',
    ]
    list_filter = ['audit_date', 'url']
    search_fields = ['url']
    readonly_fields = [
        'url',
        'performance_score',
        'accessibility_score',
        'best_practices_score',
        'seo_score',
        'audit_date',
        'metadata',
    ]
    date_hierarchy = 'audit_date'
    ordering = ['-audit_date']

    def average_score(self, obj):
        """Display the average score."""
        return obj.average_score
    average_score.short_description = 'Average'

    def has_add_permission(self, request):
        """Disable manual adding of audits (should be created via management command)."""
        return False
