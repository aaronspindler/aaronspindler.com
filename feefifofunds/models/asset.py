"""
Asset base model - polymorphic base for all financial assets.

This module provides the base Asset model using django-polymorphic, allowing
different asset types (funds, crypto, real estate, etc.) to share common fields
while maintaining type-specific functionality.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from polymorphic.models import PolymorphicModel

from .base import SoftDeleteModel, TimestampedModel


class Asset(PolymorphicModel, TimestampedModel, SoftDeleteModel):
    """
    Base model for all financial assets.

    Provides common fields and functionality for funds, cryptocurrencies,
    inflation indices, savings accounts, real estate, and other asset types.
    Uses django-polymorphic for clean inheritance and querying.
    """

    # Core identification
    ticker = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Primary ticker symbol or identifier",
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Full asset name",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        blank=True,
        help_text="URL-friendly slug",
    )

    # Description
    description = models.TextField(
        blank=True,
        help_text="Asset description and details",
    )

    # Current state
    current_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Most recent price/value/rate",
    )
    previous_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Previous value for change calculation",
    )
    quote_currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="Currency code for quotes/prices (ISO 4217)",
    )

    # Metadata
    website = models.URLField(
        blank=True,
        max_length=500,
        help_text="Official website",
    )
    last_updated = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the asset data was last updated from external sources",
    )
    data_source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Primary data source for this asset",
    )

    class Meta:
        db_table = "feefifofunds_asset"
        verbose_name = "Asset"
        verbose_name_plural = "Assets"
        ordering = ["ticker"]
        indexes = [
            models.Index(fields=["ticker", "is_active"]),
            models.Index(fields=["name"]),
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
        """Get the canonical URL for this asset."""
        return reverse("feefifofunds:asset-detail", kwargs={"slug": self.slug})

    @property
    def value_change(self) -> Decimal | None:
        """Calculate value change from previous value."""
        if self.current_value and self.previous_value:
            return self.current_value - self.previous_value
        return None

    @property
    def value_change_percent(self) -> Decimal | None:
        """Calculate percentage value change from previous value."""
        if self.current_value and self.previous_value and self.previous_value > 0:
            change = self.current_value - self.previous_value
            return (change / self.previous_value) * 100
        return None

    @property
    def asset_type_display(self) -> str:
        """Get human-readable asset type from polymorphic type."""
        return self.polymorphic_ctype.model if self.polymorphic_ctype else "Unknown"
