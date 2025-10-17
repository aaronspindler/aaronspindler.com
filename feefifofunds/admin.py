from django.contrib import admin
from django.utils.html import format_html

from .models import Fund, FundProvider, PerformanceHistory


@admin.register(FundProvider)
class FundProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "website_link", "fund_count", "created_at"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        (
            "Basic Information",
            {
                "fields": ["name", "slug", "website", "description", "logo"],
            },
        ),
        (
            "Metadata",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def website_link(self, obj):
        if obj.website:
            return format_html('<a href="{}" target="_blank">Visit Website</a>', obj.website)
        return "-"

    website_link.short_description = "Website"

    def fund_count(self, obj):
        return obj.funds.count()

    fund_count.short_description = "Number of Funds"


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = [
        "ticker",
        "name",
        "provider",
        "fund_type",
        "mer",
        "asset_class",
        "geographic_focus",
        "is_active",
    ]
    list_filter = [
        "fund_type",
        "asset_class",
        "geographic_focus",
        "is_active",
        "provider",
    ]
    search_fields = ["name", "ticker", "description"]
    prepopulated_fields = {"slug": ("ticker", "name")}
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 50

    fieldsets = [
        (
            "Basic Information",
            {
                "fields": [
                    "name",
                    "ticker",
                    "slug",
                    "provider",
                    "fund_type",
                    "description",
                    "is_active",
                ],
            },
        ),
        (
            "Fee Structure",
            {
                "fields": [
                    "mer",
                    "front_load",
                    "back_load",
                    "transaction_fee",
                ],
            },
        ),
        (
            "Classification",
            {
                "fields": [
                    "asset_class",
                    "geographic_focus",
                ],
            },
        ),
        (
            "Performance Data",
            {
                "fields": [
                    "ytd_return",
                    "one_year_return",
                    "three_year_return",
                    "five_year_return",
                    "ten_year_return",
                ],
            },
        ),
        (
            "Fund Details",
            {
                "fields": [
                    "inception_date",
                    "aum",
                    "minimum_investment",
                ],
            },
        ),
        (
            "Metadata",
            {
                "fields": [
                    "last_data_update",
                    "data_source_url",
                    "created_at",
                    "updated_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_queryset(self, request):
        """Optimize queryset with select_related for provider."""
        return super().get_queryset(request).select_related("provider")


@admin.register(PerformanceHistory)
class PerformanceHistoryAdmin(admin.ModelAdmin):
    list_display = ["fund", "date", "nav", "daily_return", "created_at"]
    list_filter = ["date", "fund"]
    search_fields = ["fund__ticker", "fund__name"]
    date_hierarchy = "date"
    readonly_fields = ["created_at"]
    list_per_page = 100

    fieldsets = [
        (
            "Performance Data",
            {
                "fields": [
                    "fund",
                    "date",
                    "nav",
                    "daily_return",
                ],
            },
        ),
        (
            "Metadata",
            {
                "fields": ["created_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_queryset(self, request):
        """Optimize queryset with select_related for fund."""
        return super().get_queryset(request).select_related("fund")
