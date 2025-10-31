"""
RealEstate model - represents real estate properties, REITs, and housing indices.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .asset import Asset


class RealEstate(Asset):
    """
    Represents real estate assets.

    Extends Asset base model with real estate-specific fields.
    Can represent physical properties, REITs, or real estate indices (e.g., Case-Shiller).
    """

    class PropertyType(models.TextChoices):
        """Type of real estate asset."""

        RESIDENTIAL = "RES", "Residential Property"
        COMMERCIAL = "COM", "Commercial Property"
        INDUSTRIAL = "IND", "Industrial Property"
        REIT = "REIT", "Real Estate Investment Trust"
        INDEX = "INDEX", "Real Estate Index"
        LAND = "LAND", "Land"
        MIXED_USE = "MIXED", "Mixed Use"
        OTHER = "OTHER", "Other"

    # Property classification
    property_type = models.CharField(
        max_length=10,
        choices=PropertyType.choices,
        db_index=True,
        help_text="Type of real estate asset",
    )

    # Location
    location_city = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="City or locality",
    )
    location_state = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="State or province",
    )
    location_country = models.CharField(
        max_length=3,
        default="USA",
        db_index=True,
        help_text="Country code (ISO 3166-1 alpha-3)",
    )

    # Physical details (for properties)
    square_footage = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Total square footage",
    )

    # Purchase information (for properties)
    purchase_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of purchase",
    )
    purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Original purchase price",
    )

    # Index indicator
    is_index = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this represents a real estate index (e.g., Case-Shiller, FHFA)",
    )

    class Meta:
        db_table = "feefifofunds_realestate"
        verbose_name = "Real Estate"
        verbose_name_plural = "Real Estate"
        ordering = ["location_country", "location_state", "location_city"]
        indexes = [
            models.Index(fields=["property_type", "location_country"]),
            models.Index(fields=["location_country", "location_state", "location_city"]),
            models.Index(fields=["is_index"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        if self.is_index:
            return f"{self.name} Index"
        location = f"{self.location_city}, {self.location_state}" if self.location_city else self.location_country
        return f"{self.get_property_type_display()} - {location}"

    @property
    def price_per_sqft(self) -> Decimal | None:
        """Calculate current price per square foot."""
        if self.current_value and self.square_footage and self.square_footage > 0:
            return self.current_value / Decimal(str(self.square_footage))
        return None

    @property
    def appreciation_amount(self) -> Decimal | None:
        """Calculate total appreciation since purchase."""
        if self.current_value and self.purchase_price:
            return self.current_value - self.purchase_price
        return None

    @property
    def appreciation_percent(self) -> Decimal | None:
        """Calculate appreciation percentage since purchase."""
        if self.current_value and self.purchase_price and self.purchase_price > 0:
            gain = self.current_value - self.purchase_price
            return (gain / self.purchase_price) * 100
        return None
