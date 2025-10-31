"""
Metrics models - store calculated financial metrics and analytics for assets.

Includes BaseMetrics abstract model and asset-specific metrics models.
"""

from decimal import Decimal

from django.db import models

from .base import SoftDeleteModel, TimestampedModel


class BaseMetrics(TimestampedModel, SoftDeleteModel):
    """
    Abstract base model for asset metrics and analytics.

    Provides common fields for all metrics tracking models.
    """

    class TimeFrame(models.TextChoices):
        """Time frames for metric calculations."""

        ONE_MONTH = "1M", "1 Month"
        THREE_MONTH = "3M", "3 Months"
        SIX_MONTH = "6M", "6 Months"
        YTD = "YTD", "Year-to-Date"
        ONE_YEAR = "1Y", "1 Year"
        THREE_YEAR = "3Y", "3 Years"
        FIVE_YEAR = "5Y", "5 Years"
        TEN_YEAR = "10Y", "10 Years"
        ALL_TIME = "ALL", "All Time"

    # Foreign key to asset
    asset = models.ForeignKey(
        "feefifofunds.Asset",
        on_delete=models.CASCADE,
        related_name="%(class)s_records",
        db_index=True,
        help_text="The asset these metrics belong to",
    )

    # Metadata
    calculation_date = models.DateField(
        db_index=True,
        help_text="Date when these metrics were calculated",
    )
    time_frame = models.CharField(
        max_length=3,
        choices=TimeFrame.choices,
        default=TimeFrame.ONE_YEAR,
        db_index=True,
        help_text="Time frame for these metrics",
    )
    data_points = models.IntegerField(
        help_text="Number of data points used in calculations",
    )

    # Returns (as percentages)
    total_return = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Total return as a percentage",
    )
    annualized_return = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Annualized return as a percentage",
    )
    cumulative_return = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Cumulative return as a percentage",
    )

    # Volatility
    volatility = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Standard deviation of returns (annualized %)",
    )

    # Drawdown
    max_drawdown = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Maximum drawdown as a percentage",
    )

    # Calculation metadata
    calculation_engine_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Version of the calculation engine used",
    )
    calculation_duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Time taken to calculate these metrics in milliseconds",
    )

    class Meta:
        abstract = True
        ordering = ["-calculation_date"]


class FundMetrics(BaseMetrics):
    """
    Calculated metrics and analytics for funds.

    Extends BaseMetrics with comprehensive fund-specific metrics.
    """

    # Extended volatility metrics
    downside_deviation = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Downside deviation (only negative returns)",
    )

    # Risk metrics
    beta = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Beta relative to benchmark (e.g., S&P 500)",
    )
    alpha = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Alpha (excess return) as a percentage",
    )
    r_squared = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="R-squared (0.0 to 1.0) - correlation to benchmark",
    )

    # Risk-adjusted returns
    sharpe_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sharpe ratio (return per unit of risk)",
    )
    sortino_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sortino ratio (return per unit of downside risk)",
    )
    treynor_ratio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Treynor ratio (return per unit of systematic risk)",
    )
    information_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Information ratio (active return / tracking error)",
    )

    # Drawdown metrics
    max_drawdown = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Maximum drawdown as a percentage",
    )
    max_drawdown_duration = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of maximum drawdown in days",
    )
    current_drawdown = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Current drawdown from peak as a percentage",
    )

    # Value at Risk
    var_95 = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Value at Risk at 95% confidence (1-day)",
    )
    var_99 = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Value at Risk at 99% confidence (1-day)",
    )
    cvar_95 = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Conditional VaR (expected shortfall) at 95%",
    )

    # Performance statistics
    win_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percentage of positive return periods",
    )
    best_day = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Best single-day return as a percentage",
    )
    worst_day = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Worst single-day return as a percentage",
    )
    avg_positive_day = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Average return on positive days",
    )
    avg_negative_day = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Average return on negative days",
    )

    # Benchmark comparison
    benchmark_ticker = models.CharField(
        max_length=20,
        blank=True,
        help_text="Benchmark used for comparison (e.g., 'SPY' for S&P 500)",
    )
    excess_return = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Return above benchmark",
    )
    tracking_error = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Standard deviation of excess returns",
    )

    # Distribution characteristics
    skewness = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Skewness of return distribution",
    )
    kurtosis = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Kurtosis of return distribution",
    )

    # Composite scores (for ranking/comparison)
    risk_score = models.IntegerField(
        null=True,
        blank=True,
        help_text="Risk score (0-100, higher = more risk)",
    )
    return_score = models.IntegerField(
        null=True,
        blank=True,
        help_text="Return score (0-100, higher = better returns)",
    )
    overall_score = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Overall composite score (0-100)",
    )

    # Calculation metadata
    calculation_engine_version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Version of the calculation engine used",
    )
    calculation_duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Time taken to calculate these metrics in milliseconds",
    )

    class Meta:
        db_table = "feefifofunds_metrics"
        verbose_name = "Fund Metrics"
        verbose_name_plural = "Fund Metrics"
        ordering = ["-calculation_date"]
        unique_together = [["asset", "calculation_date", "time_frame"]]
        indexes = [
            models.Index(fields=["asset", "-calculation_date"]),
            models.Index(fields=["asset", "time_frame", "-calculation_date"]),
            models.Index(fields=["-overall_score"]),
            models.Index(fields=["time_frame", "-overall_score"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.ticker} Metrics - {self.time_frame} ({self.calculation_date})"

    @property
    def is_outperforming_benchmark(self) -> bool | None:
        """Check if fund is outperforming its benchmark."""
        if self.excess_return is not None:
            return self.excess_return > 0
        return None

    @property
    def risk_adjusted_return_score(self) -> Decimal | None:
        """Calculate a simple risk-adjusted return score."""
        if self.sharpe_ratio is not None and self.sortino_ratio is not None:
            # Average of Sharpe and Sortino as a simple composite
            return (self.sharpe_ratio + self.sortino_ratio) / 2
        return None

    @classmethod
    def get_latest_for_asset(cls, asset, time_frame=None):
        """
        Get the most recent metrics for an asset.

        Args:
            asset: Asset instance or asset_id
            time_frame: Optional time frame filter

        Returns:
            FundMetrics instance or None
        """
        queryset = cls.objects.filter(asset=asset, is_active=True)
        if time_frame:
            queryset = queryset.filter(time_frame=time_frame)
        return queryset.order_by("-calculation_date").first()

    @classmethod
    def get_all_timeframes_for_asset(cls, asset, calculation_date=None):
        """
        Get metrics for all time frames for an asset.

        Args:
            asset: Asset instance or asset_id
            calculation_date: Optional specific date (defaults to latest)

        Returns:
            Dictionary mapping time frames to FundMetrics instances
        """
        queryset = cls.objects.filter(asset=asset, is_active=True)

        if calculation_date:
            queryset = queryset.filter(calculation_date=calculation_date)
        else:
            # Get latest calculation date
            latest_date = queryset.order_by("-calculation_date").values_list("calculation_date", flat=True).first()
            if latest_date:
                queryset = queryset.filter(calculation_date=latest_date)

        return {metric.time_frame: metric for metric in queryset}


class CryptoMetrics(BaseMetrics):
    """
    Calculated metrics for cryptocurrencies.

    Extends BaseMetrics with crypto-specific metrics.
    """

    # Risk-adjusted returns
    sharpe_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sharpe ratio (return per unit of risk)",
    )
    sortino_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sortino ratio (return per unit of downside risk)",
    )

    # Drawdown metrics
    max_drawdown_duration = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration of maximum drawdown in days",
    )
    current_drawdown = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Current drawdown from peak as a percentage",
    )

    # Benchmark comparison
    correlation_to_btc = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Correlation coefficient to Bitcoin (-1 to 1)",
    )

    # Statistics
    win_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percentage of positive return periods",
    )
    best_day = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Best single-day return as a percentage",
    )
    worst_day = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Worst single-day return as a percentage",
    )

    class Meta:
        db_table = "feefifofunds_crypto_metrics"
        verbose_name = "Crypto Metrics"
        verbose_name_plural = "Crypto Metrics"
        unique_together = [["asset", "calculation_date", "time_frame"]]
        indexes = [
            models.Index(fields=["asset", "-calculation_date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.ticker} Crypto Metrics - {self.time_frame} ({self.calculation_date})"


class CurrencyMetrics(BaseMetrics):
    """
    Calculated metrics for currencies/forex.

    Extends BaseMetrics with currency-specific metrics.
    """

    # Risk metrics
    sharpe_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sharpe ratio",
    )

    # Drawdown
    current_drawdown = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Current drawdown from peak as a percentage",
    )

    # Statistics
    win_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percentage of positive return periods",
    )

    class Meta:
        db_table = "feefifofunds_currency_metrics"
        verbose_name = "Currency Metrics"
        verbose_name_plural = "Currency Metrics"
        unique_together = [["asset", "calculation_date", "time_frame"]]
        indexes = [
            models.Index(fields=["asset", "-calculation_date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.ticker} Currency Metrics - {self.time_frame} ({self.calculation_date})"


class CommodityMetrics(BaseMetrics):
    """
    Calculated metrics for commodities.

    Extends BaseMetrics with commodity-specific metrics.
    """

    # Risk metrics
    sharpe_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sharpe ratio",
    )
    sortino_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sortino ratio",
    )

    # Drawdown
    current_drawdown = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Current drawdown from peak",
    )

    # Statistics
    win_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percentage of positive return periods",
    )
    best_day = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Best single-day return",
    )
    worst_day = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Worst single-day return",
    )

    class Meta:
        db_table = "feefifofunds_commodity_metrics"
        verbose_name = "Commodity Metrics"
        verbose_name_plural = "Commodity Metrics"
        unique_together = [["asset", "calculation_date", "time_frame"]]
        indexes = [
            models.Index(fields=["asset", "-calculation_date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.ticker} Commodity Metrics - {self.time_frame} ({self.calculation_date})"


class InflationMetrics(BaseMetrics):
    """
    Calculated metrics for inflation indices.

    Extends BaseMetrics with inflation-specific metrics.
    """

    # Inflation-specific metrics
    average_annual_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Average annual inflation rate for period",
    )
    cumulative_inflation = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Cumulative inflation since base year (%)",
    )
    purchasing_power_change = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Change in purchasing power (%)",
    )

    # Trend
    trend_direction = models.CharField(
        max_length=15,
        choices=[
            ("INCREASING", "Increasing"),
            ("DECREASING", "Decreasing"),
            ("STABLE", "Stable"),
        ],
        blank=True,
        help_text="Trend direction of inflation",
    )

    class Meta:
        db_table = "feefifofunds_inflation_metrics"
        verbose_name = "Inflation Metrics"
        verbose_name_plural = "Inflation Metrics"
        unique_together = [["asset", "calculation_date", "time_frame"]]
        indexes = [
            models.Index(fields=["asset", "-calculation_date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.ticker} Inflation Metrics - {self.time_frame} ({self.calculation_date})"


class SavingsMetrics(BaseMetrics):
    """
    Calculated metrics for savings accounts.

    Extends BaseMetrics with savings-specific metrics.
    """

    # Savings-specific metrics
    effective_annual_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Weighted average effective annual rate",
    )
    total_interest_earned = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total interest earned in period",
    )
    real_return = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Real return after inflation adjustment (%)",
    )
    rate_stability_score = models.IntegerField(
        null=True,
        blank=True,
        help_text="Rate stability score (0-100, higher = more stable)",
    )

    class Meta:
        db_table = "feefifofunds_savings_metrics"
        verbose_name = "Savings Metrics"
        verbose_name_plural = "Savings Metrics"
        unique_together = [["asset", "calculation_date", "time_frame"]]
        indexes = [
            models.Index(fields=["asset", "-calculation_date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.name} Savings Metrics - {self.time_frame} ({self.calculation_date})"


class RealEstateMetrics(BaseMetrics):
    """
    Calculated metrics for real estate.

    Extends BaseMetrics with real estate-specific metrics.
    """

    # Real estate-specific metrics
    cap_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Capitalization rate (NOI / property value) %",
    )
    cash_on_cash_return = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Cash on cash return %",
    )
    rental_yield = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Annual rental yield %",
    )
    appreciation_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Annual appreciation rate %",
    )

    # For indices/REITs
    sharpe_ratio = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Sharpe ratio (for indices/REITs)",
    )

    class Meta:
        db_table = "feefifofunds_realestate_metrics"
        verbose_name = "Real Estate Metrics"
        verbose_name_plural = "Real Estate Metrics"
        unique_together = [["asset", "calculation_date", "time_frame"]]
        indexes = [
            models.Index(fields=["asset", "-calculation_date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.name} Real Estate Metrics - {self.time_frame} ({self.calculation_date})"
