"""
Models for FeeFiFoFunds application.

This package contains all database models for the fund tracking and analysis system.
"""

# Import base classes
from .base import SoftDeleteModel, TimestampedModel
from .data_source import DataSource, DataSync

# Import core models
from .fund import Fund
from .holding import FundHolding
from .metrics import FundMetrics
from .performance import FundPerformance

# Expose all models at package level
__all__ = [
    # Base classes
    "TimestampedModel",
    "SoftDeleteModel",
    # Core models
    "Fund",
    "FundPerformance",
    "FundHolding",
    "FundMetrics",
    # Data source models
    "DataSource",
    "DataSync",
]
