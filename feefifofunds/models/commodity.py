"""
Commodity model - represents commodities like gold, oil, wheat, etc.
"""

from django.db import models

from .asset import Asset


class Commodity(Asset):
    """
    Represents a commodity.

    Extends Asset base model with commodity-specific fields.
    Examples: Gold, Crude Oil, Natural Gas, Wheat, Corn, Copper, etc.
    """

    class CommodityType(models.TextChoices):
        """Type of commodity."""

        ENERGY = "ENERGY", "Energy (Oil, Gas, etc.)"
        PRECIOUS_METALS = "PRECIOUS", "Precious Metals (Gold, Silver, etc.)"
        INDUSTRIAL_METALS = "INDUSTRIAL", "Industrial Metals (Copper, Aluminum, etc.)"
        AGRICULTURE = "AGRICULTURE", "Agriculture (Wheat, Corn, etc.)"
        LIVESTOCK = "LIVESTOCK", "Livestock (Cattle, Hogs, etc.)"
        SOFT = "SOFT", "Soft Commodities (Coffee, Cotton, Sugar, etc.)"
        OTHER = "OTHER", "Other"

    class UnitOfMeasure(models.TextChoices):
        """Unit of measure for pricing."""

        BARREL = "BBL", "Barrel"
        TROY_OUNCE = "OZ_T", "Troy Ounce"
        METRIC_TON = "MT", "Metric Ton"
        BUSHEL = "BU", "Bushel"
        POUND = "LB", "Pound"
        GALLON = "GAL", "Gallon"
        MMBTU = "MMBTU", "Million BTU"
        OTHER = "OTHER", "Other"

    # Commodity classification
    commodity_type = models.CharField(
        max_length=12,
        choices=CommodityType.choices,
        db_index=True,
        help_text="Type of commodity",
    )

    # Trading details
    unit_of_measure = models.CharField(
        max_length=10,
        choices=UnitOfMeasure.choices,
        help_text="Unit of measure for pricing",
    )
    trading_exchange = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Primary trading exchange (e.g., NYMEX, COMEX, CBOT)",
    )
    contract_symbol = models.CharField(
        max_length=20,
        blank=True,
        help_text="Futures contract symbol",
    )

    # Contract details (for futures)
    contract_month = models.CharField(
        max_length=10,
        blank=True,
        help_text="Contract month for futures (e.g., 'Dec 2025', 'Z25')",
    )
    contract_size = models.CharField(
        max_length=100,
        blank=True,
        help_text="Standard contract size (e.g., '1,000 barrels', '100 troy oz')",
    )

    # Quality specifications
    grade = models.CharField(
        max_length=100,
        blank=True,
        help_text="Grade or quality specification (e.g., 'WTI', 'Brent', '.999 fine')",
    )

    # Spot vs Futures indicator
    is_spot_price = models.BooleanField(
        default=True,
        help_text="True if tracking spot price, False if tracking futures",
    )

    class Meta:
        db_table = "feefifofunds_commodity"
        verbose_name = "Commodity"
        verbose_name_plural = "Commodities"
        ordering = ["commodity_type", "ticker"]
        indexes = [
            models.Index(fields=["commodity_type", "trading_exchange"]),
            models.Index(fields=["trading_exchange"]),
            models.Index(fields=["is_spot_price"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        price_type = "Spot" if self.is_spot_price else "Futures"
        if self.contract_month:
            return f"{self.name} {price_type} - {self.contract_month}"
        return f"{self.name} {price_type}"

    @property
    def is_precious_metal(self) -> bool:
        """Check if this is a precious metal."""
        return self.commodity_type == self.CommodityType.PRECIOUS_METALS

    @property
    def is_energy(self) -> bool:
        """Check if this is an energy commodity."""
        return self.commodity_type == self.CommodityType.ENERGY
