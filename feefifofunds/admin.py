from django.contrib import admin

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["ticker", "name", "category", "tier", "active", "created_at"]
    list_filter = ["category", "tier", "active"]
    search_fields = ["ticker", "name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["ticker"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("ticker", "name", "category", "tier"),
            },
        ),
        (
            "Details",
            {
                "fields": ("description", "active"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
