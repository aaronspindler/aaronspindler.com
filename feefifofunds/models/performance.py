"""
FundPerformance model - stores historical price and volume data.

Optimized for time-series queries and future TimescaleDB integration.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .base import SoftDeleteModel, TimestampedModel


class FundPerformance(TimestampedModel, SoftDeleteModel):
    """
    Historical performance data for funds.

    Stores OHLCV (Open, High, Low, Close, Volume) data by date.
    Designed to work with TimescaleDB hypertables for optimal time-series performance.
    """

    class Interval(models.TextChoices):
        """Time intervals for aggregated data."""

        DAILY = "1D", "Daily"
        WEEKLY = "1W", "Weekly"
        MONTHLY = "1M", "Monthly"
        QUARTERLY = "1Q", "Quarterly"
        YEARLY = "1Y", "Yearly"

    # Foreign key to fund
    fund = models.ForeignKey(
        "feefifofunds.Fund",
        on_delete=models.CASCADE,
        related_name="performance_history",
        db_index=True,
        help_text="The fund this performance data belongs to",
    )

    # Time dimension
    date = models.DateField(
        db_index=True,
        help_text="Date of this performance record",
    )
    interval = models.CharField(
        max_length=2,
        choices=Interval.choices,
        default=Interval.DAILY,
        help_text="Time interval for this data point",
    )

    # OHLCV data
    open_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Opening price for the period",
    )
    high_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Highest price during the period",
    )
    low_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Lowest price during the period",
    )
    close_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Closing price (or NAV) for the period",
    )
    adjusted_close = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Adjusted closing price (accounting for splits, dividends)",
    )

    # Volume and trading activity
    volume = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Trading volume (number of shares)",
    )
    dollar_volume = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Dollar volume (volume * price)",
    )

    # Distributions
    dividend = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        default=Decimal("0.0000"),
        help_text="Dividend paid on this date",
    )
    split_ratio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Stock split ratio (e.g., 2.0 for 2:1 split)",
    )

    # Calculated fields
    daily_return = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Daily return as a decimal (e.g., 0.015 for 1.5%)",
    )
    log_return = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Natural log return for statistical calculations",
    )

    # Data source tracking
    data_source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Source of this data (e.g., 'alpha_vantage', 'polygon', 'manual')",
    )
    data_quality_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MinValueValidator(100)],
        help_text="Data quality score (0-100), calculated during validation",
    )

    class Meta:
        db_table = "feefifofunds_performance"
        verbose_name = "Fund Performance"
        verbose_name_plural = "Fund Performance Records"
        ordering = ["-date"]
        unique_together = [["fund", "date", "interval"]]
        indexes = [
            # Primary time-series query patterns
            models.Index(fields=["fund", "-date"]),
            models.Index(fields=["fund", "-date", "interval"]),
            models.Index(fields=["date", "fund"]),
            # For aggregations and analytics
            models.Index(fields=["interval", "-date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.fund.ticker} - {self.date} ({self.interval})"

    def save(self, *args, **kwargs):
        """Override save to calculate derived fields."""
        # Calculate dollar volume if we have both volume and close price
        if self.volume and self.close_price:
            self.dollar_volume = Decimal(str(self.volume)) * self.close_price

        super().save(*args, **kwargs)

    @property
    def intraday_change(self) -> Decimal | None:
        """Calculate intraday price change."""
        if self.open_price and self.close_price:
            return self.close_price - self.open_price
        return None

    @property
    def intraday_change_percent(self) -> Decimal | None:
        """Calculate intraday percentage change."""
        if self.open_price and self.close_price and self.open_price > 0:
            change = self.close_price - self.open_price
            return (change / self.open_price) * 100
        return None

    @property
    def intraday_range(self) -> Decimal | None:
        """Calculate intraday trading range."""
        if self.high_price and self.low_price:
            return self.high_price - self.low_price
        return None

    @property
    def has_split(self) -> bool:
        """Check if a stock split occurred."""
        return self.split_ratio is not None and self.split_ratio != Decimal("1.0000")

    @property
    def has_dividend(self) -> bool:
        """Check if a dividend was paid."""
        return self.dividend is not None and self.dividend > 0

    @classmethod
    def get_date_range_for_fund(cls, fund, start_date, end_date, interval="1D"):
        """
        Get performance data for a fund within a date range.

        Args:
            fund: Fund instance or fund_id
            start_date: Start date
            end_date: End date
            interval: Time interval (default: daily)

        Returns:
            QuerySet of FundPerformance records
        """
        return cls.objects.filter(
            fund=fund, date__gte=start_date, date__lte=end_date, interval=interval, is_active=True
        ).order_by("date")

    @classmethod
    def get_latest_for_fund(cls, fund, interval="1D"):
        """
        Get the most recent performance record for a fund.

        Args:
            fund: Fund instance or fund_id
            interval: Time interval (default: daily)

        Returns:
            FundPerformance instance or None
        """
        return cls.objects.filter(fund=fund, interval=interval, is_active=True).order_by("-date").first()

    def calculate_return_from_previous(self, previous_close: Decimal) -> tuple[Decimal | None, Decimal | None]:
        """
        Calculate returns relative to a previous closing price.

        Args:
            previous_close: Previous closing price

        Returns:
            Tuple of (daily_return, log_return)
        """
        import math

        if not previous_close or previous_close <= 0:
            return None, None

        # Simple return
        daily_return = (self.close_price - previous_close) / previous_close

        # Log return
        try:
            log_return = Decimal(str(math.log(float(self.close_price / previous_close))))
        except (ValueError, ZeroDivisionError):
            log_return = None

        return daily_return, log_return
