from django.db import models


class Trade(models.Model):
    asset_id = models.IntegerField(
        db_index=True,
        help_text="ID of the asset this trade belongs to",
    )
    time = models.DateTimeField(
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

    class Meta:
        managed = False
        db_table = "trade"
        ordering = ["-time"]
        verbose_name = "Trade"
        verbose_name_plural = "Trades"

    @property
    def asset(self):
        """Lazy load asset from PostgreSQL (default database)."""
        if not hasattr(self, "_asset"):
            from .asset import Asset

            self._asset = Asset.objects.get(id=self.asset_id)
        return self._asset

    def __str__(self):
        return f"Asset {self.asset_id} @ {self.time.strftime('%Y-%m-%d %H:%M:%S')}: ${self.price} (Vol: {self.volume})"
