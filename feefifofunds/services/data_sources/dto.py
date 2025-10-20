"""
Data Transfer Objects (DTOs) for fund data.

Provides standardized data structures for transferring data between
external APIs and the database models.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class FundDataDTO:
    """
    Data Transfer Object for fund information.

    Standardizes fund data from various sources into a common format
    that can be easily converted to the Fund model.
    """

    # Required fields
    ticker: str
    name: str

    # Fund classification
    fund_type: Optional[str] = None  # ETF, MUTUAL, INDEX, BOND, MM, TARGET, OTHER
    asset_class: Optional[str] = None  # EQUITY, BOND, MIXED, MM, COMMODITY, REIT, ALT
    category: Optional[str] = None

    # Fund details
    description: Optional[str] = None
    inception_date: Optional[date] = None
    issuer: Optional[str] = None

    # Costs and fees
    expense_ratio: Optional[Decimal] = None
    management_fee: Optional[Decimal] = None
    front_load: Optional[Decimal] = None
    back_load: Optional[Decimal] = None

    # Current state
    current_price: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    currency: str = "USD"

    # Fund size
    aum: Optional[Decimal] = None  # Assets Under Management in millions
    avg_volume: Optional[int] = None

    # Metadata
    exchange: Optional[str] = None
    website: Optional[str] = None
    isin: Optional[str] = None
    cusip: Optional[str] = None

    # Data source
    source: str = "unknown"
    fetched_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate data after initialization."""
        if not self.ticker:
            raise ValueError("Ticker is required")
        if not self.name:
            raise ValueError("Name is required")

        # Convert strings to Decimals if needed
        if isinstance(self.expense_ratio, (int, float)):
            self.expense_ratio = Decimal(str(self.expense_ratio))
        if isinstance(self.current_price, (int, float)):
            self.current_price = Decimal(str(self.current_price))
        if isinstance(self.previous_close, (int, float)):
            self.previous_close = Decimal(str(self.previous_close))
        if isinstance(self.aum, (int, float)):
            self.aum = Decimal(str(self.aum))


@dataclass
class PerformanceDataDTO:
    """
    Data Transfer Object for fund performance (OHLCV) data.

    Standardizes price and volume data from various sources.
    """

    # Required fields
    ticker: str
    date: date
    close_price: Decimal

    # OHLCV data
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    adjusted_close: Optional[Decimal] = None
    volume: Optional[int] = None

    # Distributions
    dividend: Optional[Decimal] = None
    split_ratio: Optional[Decimal] = None

    # Metadata
    interval: str = "1D"  # 1D, 1W, 1M, 1Q, 1Y
    source: str = "unknown"
    fetched_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate and convert data types."""
        if not self.ticker:
            raise ValueError("Ticker is required")
        if not self.date:
            raise ValueError("Date is required")
        if not self.close_price:
            raise ValueError("Close price is required")

        # Convert to Decimal if needed
        if isinstance(self.close_price, (int, float)):
            self.close_price = Decimal(str(self.close_price))
        if self.open_price and isinstance(self.open_price, (int, float)):
            self.open_price = Decimal(str(self.open_price))
        if self.high_price and isinstance(self.high_price, (int, float)):
            self.high_price = Decimal(str(self.high_price))
        if self.low_price and isinstance(self.low_price, (int, float)):
            self.low_price = Decimal(str(self.low_price))
        if self.adjusted_close and isinstance(self.adjusted_close, (int, float)):
            self.adjusted_close = Decimal(str(self.adjusted_close))


@dataclass
class HoldingDataDTO:
    """
    Data Transfer Object for fund holdings data.

    Standardizes holdings data from various sources.
    """

    # Required fields
    ticker: str  # Holding ticker
    name: str
    weight: Decimal  # Portfolio weight as percentage

    # Position details
    shares: Optional[Decimal] = None
    market_value: Optional[Decimal] = None

    # Classification
    holding_type: str = "EQUITY"  # EQUITY, BOND, CASH, OPTION, FUTURE, COMMODITY, REIT, OTHER
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None

    # Identifiers
    cusip: Optional[str] = None
    isin: Optional[str] = None

    # Metadata
    as_of_date: Optional[date] = None
    source: str = "unknown"
    fetched_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate and convert data types."""
        if not self.ticker:
            raise ValueError("Ticker is required")
        if not self.name:
            raise ValueError("Name is required")
        if not self.weight:
            raise ValueError("Weight is required")

        # Convert to Decimal if needed
        if isinstance(self.weight, (int, float)):
            self.weight = Decimal(str(self.weight))
        if self.shares and isinstance(self.shares, (int, float)):
            self.shares = Decimal(str(self.shares))
        if self.market_value and isinstance(self.market_value, (int, float)):
            self.market_value = Decimal(str(self.market_value))
