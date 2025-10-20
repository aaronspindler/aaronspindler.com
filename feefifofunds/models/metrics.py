"""
FundMetrics model - stores calculated financial metrics and analytics.
"""

from decimal import Decimal

from django.db import models

from .base import SoftDeleteModel, TimestampedModel


class FundMetrics(TimestampedModel, SoftDeleteModel):
    """
    Calculated metrics and analytics for funds.

    Stores pre-calculated values for returns, risk metrics, and ratios
    to avoid recalculating on every request.
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

    # Foreign key to fund
    fund = models.ForeignKey(
        "feefifofunds.Fund",
        on_delete=models.CASCADE,
        related_name="metrics",
        db_index=True,
        help_text="The fund these metrics belong to",
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

    # Volatility metrics
    volatility = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Standard deviation of returns (annualized %)",
    )
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
        unique_together = [["fund", "calculation_date", "time_frame"]]
        indexes = [
            models.Index(fields=["fund", "-calculation_date"]),
            models.Index(fields=["fund", "time_frame", "-calculation_date"]),
            models.Index(fields=["-overall_score"]),
            models.Index(fields=["time_frame", "-overall_score"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.fund.ticker} Metrics - {self.time_frame} ({self.calculation_date})"

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
    def get_latest_for_fund(cls, fund, time_frame=None):
        """
        Get the most recent metrics for a fund.

        Args:
            fund: Fund instance or fund_id
            time_frame: Optional time frame filter

        Returns:
            FundMetrics instance or None
        """
        queryset = cls.objects.filter(fund=fund, is_active=True)
        if time_frame:
            queryset = queryset.filter(time_frame=time_frame)
        return queryset.order_by("-calculation_date").first()

    @classmethod
    def get_all_timeframes_for_fund(cls, fund, calculation_date=None):
        """
        Get metrics for all time frames for a fund.

        Args:
            fund: Fund instance or fund_id
            calculation_date: Optional specific date (defaults to latest)

        Returns:
            Dictionary mapping time frames to FundMetrics instances
        """
        queryset = cls.objects.filter(fund=fund, is_active=True)

        if calculation_date:
            queryset = queryset.filter(calculation_date=calculation_date)
        else:
            # Get latest calculation date
            latest_date = queryset.order_by("-calculation_date").values_list("calculation_date", flat=True).first()
            if latest_date:
                queryset = queryset.filter(calculation_date=latest_date)

        return {metric.time_frame: metric for metric in queryset}
