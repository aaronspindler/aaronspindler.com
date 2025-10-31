"""
Metrics Calculator - Calculates financial metrics and analytics.

Implements FUND-017: Calculate Basic Financial Metrics
"""

import math
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

import numpy as np

from feefifofunds.models import FundMetrics, FundPerformance


class MetricsCalculator:
    """
    Calculates financial metrics for funds.

    Provides methods for calculating returns, volatility, moving averages,
    and other fundamental metrics from price data.
    """

    def __init__(self, fund):
        """
        Initialize calculator for a specific fund.

        Args:
            fund: Fund instance
        """
        self.fund = fund

    def calculate_returns(
        self, time_frame: str = "1Y", end_date: Optional[date] = None
    ) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """
        Calculate returns for a given time frame.

        Args:
            time_frame: Time frame (1M, 3M, 6M, YTD, 1Y, 3Y, 5Y, 10Y, ALL)
            end_date: End date for calculation (defaults to today)

        Returns:
            Tuple of (total_return, annualized_return, cumulative_return) as percentages
        """
        if not end_date:
            end_date = date.today()

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None, None, None

        # Get price data
        prices = FundPerformance.objects.filter(
            fund=self.fund, date__gte=start_date, date__lte=end_date, interval="1D", is_active=True
        ).order_by("date")

        if prices.count() < 2:
            return None, None, None

        first_price = prices.first().close_price
        last_price = prices.last().close_price

        if not first_price or not last_price or first_price <= 0:
            return None, None, None

        # Calculate returns
        total_return = ((last_price - first_price) / first_price) * 100
        cumulative_return = total_return  # Same for simple returns

        # Calculate annualized return
        days = (end_date - start_date).days
        if days > 0:
            years = Decimal(str(days / 365.25))
            if years > 0:
                annual_factor = Decimal("1") / years
                annualized_return = ((Decimal("1") + total_return / 100) ** annual_factor - 1) * 100
            else:
                annualized_return = total_return
        else:
            annualized_return = total_return

        return total_return, annualized_return, cumulative_return

    def calculate_volatility(
        self, time_frame: str = "1Y", end_date: Optional[date] = None, annualized: bool = True
    ) -> Optional[Decimal]:
        """
        Calculate volatility (standard deviation of returns).

        Args:
            time_frame: Time frame for calculation
            end_date: End date (defaults to today)
            annualized: Whether to annualize the volatility

        Returns:
            Volatility as a percentage or None
        """
        if not end_date:
            end_date = date.today()

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None

        # Get daily returns
        returns = self._get_daily_returns(start_date, end_date)
        if len(returns) < 2:
            return None

        # Calculate standard deviation
        std_dev = float(np.std(returns, ddof=1))  # Use sample std dev

        if annualized:
            # Annualize using sqrt(252) for trading days
            std_dev = std_dev * math.sqrt(252)

        return Decimal(str(std_dev * 100))  # Convert to percentage

    def calculate_moving_average(
        self, days: int, end_date: Optional[date] = None, exponential: bool = False
    ) -> Optional[Decimal]:
        """
        Calculate moving average.

        Args:
            days: Number of days for moving average (e.g., 50, 200)
            end_date: End date (defaults to today)
            exponential: Whether to use exponential moving average

        Returns:
            Moving average price or None
        """
        if not end_date:
            end_date = date.today()

        start_date = end_date - timedelta(days=days + 10)  # Extra buffer

        prices_qs = FundPerformance.objects.filter(
            fund=self.fund, date__gte=start_date, date__lte=end_date, interval="1D", is_active=True
        ).order_by("date")

        if prices_qs.count() < days:
            return None

        prices = [float(p.close_price) for p in prices_qs.values_list("close_price", flat=True)]

        if exponential:
            # EMA calculation
            ema = self._calculate_ema(prices, days)
            return Decimal(str(ema)) if ema else None
        else:
            # SMA calculation
            recent_prices = prices[-days:]
            sma = sum(recent_prices) / len(recent_prices)
            return Decimal(str(sma))

    def calculate_all_metrics(self, time_frame: str = "1Y", end_date: Optional[date] = None) -> Optional[FundMetrics]:
        """
        Calculate all basic metrics for a time frame and save to database.

        Args:
            time_frame: Time frame for calculations
            end_date: End date (defaults to today)

        Returns:
            FundMetrics instance or None
        """
        if not end_date:
            end_date = date.today()

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None

        # Get data points count
        data_points = FundPerformance.objects.filter(
            fund=self.fund, date__gte=start_date, date__lte=end_date, interval="1D", is_active=True
        ).count()

        if data_points < 2:
            return None

        # Calculate returns
        total_return, annualized_return, cumulative_return = self.calculate_returns(time_frame, end_date)

        # Calculate volatility
        volatility = self.calculate_volatility(time_frame, end_date, annualized=True)

        # Create metrics record
        metrics = FundMetrics.objects.create(
            fund=self.fund,
            calculation_date=end_date,
            time_frame=time_frame,
            data_points=data_points,
            total_return=total_return,
            annualized_return=annualized_return,
            cumulative_return=cumulative_return,
            volatility=volatility,
            calculation_engine_version="1.0.0",
        )

        return metrics

    # Helper methods

    def _get_start_date_for_timeframe(self, time_frame: str, end_date: date) -> Optional[date]:
        """
        Get start date for a given time frame.

        Args:
            time_frame: Time frame code (1M, 3M, 6M, YTD, 1Y, 3Y, 5Y, 10Y, ALL)
            end_date: End date

        Returns:
            Start date or None
        """
        timeframe_map = {
            "1M": timedelta(days=30),
            "3M": timedelta(days=90),
            "6M": timedelta(days=180),
            "1Y": timedelta(days=365),
            "3Y": timedelta(days=365 * 3),
            "5Y": timedelta(days=365 * 5),
            "10Y": timedelta(days=365 * 10),
        }

        if time_frame == "YTD":
            return date(end_date.year, 1, 1)
        elif time_frame == "ALL":
            # Get earliest data point
            earliest = (
                FundPerformance.objects.filter(fund=self.fund, is_active=True)
                .order_by("date")
                .values_list("date", flat=True)
                .first()
            )
            return earliest
        elif time_frame in timeframe_map:
            return end_date - timeframe_map[time_frame]
        else:
            return None

    def _get_daily_returns(self, start_date: date, end_date: date) -> List[float]:
        """
        Get daily returns for a date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of daily returns as floats
        """
        prices_qs = FundPerformance.objects.filter(
            fund=self.fund, date__gte=start_date, date__lte=end_date, interval="1D", is_active=True
        ).order_by("date")

        prices = [float(p.close_price) for p in prices_qs]

        if len(prices) < 2:
            return []

        # Calculate daily returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                daily_return = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(daily_return)

        return returns

    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Exponential Moving Average.

        Args:
            prices: List of prices
            period: EMA period

        Returns:
            EMA value or None
        """
        if len(prices) < period:
            return None

        # Calculate multiplier
        multiplier = 2 / (period + 1)

        # Start with SMA
        ema = sum(prices[:period]) / period

        # Calculate EMA for remaining prices
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema
