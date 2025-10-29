"""
Data validation pipeline for FeeFiFoFunds.

Implements FUND-012: Data Validation Pipeline
Validates data from external sources before storage.
"""

from datetime import date
from decimal import Decimal
from typing import List, Tuple

from .data_sources.dto import FundDataDTO, HoldingDataDTO, PerformanceDataDTO


class ValidationError(Exception):
    """Raised when data validation fails."""

    pass


class DataValidator:
    """
    Validates fund data from external sources.

    Performs sanity checks on prices, volumes, dates, and other fields
    to ensure data quality before storage.
    """

    # Validation thresholds
    MAX_DAILY_PRICE_CHANGE_PERCENT = 50.0  # Max 50% daily change (likely bad data)
    MIN_PRICE = Decimal("0.01")  # Minimum valid price
    MAX_PRICE = Decimal("1000000")  # Maximum valid price
    MAX_EXPENSE_RATIO = Decimal("10.0")  # Max 10% expense ratio
    MIN_VOLUME = 0
    MAX_VOLUME = 10_000_000_000  # 10 billion shares

    def validate_fund_data(self, data: FundDataDTO) -> Tuple[bool, List[str]]:
        """
        Validate fund information data.

        Args:
            data: FundDataDTO to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Required fields
        if not data.ticker or len(data.ticker) == 0:
            errors.append("Ticker is required")
        if not data.name or len(data.name) == 0:
            errors.append("Name is required")

        # Ticker format
        if data.ticker and not data.ticker.replace(".", "").replace("-", "").isalnum():
            errors.append(f"Invalid ticker format: {data.ticker}")

        # Price validation
        if data.current_price is not None:
            if data.current_price < self.MIN_PRICE:
                errors.append(f"Price too low: ${data.current_price}")
            if data.current_price > self.MAX_PRICE:
                errors.append(f"Price unrealistic: ${data.current_price}")

        # Previous close validation
        if data.previous_close is not None and data.current_price is not None:
            if data.previous_close > 0:
                price_change_pct = abs(
                    (float(data.current_price) - float(data.previous_close)) / float(data.previous_close) * 100
                )
                if price_change_pct > self.MAX_DAILY_PRICE_CHANGE_PERCENT:
                    errors.append(f"Unrealistic price change: {price_change_pct:.1f}%")

        # Expense ratio validation
        if data.expense_ratio is not None:
            if data.expense_ratio < 0:
                errors.append(f"Negative expense ratio: {data.expense_ratio}")
            if data.expense_ratio > self.MAX_EXPENSE_RATIO:
                errors.append(f"Expense ratio too high: {data.expense_ratio}%")

        # AUM validation
        if data.aum is not None and data.aum < 0:
            errors.append(f"Negative AUM: {data.aum}")

        # Volume validation
        if data.avg_volume is not None:
            if data.avg_volume < self.MIN_VOLUME:
                errors.append(f"Negative volume: {data.avg_volume}")
            if data.avg_volume > self.MAX_VOLUME:
                errors.append(f"Unrealistic volume: {data.avg_volume}")

        # Date validation
        if data.inception_date is not None:
            if data.inception_date > date.today():
                errors.append(f"Inception date in future: {data.inception_date}")
            if data.inception_date < date(1900, 1, 1):
                errors.append(f"Inception date too old: {data.inception_date}")

        return (len(errors) == 0, errors)

    def validate_performance_data(self, data: PerformanceDataDTO) -> Tuple[bool, List[str]]:
        """
        Validate performance (OHLCV) data.

        Args:
            data: PerformanceDataDTO to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Required fields
        if not data.ticker:
            errors.append("Ticker is required")
        if not data.date:
            errors.append("Date is required")
        if data.close_price is None:
            errors.append("Close price is required")

        # Date validation
        if data.date:
            if data.date > date.today():
                errors.append(f"Date in future: {data.date}")
            if data.date < date(1900, 1, 1):
                errors.append(f"Date too old: {data.date}")

        # Price validation
        if data.close_price is not None:
            if data.close_price < self.MIN_PRICE:
                errors.append(f"Close price too low: ${data.close_price}")
            if data.close_price > self.MAX_PRICE:
                errors.append(f"Close price unrealistic: ${data.close_price}")

        # OHLC consistency
        if all([data.open_price, data.high_price, data.low_price, data.close_price]):
            if data.low_price > data.high_price:
                errors.append(f"Low ({data.low_price}) > High ({data.high_price})")
            if data.open_price < data.low_price or data.open_price > data.high_price:
                errors.append(f"Open ({data.open_price}) outside Low-High range")
            if data.close_price < data.low_price or data.close_price > data.high_price:
                errors.append(f"Close ({data.close_price}) outside Low-High range")

        # Volume validation
        if data.volume is not None:
            if data.volume < 0:
                errors.append(f"Negative volume: {data.volume}")
            if data.volume > self.MAX_VOLUME:
                errors.append(f"Unrealistic volume: {data.volume}")

        # Split ratio validation
        if data.split_ratio is not None:
            if data.split_ratio <= 0:
                errors.append(f"Invalid split ratio: {data.split_ratio}")

        return (len(errors) == 0, errors)

    def validate_holding_data(self, data: HoldingDataDTO) -> Tuple[bool, List[str]]:
        """
        Validate holdings data.

        Args:
            data: HoldingDataDTO to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Required fields
        if not data.ticker:
            errors.append("Ticker is required")
        if not data.name:
            errors.append("Name is required")
        if data.weight is None:
            errors.append("Weight is required")

        # Weight validation (should be 0-100%)
        if data.weight is not None:
            if data.weight < 0:
                errors.append(f"Negative weight: {data.weight}%")
            if data.weight > 100:
                errors.append(f"Weight > 100%: {data.weight}%")

        # Market value validation
        if data.market_value is not None and data.market_value < 0:
            errors.append(f"Negative market value: {data.market_value}")

        # Shares validation
        if data.shares is not None and data.shares < 0:
            errors.append(f"Negative shares: {data.shares}")

        return (len(errors) == 0, errors)

    def validate_batch(self, data_list: List[FundDataDTO | PerformanceDataDTO | HoldingDataDTO]) -> Tuple[List, List]:
        """
        Validate a batch of data objects.

        Args:
            data_list: List of DTO objects to validate

        Returns:
            Tuple of (valid_data_list, invalid_data_with_errors)
        """
        valid_data = []
        invalid_data = []

        for data in data_list:
            if isinstance(data, FundDataDTO):
                is_valid, errors = self.validate_fund_data(data)
            elif isinstance(data, PerformanceDataDTO):
                is_valid, errors = self.validate_performance_data(data)
            elif isinstance(data, HoldingDataDTO):
                is_valid, errors = self.validate_holding_data(data)
            else:
                invalid_data.append((data, ["Unknown data type"]))
                continue

            if is_valid:
                valid_data.append(data)
            else:
                invalid_data.append((data, errors))

        return valid_data, invalid_data

    def calculate_data_quality_score(self, data: PerformanceDataDTO) -> int:
        """
        Calculate a data quality score (0-100).

        Higher scores indicate more complete and reliable data.

        Args:
            data: PerformanceDataDTO to score

        Returns:
            Quality score (0-100)
        """
        score = 100

        # Deduct points for missing optional fields
        if data.open_price is None:
            score -= 10
        if data.high_price is None:
            score -= 10
        if data.low_price is None:
            score -= 10
        if data.adjusted_close is None:
            score -= 10
        if data.volume is None:
            score -= 10

        # Check for OHLC consistency
        if all([data.open_price, data.high_price, data.low_price, data.close_price]):
            if not (data.low_price <= data.open_price <= data.high_price):
                score -= 15
            if not (data.low_price <= data.close_price <= data.high_price):
                score -= 15

        # Bonus for dividends/splits
        if data.dividend and data.dividend > 0:
            score += 5
        if data.split_ratio and data.split_ratio != Decimal("1.0"):
            score += 5

        return max(0, min(100, score))
