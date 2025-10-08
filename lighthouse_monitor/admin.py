from django.contrib import admin
from .models import LighthouseAudit


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
        'pwa_score',
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
        'pwa_score',
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
