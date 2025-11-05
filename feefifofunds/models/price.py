from django.db import models


class AssetPrice(models.Model):
    asset = models.ForeignKey(
        "Asset",
        on_delete=models.CASCADE,
        related_name="prices",
        help_text="Asset this price record belongs to",
    )
    timestamp = models.DateTimeField(
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
    source = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Data source for this price record (e.g., 'finnhub', 'massive', 'yahoo')",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Asset Price"
        verbose_name_plural = "Asset Prices"
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "timestamp", "source"],
                name="unique_asset_timestamp_source",
            ),
        ]
        indexes = [
            models.Index(fields=["asset", "timestamp", "source"]),
            models.Index(fields=["asset", "source"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        return f"{self.asset.ticker} @ {self.timestamp.strftime('%Y-%m-%d %H:%M')} ({self.source}): ${self.close}"
