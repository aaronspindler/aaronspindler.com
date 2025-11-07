from django.db import models
from timescale.db.models.fields import TimescaleDateTimeField
from timescale.db.models.models import TimescaleModel


class Trade(TimescaleModel):
    asset = models.ForeignKey(
        "Asset",
        on_delete=models.CASCADE,
        related_name="trades",
        help_text="Asset this trade belongs to",
    )
    time = TimescaleDateTimeField(
        interval="1 day",
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
    quote_currency = models.CharField(
        max_length=10,
        default="USD",
        db_index=True,
        help_text="Currency in which the price is quoted (USD, EUR, BTC, etc.)",
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
        ordering = ["-time"]
        verbose_name = "Trade"
        verbose_name_plural = "Trades"
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "time", "source", "quote_currency"],
                name="unique_trade_asset_time_source_currency",
            ),
        ]
        indexes = [
            models.Index(fields=["asset"]),
        ]

    def __str__(self):
        return f"{self.asset.ticker} @ {self.time.strftime('%Y-%m-%d %H:%M:%S')}: ${self.price} (Vol: {self.volume})"
