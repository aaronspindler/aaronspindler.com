"""
Currency model - represents foreign exchange rates and currency pairs.
"""

from django.db import models

from .asset import Asset


class Currency(Asset):
    """
    Represents a currency or currency pair.

    Extends Asset base model with currency-specific fields.
    Can represent fiat currencies or be used for forex pairs.
    """

    class CurrencyType(models.TextChoices):
        """Type of currency."""

        FIAT = "FIAT", "Fiat Currency"
        DIGITAL = "DIGITAL", "Digital Currency (non-crypto)"
        COMMODITY = "COMMODITY", "Commodity-backed Currency"

    # Currency details
    currency_code = models.CharField(
        max_length=3,
        db_index=True,
        help_text="ISO 4217 currency code (e.g., USD, EUR, GBP)",
    )
    base_currency = models.CharField(
        max_length=3,
        default="USD",
        db_index=True,
        help_text="Base currency for exchange rate (usually USD)",
    )
    currency_type = models.CharField(
        max_length=10,
        choices=CurrencyType.choices,
        default=CurrencyType.FIAT,
        help_text="Type of currency",
    )

    # Geographic info
    country = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Primary country/region for this currency",
    )
    central_bank = models.CharField(
        max_length=255,
        blank=True,
        help_text="Central bank or monetary authority",
    )

    # Trading info
    is_major_currency = models.BooleanField(
        default=False,
        help_text="True if this is a major trading currency (USD, EUR, JPY, GBP, etc.)",
    )
    is_reserve_currency = models.BooleanField(
        default=False,
        help_text="True if this is a global reserve currency",
    )

    class Meta:
        db_table = "feefifofunds_currency"
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ["currency_code"]
        indexes = [
            models.Index(fields=["currency_code", "base_currency"]),
            models.Index(fields=["country"]),
            models.Index(fields=["is_major_currency"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        if self.base_currency and self.base_currency != "USD":
            return f"{self.currency_code}/{self.base_currency}"
        return self.currency_code

    @property
    def currency_pair(self) -> str:
        """Get the currency pair notation."""
        return f"{self.currency_code}/{self.base_currency}"
