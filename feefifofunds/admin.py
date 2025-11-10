from django.contrib import admin

from .models import Asset, AssetPrice, Trade


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


@admin.register(AssetPrice)
class AssetPriceAdmin(admin.ModelAdmin):
    list_display = [
        "asset_id",
        "time",
        "quote_currency",
        "interval_minutes",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
    ]
    list_filter = ["source", "quote_currency", "interval_minutes", "time"]
    search_fields = ["asset_id"]
    readonly_fields = ["created_at"]
    ordering = ["-time"]
    date_hierarchy = "time"

    fieldsets = (
        (
            "Asset & Time",
            {
                "fields": ("asset_id", "time", "quote_currency", "source", "interval_minutes"),
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
    list_display = ["asset_id", "time", "quote_currency", "price", "volume", "source"]
    list_filter = ["source", "quote_currency", "time"]
    search_fields = ["asset_id"]
    readonly_fields = ["created_at"]
    ordering = ["-time"]
    date_hierarchy = "time"

    fieldsets = (
        (
            "Trade Details",
            {
                "fields": ("asset_id", "time", "quote_currency", "price", "volume", "source"),
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
