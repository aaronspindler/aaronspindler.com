from django.contrib import admin

from .models import Asset, AssetPrice


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["ticker", "name", "category", "quote_currency", "active", "created_at"]
    list_filter = ["category", "quote_currency", "active"]
    search_fields = ["ticker", "name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["ticker"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("ticker", "name", "category", "quote_currency"),
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


@admin.register(AssetPrice)
class AssetPriceAdmin(admin.ModelAdmin):
    list_display = ["asset", "timestamp", "open", "high", "low", "close", "volume", "source"]
    list_filter = ["source", "timestamp"]
    search_fields = ["asset__ticker", "asset__name"]
    readonly_fields = ["created_at"]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"
    raw_id_fields = ["asset"]

    fieldsets = (
        (
            "Asset & Time",
            {
                "fields": ("asset", "timestamp", "source"),
            },
        ),
        (
            "OHLC Data",
            {
                "fields": ("open", "high", "low", "close"),
            },
        ),
        (
            "Volume",
            {
                "fields": ("volume",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )
