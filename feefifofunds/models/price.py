from django.db import models
from timescale.db.models.fields import TimescaleDateTimeField
from timescale.db.models.models import TimescaleModel


class AssetPrice(TimescaleModel):
    asset = models.ForeignKey(
        "Asset",
        on_delete=models.CASCADE,
        related_name="prices",
        help_text="Asset this price record belongs to",
    )
    time = TimescaleDateTimeField(
        interval="1 week",
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
        ordering = ["-time"]
        verbose_name = "Asset Price"
        verbose_name_plural = "Asset Prices"
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "time", "source", "interval_minutes"],
                name="unique_asset_time_source_interval",
            ),
        ]
        indexes = [
            models.Index(fields=["asset", "interval_minutes"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        return f"{self.asset.ticker} @ {self.time.strftime('%Y-%m-%d %H:%M')} ({self.source}): ${self.close}"
