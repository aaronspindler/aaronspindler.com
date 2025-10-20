"""
Fund model - represents mutual funds, ETFs, and other investment funds.
"""

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .base import SoftDeleteModel, TimestampedModel


class Fund(TimestampedModel, SoftDeleteModel):
    """
    Represents a mutual fund, ETF, or other investment fund.

    Core model that stores master fund information and metadata.
    """

    class FundType(models.TextChoices):
        """Types of investment funds."""

        ETF = "ETF", "Exchange-Traded Fund"
        MUTUAL_FUND = "MUTUAL", "Mutual Fund"
        INDEX_FUND = "INDEX", "Index Fund"
        BOND_FUND = "BOND", "Bond Fund"
        MONEY_MARKET = "MM", "Money Market Fund"
        TARGET_DATE = "TARGET", "Target Date Fund"
        OTHER = "OTHER", "Other"

    class AssetClass(models.TextChoices):
        """Primary asset class of the fund."""

        EQUITY = "EQUITY", "Equity"
        FIXED_INCOME = "BOND", "Fixed Income"
        MIXED = "MIXED", "Mixed/Balanced"
        MONEY_MARKET = "MM", "Money Market"
        COMMODITY = "COMMODITY", "Commodity"
        REAL_ESTATE = "REIT", "Real Estate"
        ALTERNATIVE = "ALT", "Alternative"

    # Core identification
    ticker = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Primary ticker symbol",
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Full fund name",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        blank=True,
        help_text="URL-friendly slug",
    )

    # Fund classification
    fund_type = models.CharField(
        max_length=10,
        choices=FundType.choices,
        default=FundType.ETF,
        db_index=True,
        help_text="Type of fund",
    )
    asset_class = models.CharField(
        max_length=20,
        choices=AssetClass.choices,
        default=AssetClass.EQUITY,
        db_index=True,
        help_text="Primary asset class",
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Morningstar or similar category",
    )

    # Fund details
    description = models.TextField(
        blank=True,
        help_text="Fund description and investment strategy",
    )
    inception_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when the fund was launched",
    )
    issuer = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Fund issuer/provider (e.g., Vanguard, iShares)",
    )

    # Costs and fees
    expense_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0000")), MaxValueValidator(Decimal("99.9999"))],
        help_text="Annual expense ratio as a percentage (e.g., 0.03 for 0.03%)",
    )
    management_fee = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0000")), MaxValueValidator(Decimal("99.9999"))],
        help_text="Management fee as a percentage",
    )
    front_load = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0000")), MaxValueValidator(Decimal("99.9999"))],
        help_text="Front-end load fee as a percentage",
    )
    back_load = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0000")), MaxValueValidator(Decimal("99.9999"))],
        help_text="Back-end load fee as a percentage",
    )

    # Current state
    current_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Most recent NAV or price",
    )
    previous_close = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Previous closing price",
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="Currency code (ISO 4217)",
    )

    # Fund size and liquidity
    aum = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Assets Under Management in millions",
    )
    avg_volume = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Average daily trading volume (shares)",
    )

    # Metadata
    exchange = models.CharField(
        max_length=50,
        blank=True,
        help_text="Primary exchange where the fund trades",
    )
    website = models.URLField(
        blank=True,
        max_length=500,
        help_text="Official fund website",
    )
    isin = models.CharField(
        max_length=12,
        blank=True,
        unique=True,
        null=True,
        help_text="International Securities Identification Number",
    )
    cusip = models.CharField(
        max_length=9,
        blank=True,
        help_text="Committee on Uniform Securities Identification Procedures number",
    )

    # Data freshness
    last_updated = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the fund data was last updated from external sources",
    )
    last_price_update = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the price was last updated",
    )

    class Meta:
        db_table = "feefifofunds_fund"
        verbose_name = "Fund"
        verbose_name_plural = "Funds"
        ordering = ["ticker"]
        indexes = [
            models.Index(fields=["ticker", "is_active"]),
            models.Index(fields=["fund_type", "asset_class"]),
            models.Index(fields=["category"]),
            models.Index(fields=["expense_ratio"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.ticker} - {self.name}"

    def save(self, *args, **kwargs):
        """Override save to auto-generate slug."""
        if not self.slug:
            self.slug = slugify(f"{self.ticker}-{self.name}")
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        """Get the canonical URL for this fund."""
        return reverse("feefifofunds:fund-detail", kwargs={"slug": self.slug})

    @property
    def price_change(self) -> Decimal | None:
        """Calculate price change from previous close."""
        if self.current_price and self.previous_close:
            return self.current_price - self.previous_close
        return None

    @property
    def price_change_percent(self) -> Decimal | None:
        """Calculate percentage price change from previous close."""
        if self.current_price and self.previous_close and self.previous_close > 0:
            change = self.current_price - self.previous_close
            return (change / self.previous_close) * 100
        return None

    @property
    def total_cost_percent(self) -> Decimal:
        """Calculate total cost including all fees."""
        total = Decimal("0.0000")
        if self.expense_ratio:
            total += self.expense_ratio
        if self.management_fee:
            total += self.management_fee
        return total

    def get_latest_performance(self, limit: int = 30):
        """
        Get recent performance data.

        Args:
            limit: Number of days to retrieve

        Returns:
            QuerySet of FundPerformance records
        """
        return self.performance_history.filter(is_active=True).order_by("-date")[:limit]

    def get_holdings(self, top_n: int | None = None):
        """
        Get fund holdings.

        Args:
            top_n: If specified, return only top N holdings by weight

        Returns:
            QuerySet of FundHolding records
        """
        holdings = self.holdings.filter(is_active=True).order_by("-weight")
        if top_n:
            return holdings[:top_n]
        return holdings

    def get_latest_metrics(self):
        """Get the most recent calculated metrics."""
        return self.metrics.filter(is_active=True).order_by("-calculation_date").first()
