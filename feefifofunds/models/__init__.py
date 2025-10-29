"""
Models for FeeFiFoFunds application.

This package contains all database models for the asset tracking and analysis system.
"""

# Import base classes
# Import base asset model
from .asset import Asset
from .base import SoftDeleteModel, TimestampedModel

# Import asset type models
from .commodity import Commodity
from .crypto import Crypto
from .currency import Currency
from .data_source import DataSource, DataSync
from .fund import Fund

# Import holdings model
from .holding import FundHolding
from .inflation import InflationIndex

# Import metrics models
from .metrics import (
    BaseMetrics,
    CommodityMetrics,
    CryptoMetrics,
    CurrencyMetrics,
    FundMetrics,
    InflationMetrics,
    RealEstateMetrics,
    SavingsMetrics,
)

# Import performance models
from .performance import (
    BasePerformance,
    CommodityPerformance,
    CryptoPerformance,
    CurrencyPerformance,
    FundPerformance,
    InflationData,
    PropertyValuation,
    SavingsRateHistory,
)
from .realestate import RealEstate
from .savings import SavingsAccount

# Expose all models at package level
__all__ = [
    # Base classes
    "TimestampedModel",
    "SoftDeleteModel",
    # Base asset model
    "Asset",
    # Asset type models
    "Fund",
    "Crypto",
    "Currency",
    "Commodity",
    "InflationIndex",
    "SavingsAccount",
    "RealEstate",
    # Holdings
    "FundHolding",
    # Performance models
    "BasePerformance",
    "FundPerformance",
    "CryptoPerformance",
    "CurrencyPerformance",
    "CommodityPerformance",
    "InflationData",
    "SavingsRateHistory",
    "PropertyValuation",
    # Metrics models
    "BaseMetrics",
    "FundMetrics",
    "CryptoMetrics",
    "CurrencyMetrics",
    "CommodityMetrics",
    "InflationMetrics",
    "SavingsMetrics",
    "RealEstateMetrics",
    # Data source models
    "DataSource",
    "DataSync",
]
