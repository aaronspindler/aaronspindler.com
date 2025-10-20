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
        """Validate and normalize data after initialization."""
        if not self.ticker:
            raise ValueError("Ticker is required")
        if not self.name:
            raise ValueError("Name is required")

        # Convert and enforce precision for expense_ratio (max 4 decimal places)
        if isinstance(self.expense_ratio, (int, float)):
            self.expense_ratio = Decimal(str(self.expense_ratio))
        if self.expense_ratio and self.expense_ratio.as_tuple().exponent < -4:
            self.expense_ratio = round(self.expense_ratio, 4)

        # Convert and enforce precision for management_fee (max 4 decimal places)
        if isinstance(self.management_fee, (int, float)):
            self.management_fee = Decimal(str(self.management_fee))
        if self.management_fee and self.management_fee.as_tuple().exponent < -4:
            self.management_fee = round(self.management_fee, 4)

        # Convert and enforce precision for front_load (max 4 decimal places)
        if isinstance(self.front_load, (int, float)):
            self.front_load = Decimal(str(self.front_load))
        if self.front_load and self.front_load.as_tuple().exponent < -4:
            self.front_load = round(self.front_load, 4)

        # Convert and enforce precision for back_load (max 4 decimal places)
        if isinstance(self.back_load, (int, float)):
            self.back_load = Decimal(str(self.back_load))
        if self.back_load and self.back_load.as_tuple().exponent < -4:
            self.back_load = round(self.back_load, 4)

        # Convert and enforce precision for current_price (max 4 decimal places)
        if isinstance(self.current_price, (int, float)):
            self.current_price = Decimal(str(self.current_price))
        if self.current_price and self.current_price.as_tuple().exponent < -4:
            self.current_price = round(self.current_price, 4)

        # Convert and enforce precision for previous_close (max 4 decimal places)
        if isinstance(self.previous_close, (int, float)):
            self.previous_close = Decimal(str(self.previous_close))
        if self.previous_close and self.previous_close.as_tuple().exponent < -4:
            self.previous_close = round(self.previous_close, 4)

        # Convert and enforce precision for aum (max 2 decimal places for millions)
        if isinstance(self.aum, (int, float)):
            self.aum = Decimal(str(self.aum))
        if self.aum and self.aum.as_tuple().exponent < -2:
            self.aum = round(self.aum, 2)


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
        """Validate and normalize data types."""
        if not self.ticker:
            raise ValueError("Ticker is required")
        if not self.date:
            raise ValueError("Date is required")
        if not self.close_price:
            raise ValueError("Close price is required")

        # Convert and enforce precision for close_price (max 4 decimal places)
        if isinstance(self.close_price, (int, float)):
            self.close_price = Decimal(str(self.close_price))
        if self.close_price and self.close_price.as_tuple().exponent < -4:
            self.close_price = round(self.close_price, 4)

        # Convert and enforce precision for open_price (max 4 decimal places)
        if self.open_price and isinstance(self.open_price, (int, float)):
            self.open_price = Decimal(str(self.open_price))
        if self.open_price and self.open_price.as_tuple().exponent < -4:
            self.open_price = round(self.open_price, 4)

        # Convert and enforce precision for high_price (max 4 decimal places)
        if self.high_price and isinstance(self.high_price, (int, float)):
            self.high_price = Decimal(str(self.high_price))
        if self.high_price and self.high_price.as_tuple().exponent < -4:
            self.high_price = round(self.high_price, 4)

        # Convert and enforce precision for low_price (max 4 decimal places)
        if self.low_price and isinstance(self.low_price, (int, float)):
            self.low_price = Decimal(str(self.low_price))
        if self.low_price and self.low_price.as_tuple().exponent < -4:
            self.low_price = round(self.low_price, 4)

        # Convert and enforce precision for adjusted_close (max 4 decimal places)
        if self.adjusted_close and isinstance(self.adjusted_close, (int, float)):
            self.adjusted_close = Decimal(str(self.adjusted_close))
        if self.adjusted_close and self.adjusted_close.as_tuple().exponent < -4:
            self.adjusted_close = round(self.adjusted_close, 4)

        # Convert and enforce precision for dividend (max 4 decimal places)
        if self.dividend and isinstance(self.dividend, (int, float)):
            self.dividend = Decimal(str(self.dividend))
        if self.dividend and self.dividend.as_tuple().exponent < -4:
            self.dividend = round(self.dividend, 4)

        # Convert and enforce precision for split_ratio (max 4 decimal places)
        if self.split_ratio and isinstance(self.split_ratio, (int, float)):
            self.split_ratio = Decimal(str(self.split_ratio))
        if self.split_ratio and self.split_ratio.as_tuple().exponent < -4:
            self.split_ratio = round(self.split_ratio, 4)


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
        """Validate and normalize data types."""
        if not self.ticker:
            raise ValueError("Ticker is required")
        if not self.name:
            raise ValueError("Name is required")
        if not self.weight:
            raise ValueError("Weight is required")

        # Convert and enforce precision for weight (max 4 decimal places)
        if isinstance(self.weight, (int, float)):
            self.weight = Decimal(str(self.weight))
        if self.weight and self.weight.as_tuple().exponent < -4:
            self.weight = round(self.weight, 4)

        # Convert and enforce precision for shares (max 4 decimal places)
        if self.shares and isinstance(self.shares, (int, float)):
            self.shares = Decimal(str(self.shares))
        if self.shares and self.shares.as_tuple().exponent < -4:
            self.shares = round(self.shares, 4)

        # Convert and enforce precision for market_value (max 2 decimal places)
        if self.market_value and isinstance(self.market_value, (int, float)):
            self.market_value = Decimal(str(self.market_value))
        if self.market_value and self.market_value.as_tuple().exponent < -2:
            self.market_value = round(self.market_value, 2)
