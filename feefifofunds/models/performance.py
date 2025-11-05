"""
Performance models - store historical price, rate, and index data for assets.

Includes BasePerformance abstract model and asset-specific performance models.
Optimized for time-series queries and future TimescaleDB integration.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .base import SoftDeleteModel, TimestampedModel


class BasePerformance(TimestampedModel, SoftDeleteModel):
    """
    Abstract base model for asset performance/price history.

    Provides common fields for all performance tracking models.

    Note: Uses composite primary key (asset, date, interval) for TimescaleDB compatibility.
    Django's auto id field is disabled to allow partitioning on the date column.
    """

    class Interval(models.TextChoices):
        """Time intervals for aggregated data."""

        DAILY = "1D", "Daily"
        WEEKLY = "1W", "Weekly"
        MONTHLY = "1M", "Monthly"
        QUARTERLY = "1Q", "Quarterly"
        YEARLY = "1Y", "Yearly"

    # Disable Django's auto-incrementing id for TimescaleDB compatibility
    # Use bulk_create with update_conflicts instead of update_or_create
    id = None

    # Foreign key to asset (part of composite PK)
    asset = models.ForeignKey(
        "feefifofunds.Asset",
        on_delete=models.CASCADE,
        related_name="%(class)s_history",
        db_index=True,
        help_text="The asset this performance data belongs to",
    )

    # Time dimension (part of composite PK)
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

    # Generic value field
    value = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Generic value (price, rate, index, etc.)",
    )

    # Data source tracking
    data_source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Source of this data",
    )
    data_quality_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MinValueValidator(100)],
        help_text="Data quality score (0-100)",
    )

    class Meta:
        abstract = True
        ordering = ["-date"]


class FundPerformance(BasePerformance):
    """
    Historical performance data for funds.

    Extends BasePerformance with fund-specific OHLCV (Open, High, Low, Close, Volume) data.
    Designed to work with TimescaleDB hypertables for optimal time-series performance.
    """

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

    class Meta:
        db_table = "feefifofunds_performance"
        verbose_name = "Fund Performance"
        verbose_name_plural = "Fund Performance Records"
        ordering = ["-date"]
        # Unique constraint for composite key (database has this as PK)
        unique_together = [["asset", "date", "interval"]]
        indexes = [
            # Primary time-series query patterns
            models.Index(fields=["asset", "-date"]),
            models.Index(fields=["asset", "-date", "interval"]),
            models.Index(fields=["date", "asset"]),
            # For aggregations and analytics
            models.Index(fields=["interval", "-date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.ticker} - {self.date} ({self.interval})"

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
    def get_date_range_for_asset(cls, asset, start_date, end_date, interval="1D"):
        """
        Get performance data for an asset within a date range.

        Args:
            asset: Asset instance or asset_id
            start_date: Start date
            end_date: End date
            interval: Time interval (default: daily)

        Returns:
            QuerySet of FundPerformance records
        """
        return cls.objects.filter(
            asset=asset, date__gte=start_date, date__lte=end_date, interval=interval, is_active=True
        ).order_by("date")

    @classmethod
    def get_latest_for_asset(cls, asset, interval="1D"):
        """
        Get the most recent performance record for an asset.

        Args:
            asset: Asset instance or asset_id
            interval: Time interval (default: daily)

        Returns:
            FundPerformance instance or None
        """
        return cls.objects.filter(asset=asset, interval=interval, is_active=True).order_by("-date").first()

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


class CryptoPerformance(BasePerformance):
    """
    Historical performance data for cryptocurrencies.

    Extends BasePerformance with crypto-specific OHLCV and market data.
    """

    # OHLCV data
    open_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Opening price for the period",
    )
    high_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Highest price during the period",
    )
    low_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Lowest price during the period",
    )
    close_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Closing price for the period",
    )

    # Volume (24h trading volume in USD)
    volume_24h = models.DecimalField(
        max_digits=25,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="24-hour trading volume in USD",
    )
    volume_crypto = models.DecimalField(
        max_digits=30,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="24-hour trading volume in cryptocurrency units",
    )

    # Market data
    market_cap = models.DecimalField(
        max_digits=25,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Market capitalization in USD",
    )
    total_value_locked = models.DecimalField(
        max_digits=25,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total Value Locked (for DeFi tokens)",
    )

    # Calculated fields
    daily_return = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Daily return as a decimal",
    )
    log_return = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Natural log return",
    )

    class Meta:
        db_table = "feefifofunds_crypto_performance"
        verbose_name = "Crypto Performance"
        verbose_name_plural = "Crypto Performance Records"
        ordering = ["-date"]
        # Note: These fields form the composite primary key (set up in migration for TimescaleDB)
        unique_together = [["asset", "date", "interval"]]
        indexes = [
            models.Index(fields=["asset", "-date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.ticker} - {self.date} ({self.interval})"


class InflationData(BasePerformance):
    """
    Historical inflation index data.

    Extends BasePerformance with inflation-specific fields.
    """

    # Index value
    index_value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Index value (e.g., CPI value)",
    )

    # Rate calculations
    annual_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Year-over-year inflation rate as percentage",
    )
    monthly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Month-over-month inflation rate as percentage",
    )

    # Core index (excluding food/energy)
    core_index_value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Core index value (excluding volatile components)",
    )

    class Meta:
        db_table = "feefifofunds_inflation_data"
        verbose_name = "Inflation Data"
        verbose_name_plural = "Inflation Data Records"
        ordering = ["-date"]
        # Note: These fields form the composite primary key (set up in migration for TimescaleDB)
        unique_together = [["asset", "date", "interval"]]
        indexes = [
            models.Index(fields=["asset", "-date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.ticker} - {self.date}: {self.index_value}"


class SavingsRateHistory(BasePerformance):
    """
    Historical savings account rate data.

    Extends BasePerformance with savings rate-specific fields.
    """

    # Interest rates
    annual_percentage_yield = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0000"))],
        help_text="Annual Percentage Yield (APY)",
    )
    interest_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0000"))],
        help_text="Nominal interest rate",
    )

    # Compounding
    compounding_frequency = models.CharField(
        max_length=10,
        choices=[
            ("DAILY", "Daily"),
            ("MONTHLY", "Monthly"),
            ("QUARTERLY", "Quarterly"),
            ("ANNUALLY", "Annually"),
        ],
        default="MONTHLY",
        help_text="Compounding frequency",
    )

    # Effective rate
    effective_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0000"))],
        help_text="Calculated effective annual rate",
    )

    class Meta:
        db_table = "feefifofunds_savings_rate"
        verbose_name = "Savings Rate History"
        verbose_name_plural = "Savings Rate History"
        ordering = ["-date"]
        # Note: These fields form the composite primary key (set up in migration for TimescaleDB)
        unique_together = [["asset", "date", "interval"]]
        indexes = [
            models.Index(fields=["asset", "-date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.name} - {self.date}: {self.annual_percentage_yield}% APY"


class PropertyValuation(BasePerformance):
    """
    Historical property valuation data.

    Extends BasePerformance with real estate-specific fields.
    """

    class ValuationMethod(models.TextChoices):
        """Method used for valuation."""

        APPRAISAL = "APPRAISAL", "Professional Appraisal"
        MARKET_COMP = "MARKET", "Market Comparables"
        INDEX = "INDEX", "Real Estate Index"
        ASSESSMENT = "ASSESSMENT", "Tax Assessment"
        AUTOMATED = "AUTOMATED", "Automated Valuation Model"

    # Valuation
    assessed_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Tax assessed value",
    )
    market_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Market value or estimated price",
    )

    # Rental income (for investment properties)
    rental_income_monthly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Monthly rental income",
    )
    occupancy_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Occupancy rate as percentage",
    )

    # Valuation method
    valuation_method = models.CharField(
        max_length=12,
        choices=ValuationMethod.choices,
        default=ValuationMethod.MARKET_COMP,
        help_text="Method used for this valuation",
    )

    class Meta:
        db_table = "feefifofunds_property_valuation"
        verbose_name = "Property Valuation"
        verbose_name_plural = "Property Valuations"
        ordering = ["-date"]
        # Note: These fields form the composite primary key (set up in migration for TimescaleDB)
        unique_together = [["asset", "date", "interval"]]
        indexes = [
            models.Index(fields=["asset", "-date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.name} - {self.date}: ${self.market_value}"


class CurrencyPerformance(BasePerformance):
    """
    Historical currency exchange rate data.

    Extends BasePerformance with forex-specific fields.
    """

    # Exchange rates
    exchange_rate = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Exchange rate (how much base currency per unit)",
    )
    bid_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Bid price (buy price)",
    )
    ask_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Ask price (sell price)",
    )

    # Spread
    spread = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Bid-ask spread",
    )

    # Returns
    daily_return = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Daily return as a decimal",
    )
    log_return = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Natural log return",
    )

    class Meta:
        db_table = "feefifofunds_currency_performance"
        verbose_name = "Currency Performance"
        verbose_name_plural = "Currency Performance Records"
        ordering = ["-date"]
        # Note: These fields form the composite primary key (set up in migration for TimescaleDB)
        unique_together = [["asset", "date", "interval"]]
        indexes = [
            models.Index(fields=["asset", "-date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.asset.ticker} - {self.date}: {self.exchange_rate}"

    def save(self, *args, **kwargs):
        """Override save to calculate spread."""
        if self.bid_price and self.ask_price:
            self.spread = self.ask_price - self.bid_price
        super().save(*args, **kwargs)


class CommodityPerformance(BasePerformance):
    """
    Historical commodity price data.

    Extends BasePerformance with commodity-specific fields.
    """

    # Price data
    spot_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Spot price",
    )
    futures_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Futures price (if applicable)",
    )

    # OHLC data
    open_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Opening price",
    )
    high_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="High price",
    )
    low_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Low price",
    )
    close_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Closing price",
    )

    # Trading volume
    volume = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Trading volume (contracts or units)",
    )
    open_interest = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Open interest (for futures)",
    )

    # Returns
    daily_return = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Daily return as a decimal",
    )
    log_return = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Natural log return",
    )

    class Meta:
        db_table = "feefifofunds_commodity_performance"
        verbose_name = "Commodity Performance"
        verbose_name_plural = "Commodity Performance Records"
        ordering = ["-date"]
        # Note: These fields form the composite primary key (set up in migration for TimescaleDB)
        unique_together = [["asset", "date", "interval"]]
        indexes = [
            models.Index(fields=["asset", "-date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        price = self.spot_price or self.futures_price or self.close_price
        return f"{self.asset.ticker} - {self.date}: ${price}"
