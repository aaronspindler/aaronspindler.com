"""
InflationIndex model - represents inflation indices like CPI, PPI, etc.
"""

from django.db import models

from .asset import Asset


class InflationIndex(Asset):
    """
    Represents an inflation index.

    Extends Asset base model with inflation index-specific fields.
    Examples: CPI, PPI, PCE, GDP Deflator
    """

    class IndexType(models.TextChoices):
        """Type of inflation index."""

        CPI = "CPI", "Consumer Price Index"
        CORE_CPI = "CORE_CPI", "Core CPI (excl. food & energy)"
        PPI = "PPI", "Producer Price Index"
        PCE = "PCE", "Personal Consumption Expenditures"
        CORE_PCE = "CORE_PCE", "Core PCE"
        GDP_DEFLATOR = "GDP_DEF", "GDP Deflator"
        IMPORT_PRICE = "IMP", "Import Price Index"
        EXPORT_PRICE = "EXP", "Export Price Index"
        OTHER = "OTHER", "Other"

    class Frequency(models.TextChoices):
        """Reporting frequency."""

        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        ANNUAL = "ANNUAL", "Annual"

    # Index classification
    index_type = models.CharField(
        max_length=10,
        choices=IndexType.choices,
        db_index=True,
        help_text="Type of inflation index",
    )

    # Index details
    base_year = models.IntegerField(
        help_text="Base year for index calculation (e.g., 1982, 2015)",
    )
    geographic_region = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Geographic region (e.g., US, EU, UK, Global)",
    )
    frequency = models.CharField(
        max_length=10,
        choices=Frequency.choices,
        default=Frequency.MONTHLY,
        help_text="Reporting frequency",
    )

    # Seasonal adjustment
    seasonal_adjustment = models.BooleanField(
        default=True,
        help_text="Whether index is seasonally adjusted",
    )

    class Meta:
        db_table = "feefifofunds_inflation"
        verbose_name = "Inflation Index"
        verbose_name_plural = "Inflation Indices"
        ordering = ["geographic_region", "index_type"]
        indexes = [
            models.Index(fields=["index_type", "geographic_region"]),
            models.Index(fields=["geographic_region", "frequency"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.get_index_type_display()} - {self.geographic_region}"
