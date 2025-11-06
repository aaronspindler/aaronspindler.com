from django.db import models


class Trade(models.Model):
    asset = models.ForeignKey(
        "Asset",
        on_delete=models.CASCADE,
        related_name="trades",
        help_text="Asset this trade belongs to",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="Exact time of the trade",
    )
    price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Trade execution price",
    )
    volume = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Trade volume/quantity",
    )
    source = models.CharField(
        max_length=50,
        default="kraken",
        db_index=True,
        help_text="Data source for this trade (e.g., 'kraken')",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Trade"
        verbose_name_plural = "Trades"
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "timestamp", "source"],
                name="unique_trade_asset_timestamp_source",
            ),
        ]
        indexes = [
            models.Index(fields=["asset", "timestamp"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["asset"]),
        ]

    def __str__(self):
        return (
            f"{self.asset.ticker} @ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: ${self.price} (Vol: {self.volume})"
        )
