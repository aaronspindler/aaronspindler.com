from django.db import models

from utils.models import TimestampedModel


class Asset(TimestampedModel):
    class Category(models.TextChoices):
        STOCK = "STOCK", "Stock/ETF"
        CRYPTO = "CRYPTO", "Cryptocurrency"
        COMMODITY = "COMMODITY", "Commodity"
        CURRENCY = "CURRENCY", "Currency"

    class Tier(models.TextChoices):
        TIER1 = "TIER1", "Tier 1 - Major/Blue-chip"
        TIER2 = "TIER2", "Tier 2 - Mid-cap/Established"
        TIER3 = "TIER3", "Tier 3 - Small-cap/Emerging"
        TIER4 = "TIER4", "Tier 4 - Micro-cap/Speculative"
        UNCLASSIFIED = "UNCLASSIFIED", "Unclassified"

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
    tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
        default=Tier.UNCLASSIFIED,
        db_index=True,
        help_text="Asset tier classification based on market cap/importance",
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
