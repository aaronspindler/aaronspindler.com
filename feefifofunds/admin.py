"""
Django admin configuration for FeeFiFoFunds models.
"""

from django.contrib import admin
from django.utils.html import SafeString, format_html

from .models import DataSource, DataSync, Fund, FundHolding, FundMetrics, FundPerformance


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    """Admin interface for Fund model."""

    list_display = [
        "ticker",
        "name",
        "fund_type",
        "asset_class",
        "expense_ratio",
        "current_price",
        "price_change_display",
        "is_active",
        "last_price_update",
    ]
    list_filter = [
        "fund_type",
        "asset_class",
        "is_active",
        "currency",
        "category",
    ]
    search_fields = [
        "ticker",
        "name",
        "issuer",
        "isin",
        "cusip",
    ]
    readonly_fields = [
        "slug",
        "created_at",
        "updated_at",
        "deleted_at",
        "price_change",
        "price_change_percent",
        "total_cost_percent",
    ]
    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "ticker",
                    "name",
                    "slug",
                    "isin",
                    "cusip",
                )
            },
        ),
        (
            "Classification",
            {
                "fields": (
                    "fund_type",
                    "asset_class",
                    "category",
                    "issuer",
                )
            },
        ),
        (
            "Details",
            {
                "fields": (
                    "description",
                    "inception_date",
                    "website",
                    "exchange",
                )
            },
        ),
        (
            "Costs & Fees",
            {
                "fields": (
                    "expense_ratio",
                    "management_fee",
                    "front_load",
                    "back_load",
                    "total_cost_percent",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Current State",
            {
                "fields": (
                    "current_price",
                    "previous_close",
                    "price_change",
                    "price_change_percent",
                    "currency",
                    "last_price_update",
                )
            },
        ),
        (
            "Fund Size",
            {
                "fields": (
                    "aum",
                    "avg_volume",
                )
            },
        ),
        (
            "Status & Timestamps",
            {
                "fields": (
                    "is_active",
                    "deleted_at",
                    "last_updated",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["ticker"]
    date_hierarchy = "created_at"

    def price_change_display(self, obj: Fund) -> SafeString:
        """Display price change with color coding."""
        change = obj.price_change_percent
        if change is None:
            return "-"

        color = "green" if change > 0 else "red" if change < 0 else "gray"
        return format_html('<span style="color: {};">{:.2f}%</span>', color, change)

    price_change_display.short_description = "Change %"
    price_change_display.admin_order_field = "price_change_percent"


@admin.register(FundPerformance)
class FundPerformanceAdmin(admin.ModelAdmin):
    """Admin interface for FundPerformance model."""

    list_display = [
        "fund",
        "date",
        "interval",
        "close_price",
        "volume",
        "daily_return",
        "data_source",
        "is_active",
    ]
    list_filter = [
        "interval",
        "data_source",
        "is_active",
        "date",
    ]
    search_fields = [
        "fund__ticker",
        "fund__name",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "dollar_volume",
        "intraday_change",
        "intraday_change_percent",
        "intraday_range",
    ]
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "fund",
                    "date",
                    "interval",
                    "data_source",
                )
            },
        ),
        (
            "OHLCV Data",
            {
                "fields": (
                    "open_price",
                    "high_price",
                    "low_price",
                    "close_price",
                    "adjusted_close",
                    "volume",
                    "dollar_volume",
                )
            },
        ),
        (
            "Distributions",
            {
                "fields": (
                    "dividend",
                    "split_ratio",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Calculated Fields",
            {
                "fields": (
                    "daily_return",
                    "log_return",
                    "intraday_change",
                    "intraday_change_percent",
                    "intraday_range",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "data_quality_score",
                    "is_active",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-date"]
    date_hierarchy = "date"
    raw_id_fields = ["fund"]


@admin.register(FundHolding)
class FundHoldingAdmin(admin.ModelAdmin):
    """Admin interface for FundHolding model."""

    list_display = [
        "fund",
        "ticker",
        "name",
        "holding_type",
        "weight",
        "market_value",
        "sector",
        "as_of_date",
    ]
    list_filter = [
        "holding_type",
        "sector",
        "country",
        "as_of_date",
        "is_active",
    ]
    search_fields = [
        "fund__ticker",
        "ticker",
        "name",
        "cusip",
        "isin",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "weight_change",
        "unrealized_gain_loss",
        "unrealized_gain_loss_percent",
    ]
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "fund",
                    "ticker",
                    "name",
                    "cusip",
                    "isin",
                )
            },
        ),
        (
            "Classification",
            {
                "fields": (
                    "holding_type",
                    "sector",
                    "industry",
                    "country",
                )
            },
        ),
        (
            "Position",
            {
                "fields": (
                    "shares",
                    "market_value",
                    "weight",
                    "previous_weight",
                    "weight_change",
                )
            },
        ),
        (
            "Pricing",
            {
                "fields": (
                    "price",
                    "cost_basis",
                    "unrealized_gain_loss",
                    "unrealized_gain_loss_percent",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "as_of_date",
                    "data_source",
                    "is_active",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-weight"]
    date_hierarchy = "as_of_date"
    raw_id_fields = ["fund"]


@admin.register(FundMetrics)
class FundMetricsAdmin(admin.ModelAdmin):
    """Admin interface for FundMetrics model."""

    list_display = [
        "fund",
        "time_frame",
        "calculation_date",
        "total_return",
        "sharpe_ratio",
        "max_drawdown",
        "overall_score",
    ]
    list_filter = [
        "time_frame",
        "calculation_date",
        "is_active",
    ]
    search_fields = [
        "fund__ticker",
        "fund__name",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "is_outperforming_benchmark",
        "risk_adjusted_return_score",
    ]
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "fund",
                    "calculation_date",
                    "time_frame",
                    "data_points",
                )
            },
        ),
        (
            "Returns",
            {
                "fields": (
                    "total_return",
                    "annualized_return",
                    "cumulative_return",
                )
            },
        ),
        (
            "Risk Metrics",
            {
                "fields": (
                    "volatility",
                    "downside_deviation",
                    "beta",
                    "alpha",
                    "r_squared",
                )
            },
        ),
        (
            "Risk-Adjusted Returns",
            {
                "fields": (
                    "sharpe_ratio",
                    "sortino_ratio",
                    "treynor_ratio",
                    "information_ratio",
                    "risk_adjusted_return_score",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Drawdown",
            {
                "fields": (
                    "max_drawdown",
                    "max_drawdown_duration",
                    "current_drawdown",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Value at Risk",
            {
                "fields": (
                    "var_95",
                    "var_99",
                    "cvar_95",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "win_rate",
                    "best_day",
                    "worst_day",
                    "avg_positive_day",
                    "avg_negative_day",
                    "skewness",
                    "kurtosis",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Benchmark Comparison",
            {
                "fields": (
                    "benchmark_ticker",
                    "excess_return",
                    "tracking_error",
                    "is_outperforming_benchmark",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Scores",
            {
                "fields": (
                    "risk_score",
                    "return_score",
                    "overall_score",
                )
            },
        ),
        (
            "Calculation Metadata",
            {
                "fields": (
                    "calculation_engine_version",
                    "calculation_duration_ms",
                    "is_active",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-calculation_date", "fund"]
    date_hierarchy = "calculation_date"
    raw_id_fields = ["fund"]


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    """Admin interface for DataSource model."""

    list_display = [
        "name",
        "display_name",
        "source_type",
        "status_display",
        "priority",
        "reliability_score",
        "requests_today",
        "last_successful_sync",
    ]
    list_filter = [
        "source_type",
        "status",
        "is_active",
        "is_free",
        "api_key_required",
    ]
    search_fields = [
        "name",
        "display_name",
        "description",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "last_request_time",
        "last_successful_sync",
        "last_error_time",
        "reliability_score",
    ]
    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "name",
                    "display_name",
                    "source_type",
                    "description",
                )
            },
        ),
        (
            "Configuration",
            {
                "fields": (
                    "base_url",
                    "api_key_required",
                    "documentation_url",
                )
            },
        ),
        (
            "Rate Limiting",
            {
                "fields": (
                    "rate_limit_requests",
                    "rate_limit_period_seconds",
                    "requests_today",
                    "last_request_time",
                )
            },
        ),
        (
            "Status & Health",
            {
                "fields": (
                    "status",
                    "last_successful_sync",
                    "last_error",
                    "last_error_time",
                    "consecutive_failures",
                )
            },
        ),
        (
            "Priority & Reliability",
            {
                "fields": (
                    "priority",
                    "reliability_score",
                )
            },
        ),
        (
            "Data Coverage",
            {
                "fields": (
                    "supports_historical_data",
                    "supports_realtime_data",
                    "supports_holdings",
                    "supports_fundamentals",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Cost",
            {
                "fields": (
                    "is_free",
                    "monthly_cost",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "is_active",
                    "deleted_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-priority", "name"]

    def status_display(self, obj: DataSource) -> SafeString:
        """Display status with color coding."""
        colors = {
            "ACTIVE": "green",
            "INACTIVE": "gray",
            "ERROR": "red",
            "RATE_LIMITED": "orange",
            "MAINTENANCE": "blue",
        }
        color = colors.get(obj.status, "black")
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())

    status_display.short_description = "Status"


@admin.register(DataSync)
class DataSyncAdmin(admin.ModelAdmin):
    """Admin interface for DataSync model."""

    list_display = [
        "data_source",
        "sync_type",
        "fund",
        "status_display",
        "started_at",
        "duration_seconds",
        "records_created",
        "records_updated",
    ]
    list_filter = [
        "sync_type",
        "status",
        "data_source",
        "started_at",
    ]
    search_fields = [
        "fund__ticker",
        "data_source__name",
        "celery_task_id",
        "error_message",
    ]
    readonly_fields = [
        "created_at",
        "started_at",
        "completed_at",
        "duration_seconds",
    ]
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "data_source",
                    "fund",
                    "sync_type",
                    "status",
                    "celery_task_id",
                )
            },
        ),
        (
            "Timing",
            {
                "fields": (
                    "started_at",
                    "completed_at",
                    "duration_seconds",
                )
            },
        ),
        (
            "Results",
            {
                "fields": (
                    "records_fetched",
                    "records_created",
                    "records_updated",
                    "records_failed",
                )
            },
        ),
        (
            "Errors",
            {
                "fields": (
                    "error_message",
                    "error_details",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Request/Response",
            {
                "fields": (
                    "request_params",
                    "response_metadata",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-started_at"]
    date_hierarchy = "started_at"
    raw_id_fields = ["fund"]

    def status_display(self, obj: DataSync) -> SafeString:
        """Display status with color coding."""
        colors = {
            "PENDING": "gray",
            "IN_PROGRESS": "blue",
            "SUCCESS": "green",
            "PARTIAL": "orange",
            "FAILED": "red",
        }
        color = colors.get(obj.status, "black")
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())

    status_display.short_description = "Status"
