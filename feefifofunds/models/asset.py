from django.db import models

from utils.models import TimestampedModel


class Asset(TimestampedModel):
    class Category(models.TextChoices):
        STOCK = "STOCK", "Stock/ETF"
        CRYPTO = "CRYPTO", "Cryptocurrency"
        COMMODITY = "COMMODITY", "Commodity"
        CURRENCY = "CURRENCY", "Currency"

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
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        db_index=True,
        help_text="Asset category",
    )
    quote_currency = models.CharField(
        max_length=10,
        default="USD",
        help_text="Currency in which the asset is quoted (USD, EUR, BTC, etc.)",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the asset",
    )
    active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this asset is actively tracked",
    )

    class Meta:
        ordering = ["ticker"]
        verbose_name = "Asset"
        verbose_name_plural = "Assets"

    def __str__(self):
        return f"{self.ticker} - {self.name}"
