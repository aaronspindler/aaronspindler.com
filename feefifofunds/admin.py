"""
Django admin configuration for FeeFiFoFunds models.
"""

from django.contrib import admin
from django.utils.html import SafeString, format_html
from polymorphic.admin import PolymorphicChildModelAdmin, PolymorphicParentModelAdmin

from .models import (
    Asset,
    Commodity,
    CommodityMetrics,
    CommodityPerformance,
    Crypto,
    CryptoMetrics,
    CryptoPerformance,
    Currency,
    CurrencyMetrics,
    CurrencyPerformance,
    DataSource,
    DataSync,
    Fund,
    FundHolding,
    FundMetrics,
    FundPerformance,
    InflationData,
    InflationIndex,
    InflationMetrics,
    PropertyValuation,
    RealEstate,
    RealEstateMetrics,
    SavingsAccount,
    SavingsMetrics,
    SavingsRateHistory,
)


@admin.register(Asset)
class AssetParentAdmin(PolymorphicParentModelAdmin):
    """Polymorphic parent admin for all asset types."""

    base_model = Asset
    child_models = (Fund, Crypto, Currency, Commodity, InflationIndex, SavingsAccount, RealEstate)
    list_display = ["ticker", "name", "asset_type_display", "current_value", "quote_currency", "is_active"]
    list_filter = ["is_active", "quote_currency"]
    search_fields = ["ticker", "name", "description"]


@admin.register(Fund)
class FundAdmin(PolymorphicChildModelAdmin, admin.ModelAdmin):
    """Admin interface for Fund model."""

    list_display = [
        "ticker",
        "name",
        "fund_type",
        "asset_class",
        "expense_ratio",
        "current_value",
        "price_change_display",
        "is_active",
        "last_price_update",
    ]
    list_filter = [
        "fund_type",
        "asset_class",
        "is_active",
        "quote_currency",
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
                    "current_value",
                    "previous_value",
                    "price_change",
                    "price_change_percent",
                    "quote_currency",
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
        "asset",
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
        "asset__ticker",
        "asset__name",
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
                    "asset",
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
    raw_id_fields = ["asset"]


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
        "asset",
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
        "asset__ticker",
        "asset__name",
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
                    "asset",
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
    ordering = ["-calculation_date", "asset"]
    date_hierarchy = "calculation_date"
    raw_id_fields = ["asset"]


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


# ============================================================================
# Asset Type Admins
# ============================================================================


@admin.register(Crypto)
class CryptoAdmin(PolymorphicChildModelAdmin, admin.ModelAdmin):
    """Admin interface for Crypto model."""

    base_model = Crypto
    list_display = ["ticker", "name", "blockchain", "token_type", "current_value", "market_cap_rank", "is_active"]
    list_filter = ["blockchain", "token_type", "is_active"]
    search_fields = ["ticker", "name", "contract_address"]
    readonly_fields = ["slug", "created_at", "updated_at", "supply_percentage", "is_capped"]


@admin.register(Currency)
class CurrencyAdmin(PolymorphicChildModelAdmin, admin.ModelAdmin):
    """Admin interface for Currency model."""

    base_model = Currency
    list_display = ["ticker", "currency_code", "base_currency", "country", "current_value", "is_major_currency"]
    list_filter = ["currency_type", "is_major_currency", "is_reserve_currency", "country"]
    search_fields = ["ticker", "name", "currency_code", "country"]
    readonly_fields = ["slug", "created_at", "updated_at", "currency_pair"]


@admin.register(Commodity)
class CommodityAdmin(PolymorphicChildModelAdmin, admin.ModelAdmin):
    """Admin interface for Commodity model."""

    base_model = Commodity
    list_display = ["ticker", "name", "commodity_type", "unit_of_measure", "current_value", "is_spot_price"]
    list_filter = ["commodity_type", "trading_exchange", "is_spot_price"]
    search_fields = ["ticker", "name", "contract_symbol", "grade"]
    readonly_fields = ["slug", "created_at", "updated_at", "is_precious_metal", "is_energy"]


@admin.register(InflationIndex)
class InflationIndexAdmin(PolymorphicChildModelAdmin, admin.ModelAdmin):
    """Admin interface for InflationIndex model."""

    base_model = InflationIndex
    list_display = ["ticker", "index_type", "geographic_region", "base_year", "frequency", "seasonal_adjustment"]
    list_filter = ["index_type", "geographic_region", "frequency", "seasonal_adjustment"]
    search_fields = ["ticker", "name", "geographic_region"]
    readonly_fields = ["slug", "created_at", "updated_at"]


@admin.register(SavingsAccount)
class SavingsAccountAdmin(PolymorphicChildModelAdmin, admin.ModelAdmin):
    """Admin interface for SavingsAccount model."""

    base_model = SavingsAccount
    list_display = ["ticker", "institution_name", "account_type", "current_value", "fdic_insured", "is_cd"]
    list_filter = ["account_type", "fdic_insured", "institution_name"]
    search_fields = ["ticker", "name", "institution_name"]
    readonly_fields = ["slug", "created_at", "updated_at", "is_cd", "term_years"]


@admin.register(RealEstate)
class RealEstateAdmin(PolymorphicChildModelAdmin, admin.ModelAdmin):
    """Admin interface for RealEstate model."""

    base_model = RealEstate
    list_display = ["ticker", "name", "property_type", "location_city", "location_state", "is_index", "current_value"]
    list_filter = ["property_type", "location_country", "location_state", "is_index"]
    search_fields = ["ticker", "name", "location_city", "location_state"]
    readonly_fields = ["slug", "created_at", "updated_at", "price_per_sqft", "appreciation_percent"]


# ============================================================================
# Performance Model Admins
# ============================================================================


@admin.register(CryptoPerformance)
class CryptoPerformanceAdmin(admin.ModelAdmin):
    """Admin interface for CryptoPerformance model."""

    list_display = ["asset", "date", "close_price", "volume_24h", "market_cap", "daily_return"]
    list_filter = ["interval", "data_source", "is_active", "date"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-date"]
    date_hierarchy = "date"
    raw_id_fields = ["asset"]


@admin.register(CurrencyPerformance)
class CurrencyPerformanceAdmin(admin.ModelAdmin):
    """Admin interface for CurrencyPerformance model."""

    list_display = ["asset", "date", "exchange_rate", "spread", "daily_return"]
    list_filter = ["interval", "data_source", "is_active", "date"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-date"]
    date_hierarchy = "date"
    raw_id_fields = ["asset"]


@admin.register(CommodityPerformance)
class CommodityPerformanceAdmin(admin.ModelAdmin):
    """Admin interface for CommodityPerformance model."""

    list_display = ["asset", "date", "spot_price", "futures_price", "volume", "daily_return"]
    list_filter = ["interval", "data_source", "is_active", "date"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-date"]
    date_hierarchy = "date"
    raw_id_fields = ["asset"]


@admin.register(InflationData)
class InflationDataAdmin(admin.ModelAdmin):
    """Admin interface for InflationData model."""

    list_display = ["asset", "date", "index_value", "annual_rate", "monthly_rate"]
    list_filter = ["interval", "data_source", "is_active", "date"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-date"]
    date_hierarchy = "date"
    raw_id_fields = ["asset"]


@admin.register(SavingsRateHistory)
class SavingsRateHistoryAdmin(admin.ModelAdmin):
    """Admin interface for SavingsRateHistory model."""

    list_display = ["asset", "date", "annual_percentage_yield", "interest_rate", "compounding_frequency"]
    list_filter = ["interval", "compounding_frequency", "is_active", "date"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-date"]
    date_hierarchy = "date"
    raw_id_fields = ["asset"]


@admin.register(PropertyValuation)
class PropertyValuationAdmin(admin.ModelAdmin):
    """Admin interface for PropertyValuation model."""

    list_display = ["asset", "date", "market_value", "assessed_value", "rental_income_monthly", "valuation_method"]
    list_filter = ["interval", "valuation_method", "is_active", "date"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-date"]
    date_hierarchy = "date"
    raw_id_fields = ["asset"]


# ============================================================================
# Metrics Model Admins
# ============================================================================


@admin.register(CryptoMetrics)
class CryptoMetricsAdmin(admin.ModelAdmin):
    """Admin interface for CryptoMetrics model."""

    list_display = ["asset", "time_frame", "calculation_date", "total_return", "sharpe_ratio", "max_drawdown"]
    list_filter = ["time_frame", "calculation_date", "is_active"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-calculation_date"]
    date_hierarchy = "calculation_date"
    raw_id_fields = ["asset"]


@admin.register(CurrencyMetrics)
class CurrencyMetricsAdmin(admin.ModelAdmin):
    """Admin interface for CurrencyMetrics model."""

    list_display = ["asset", "time_frame", "calculation_date", "total_return", "sharpe_ratio", "volatility"]
    list_filter = ["time_frame", "calculation_date", "is_active"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-calculation_date"]
    date_hierarchy = "calculation_date"
    raw_id_fields = ["asset"]


@admin.register(CommodityMetrics)
class CommodityMetricsAdmin(admin.ModelAdmin):
    """Admin interface for CommodityMetrics model."""

    list_display = ["asset", "time_frame", "calculation_date", "total_return", "sharpe_ratio", "max_drawdown"]
    list_filter = ["time_frame", "calculation_date", "is_active"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-calculation_date"]
    date_hierarchy = "calculation_date"
    raw_id_fields = ["asset"]


@admin.register(InflationMetrics)
class InflationMetricsAdmin(admin.ModelAdmin):
    """Admin interface for InflationMetrics model."""

    list_display = [
        "asset",
        "time_frame",
        "calculation_date",
        "average_annual_rate",
        "cumulative_inflation",
        "trend_direction",
    ]
    list_filter = ["time_frame", "trend_direction", "calculation_date", "is_active"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-calculation_date"]
    date_hierarchy = "calculation_date"
    raw_id_fields = ["asset"]


@admin.register(SavingsMetrics)
class SavingsMetricsAdmin(admin.ModelAdmin):
    """Admin interface for SavingsMetrics model."""

    list_display = [
        "asset",
        "time_frame",
        "calculation_date",
        "effective_annual_rate",
        "real_return",
        "rate_stability_score",
    ]
    list_filter = ["time_frame", "calculation_date", "is_active"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-calculation_date"]
    date_hierarchy = "calculation_date"
    raw_id_fields = ["asset"]


@admin.register(RealEstateMetrics)
class RealEstateMetricsAdmin(admin.ModelAdmin):
    """Admin interface for RealEstateMetrics model."""

    list_display = ["asset", "time_frame", "calculation_date", "cap_rate", "rental_yield", "appreciation_rate"]
    list_filter = ["time_frame", "calculation_date", "is_active"]
    search_fields = ["asset__ticker", "asset__name"]
    ordering = ["-calculation_date"]
    date_hierarchy = "calculation_date"
    raw_id_fields = ["asset"]
