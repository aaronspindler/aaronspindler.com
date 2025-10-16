"""
Data Transfer Objects for standardizing fund data from different sources.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class FundDataDTO:
    """
    Standardized data structure for fund information from any source.
    Maps directly to the Fund model fields.
    """

    # Required fields
    ticker: str
    name: str
    fund_type: str  # "MUTUAL_FUND" or "ETF"

    # Provider (can be None if needs to be looked up)
    provider_name: Optional[str] = None

    # Fee Structure
    mer: Optional[Decimal] = None
    front_load: Optional[Decimal] = field(default_factory=lambda: Decimal("0.00"))
    back_load: Optional[Decimal] = field(default_factory=lambda: Decimal("0.00"))
    transaction_fee: Optional[Decimal] = field(default_factory=lambda: Decimal("0.00"))

    # Classification
    asset_class: Optional[str] = None  # EQUITY, BONDS, BALANCED, etc.
    geographic_focus: Optional[str] = None  # CANADIAN, US, INTERNATIONAL, etc.

    # Description
    description: Optional[str] = None

    # Performance (as percentages)
    ytd_return: Optional[Decimal] = None
    one_year_return: Optional[Decimal] = None
    three_year_return: Optional[Decimal] = None
    five_year_return: Optional[Decimal] = None
    ten_year_return: Optional[Decimal] = None

    # Fund Details
    inception_date: Optional[date] = None
    aum: Optional[Decimal] = None  # In millions
    minimum_investment: Optional[Decimal] = None

    # Metadata
    data_source_url: Optional[str] = None
    last_data_update: Optional[date] = None
    is_active: bool = True

    # Source information (for debugging/tracking)
    source_name: Optional[str] = None
    fetch_timestamp: Optional[datetime] = None

    def __post_init__(self):
        """Validate and normalize data after initialization."""
        # Normalize ticker (uppercase, strip whitespace)
        if self.ticker:
            self.ticker = self.ticker.strip().upper()

        # Set default last_data_update to today
        if self.last_data_update is None:
            self.last_data_update = date.today()

        # Set fetch timestamp
        if self.fetch_timestamp is None:
            self.fetch_timestamp = datetime.now()

        # Validate fund_type
        valid_fund_types = ["MUTUAL_FUND", "ETF"]
        if self.fund_type and self.fund_type not in valid_fund_types:
            # Try to normalize common variations
            fund_type_upper = self.fund_type.upper()
            if "ETF" in fund_type_upper or "EXCHANGE" in fund_type_upper:
                self.fund_type = "ETF"
            elif "MUTUAL" in fund_type_upper:
                self.fund_type = "MUTUAL_FUND"
            else:
                raise ValueError(f"Invalid fund_type: {self.fund_type}. Must be one of {valid_fund_types}")

        # Ensure decimals are Decimal type
        decimal_fields = [
            "mer",
            "front_load",
            "back_load",
            "transaction_fee",
            "ytd_return",
            "one_year_return",
            "three_year_return",
            "five_year_return",
            "ten_year_return",
            "aum",
            "minimum_investment",
        ]

        for field_name in decimal_fields:
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, Decimal):
                try:
                    setattr(self, field_name, Decimal(str(value)))
                except (ValueError, TypeError):
                    setattr(self, field_name, None)

    def to_dict(self) -> dict:
        """Convert to dictionary for easier manipulation."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "fund_type": self.fund_type,
            "provider_name": self.provider_name,
            "mer": self.mer,
            "front_load": self.front_load,
            "back_load": self.back_load,
            "transaction_fee": self.transaction_fee,
            "asset_class": self.asset_class,
            "geographic_focus": self.geographic_focus,
            "description": self.description,
            "ytd_return": self.ytd_return,
            "one_year_return": self.one_year_return,
            "three_year_return": self.three_year_return,
            "five_year_return": self.five_year_return,
            "ten_year_return": self.ten_year_return,
            "inception_date": self.inception_date,
            "aum": self.aum,
            "minimum_investment": self.minimum_investment,
            "data_source_url": self.data_source_url,
            "last_data_update": self.last_data_update,
            "is_active": self.is_active,
            "source_name": self.source_name,
            "fetch_timestamp": self.fetch_timestamp,
        }

    def is_complete(self) -> bool:
        """Check if we have the minimum required data to create a Fund record."""
        required = [self.ticker, self.name, self.fund_type]
        return all(required) and self.mer is not None

    def merge_with(self, other: "FundDataDTO", prefer_other: bool = False) -> "FundDataDTO":
        """
        Merge this DTO with another, filling in missing fields.

        Args:
            other: Another FundDataDTO to merge with
            prefer_other: If True, prefer other's values when both have data

        Returns:
            New FundDataDTO with merged data
        """
        if prefer_other:
            primary, secondary = other, self
        else:
            primary, secondary = self, other

        merged_data = {}
        for key in self.__dataclass_fields__.keys():
            primary_value = getattr(primary, key)
            secondary_value = getattr(secondary, key)

            # Use primary if it has a value, otherwise use secondary
            if primary_value is not None:
                merged_data[key] = primary_value
            else:
                merged_data[key] = secondary_value

        return FundDataDTO(**merged_data)

    def __repr__(self):
        return f"FundDataDTO(ticker={self.ticker}, name={self.name}, mer={self.mer}, source={self.source_name})"
