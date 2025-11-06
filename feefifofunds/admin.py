from django.contrib import admin

from .models import Asset, AssetPrice, Trade


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
    list_display = ["asset", "timestamp", "interval_minutes", "open", "high", "low", "close", "volume", "source"]
    list_filter = ["source", "interval_minutes", "timestamp"]
    search_fields = ["asset__ticker", "asset__name"]
    readonly_fields = ["created_at"]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"
    raw_id_fields = ["asset"]

    fieldsets = (
        (
            "Asset & Time",
            {
                "fields": ("asset", "timestamp", "source", "interval_minutes"),
            },
        ),
        (
            "OHLC Data",
            {
                "fields": ("open", "high", "low", "close"),
            },
        ),
        (
            "Volume & Trades",
            {
                "fields": ("volume", "trade_count"),
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


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ["asset", "timestamp", "price", "volume", "source"]
    list_filter = ["source", "timestamp"]
    search_fields = ["asset__ticker", "asset__name"]
    readonly_fields = ["created_at"]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"
    raw_id_fields = ["asset"]

    fieldsets = (
        (
            "Trade Details",
            {
                "fields": ("asset", "timestamp", "price", "volume", "source"),
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
