from django.db import models


class AssetPrice(models.Model):
    asset_id = models.IntegerField(
        db_index=True,
        help_text="ID of the asset this price record belongs to",
    )
    time = models.DateTimeField(
        db_index=True,
        help_text="Date and time of this price record",
    )
    open = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Opening price",
    )
    high = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Highest price during period",
    )
    low = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Lowest price during period",
    )
    close = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Closing price",
    )
    volume = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Trading volume (if applicable)",
    )
    interval_minutes = models.SmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Time interval in minutes (e.g., 1, 5, 15, 60, 1440 for daily). NULL for non-OHLCV data.",
    )
    trade_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of trades during this interval (for OHLCV data)",
    )
    quote_currency = models.CharField(
        max_length=10,
        default="USD",
        db_index=True,
        help_text="Currency in which the price is quoted (USD, EUR, BTC, etc.)",
    )
    source = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Data source for this price record (e.g., 'finnhub', 'massive', 'kraken')",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created",
    )

    class Meta:
        managed = False
        db_table = "assetprice"
        ordering = ["-time"]
        verbose_name = "Asset Price"
        verbose_name_plural = "Asset Prices"

    @property
    def asset(self):
        """Lazy load asset from PostgreSQL (default database)."""
        if not hasattr(self, "_asset"):
            from .asset import Asset

            self._asset = Asset.objects.get(id=self.asset_id)
        return self._asset

    def __str__(self):
        return f"Asset {self.asset_id} @ {self.time.strftime('%Y-%m-%d %H:%M')} ({self.source}): ${self.close}"
