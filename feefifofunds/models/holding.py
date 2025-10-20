"""
FundHolding model - stores portfolio holdings and allocations.
"""

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .base import SoftDeleteModel, TimestampedModel


class FundHolding(TimestampedModel, SoftDeleteModel):
    """
    Represents a single holding (security) within a fund's portfolio.

    Tracks what securities a fund holds, their weights, and values.
    """

    class HoldingType(models.TextChoices):
        """Types of holdings."""

        EQUITY = "EQUITY", "Equity (Stock)"
        BOND = "BOND", "Bond"
        CASH = "CASH", "Cash & Equivalents"
        OPTION = "OPTION", "Option"
        FUTURE = "FUTURE", "Future"
        COMMODITY = "COMMODITY", "Commodity"
        REAL_ESTATE = "REIT", "Real Estate"
        OTHER = "OTHER", "Other"

    # Foreign key to fund
    fund = models.ForeignKey(
        "feefifofunds.Fund",
        on_delete=models.CASCADE,
        related_name="holdings",
        db_index=True,
        help_text="The fund that holds this security",
    )

    # Holding identification
    ticker = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Ticker symbol of the holding",
    )
    name = models.CharField(
        max_length=255,
        help_text="Full name of the holding",
    )
    cusip = models.CharField(
        max_length=9,
        blank=True,
        help_text="CUSIP identifier",
    )
    isin = models.CharField(
        max_length=12,
        blank=True,
        help_text="ISIN identifier",
    )

    # Holding classification
    holding_type = models.CharField(
        max_length=20,
        choices=HoldingType.choices,
        default=HoldingType.EQUITY,
        db_index=True,
        help_text="Type of security",
    )
    sector = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Sector classification (e.g., Technology, Healthcare)",
    )
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text="Industry classification",
    )
    country = models.CharField(
        max_length=3,
        blank=True,
        db_index=True,
        help_text="Country code (ISO 3166-1 alpha-3)",
    )

    # Position details
    shares = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Number of shares held",
    )
    market_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Market value of the position in fund currency",
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0000")), MaxValueValidator(Decimal("100.0000"))],
        help_text="Portfolio weight as a percentage (e.g., 5.25 for 5.25%)",
    )

    # Pricing
    price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Current price per share",
    )
    cost_basis = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Average cost basis per share",
    )

    # Temporal tracking
    as_of_date = models.DateField(
        db_index=True,
        help_text="Date when this holding data was reported",
    )
    previous_weight = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Weight in previous reporting period",
    )

    # Metadata
    data_source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Source of this holding data",
    )

    class Meta:
        db_table = "feefifofunds_holding"
        verbose_name = "Fund Holding"
        verbose_name_plural = "Fund Holdings"
        ordering = ["-weight"]
        unique_together = [["fund", "ticker", "as_of_date"]]
        indexes = [
            models.Index(fields=["fund", "-weight"]),
            models.Index(fields=["fund", "as_of_date"]),
            models.Index(fields=["ticker", "as_of_date"]),
            models.Index(fields=["holding_type", "-weight"]),
            models.Index(fields=["sector", "-weight"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.fund.ticker}: {self.ticker} ({self.weight}%)"

    @property
    def weight_change(self) -> Decimal | None:
        """Calculate change in weight from previous period."""
        if self.previous_weight is not None:
            return self.weight - self.previous_weight
        return None

    @property
    def unrealized_gain_loss(self) -> Decimal | None:
        """Calculate unrealized gain/loss if we have cost basis."""
        if self.cost_basis and self.price and self.shares:
            return (self.price - self.cost_basis) * self.shares
        return None

    @property
    def unrealized_gain_loss_percent(self) -> Decimal | None:
        """Calculate unrealized gain/loss as a percentage."""
        if self.cost_basis and self.price and self.cost_basis > 0:
            return ((self.price - self.cost_basis) / self.cost_basis) * 100
        return None

    @classmethod
    def get_top_holdings(cls, fund, n=10, as_of_date=None):
        """
        Get top N holdings for a fund.

        Args:
            fund: Fund instance or fund_id
            n: Number of top holdings to return
            as_of_date: Optional date to get holdings as of (defaults to latest)

        Returns:
            QuerySet of top holdings
        """
        queryset = cls.objects.filter(fund=fund, is_active=True)

        if as_of_date:
            queryset = queryset.filter(as_of_date=as_of_date)
        else:
            # Get the most recent as_of_date
            latest_date = queryset.order_by("-as_of_date").values_list("as_of_date", flat=True).first()
            if latest_date:
                queryset = queryset.filter(as_of_date=latest_date)

        return queryset.order_by("-weight")[:n]

    @classmethod
    def get_sector_allocation(cls, fund, as_of_date=None):
        """
        Get sector allocation breakdown for a fund.

        Args:
            fund: Fund instance or fund_id
            as_of_date: Optional date (defaults to latest)

        Returns:
            Dictionary mapping sectors to total weights
        """
        from django.db.models import Sum

        queryset = cls.objects.filter(fund=fund, is_active=True)

        if as_of_date:
            queryset = queryset.filter(as_of_date=as_of_date)
        else:
            latest_date = queryset.order_by("-as_of_date").values_list("as_of_date", flat=True).first()
            if latest_date:
                queryset = queryset.filter(as_of_date=latest_date)

        return dict(
            queryset.values("sector")
            .annotate(total_weight=Sum("weight"))
            .order_by("-total_weight")
            .values_list("sector", "total_weight")
        )

    @classmethod
    def get_country_allocation(cls, fund, as_of_date=None):
        """
        Get country allocation breakdown for a fund.

        Args:
            fund: Fund instance or fund_id
            as_of_date: Optional date (defaults to latest)

        Returns:
            Dictionary mapping countries to total weights
        """
        from django.db.models import Sum

        queryset = cls.objects.filter(fund=fund, is_active=True)

        if as_of_date:
            queryset = queryset.filter(as_of_date=as_of_date)
        else:
            latest_date = queryset.order_by("-as_of_date").values_list("as_of_date", flat=True).first()
            if latest_date:
                queryset = queryset.filter(as_of_date=latest_date)

        return dict(
            queryset.values("country")
            .annotate(total_weight=Sum("weight"))
            .order_by("-total_weight")
            .values_list("country", "total_weight")
        )
