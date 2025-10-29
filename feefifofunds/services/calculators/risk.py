"""
Risk Metrics Calculator - Calculates advanced risk metrics.

Implements FUND-018: Implement Risk Metrics Calculations
"""

import math
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

import numpy as np

from feefifofunds.models import FundMetrics, FundPerformance

from .metrics import MetricsCalculator


class RiskCalculator(MetricsCalculator):
    """
    Calculates risk metrics for funds.

    Extends MetricsCalculator with advanced risk metrics:
    - Sharpe ratio, Sortino ratio, Treynor ratio
    - Beta, Alpha, R-squared
    - Maximum drawdown
    - Value at Risk (VaR), Conditional VaR (CVaR)
    """

    def __init__(self, fund, benchmark_ticker: str = "SPY"):
        """
        Initialize risk calculator.

        Args:
            fund: Fund instance
            benchmark_ticker: Benchmark ticker for comparison (default: SPY)
        """
        super().__init__(fund)
        self.benchmark_ticker = benchmark_ticker
        self.risk_free_rate = Decimal("0.04")  # 4% annual risk-free rate (configurable)

    def calculate_sharpe_ratio(self, time_frame: str = "1Y", end_date: Optional[date] = None) -> Optional[Decimal]:
        """
        Calculate Sharpe ratio (risk-adjusted return).

        Sharpe = (Return - RiskFreeRate) / Volatility

        Args:
            time_frame: Time frame for calculation
            end_date: End date (defaults to today)

        Returns:
            Sharpe ratio or None
        """
        if not end_date:
            end_date = date.today()

        # Get return and volatility
        total_return, annualized_return, _ = self.calculate_returns(time_frame, end_date)
        volatility = self.calculate_volatility(time_frame, end_date, annualized=True)

        if annualized_return is None or volatility is None or volatility == 0:
            return None

        # Sharpe ratio
        excess_return = annualized_return - self.risk_free_rate
        sharpe = excess_return / volatility

        return sharpe

    def calculate_sortino_ratio(self, time_frame: str = "1Y", end_date: Optional[date] = None) -> Optional[Decimal]:
        """
        Calculate Sortino ratio (downside risk-adjusted return).

        Sortino = (Return - RiskFreeRate) / DownsideDeviation

        Args:
            time_frame: Time frame for calculation
            end_date: End date (defaults to today)

        Returns:
            Sortino ratio or None
        """
        if not end_date:
            end_date = date.today()

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None

        # Get returns
        _, annualized_return, _ = self.calculate_returns(time_frame, end_date)
        if annualized_return is None:
            return None

        # Calculate downside deviation
        downside_dev = self._calculate_downside_deviation(start_date, end_date)
        if downside_dev is None or downside_dev == 0:
            return None

        # Sortino ratio
        excess_return = annualized_return - self.risk_free_rate
        sortino = excess_return / downside_dev

        return sortino

    def calculate_beta(self, time_frame: str = "1Y", end_date: Optional[date] = None) -> Optional[Decimal]:
        """
        Calculate beta (systematic risk relative to benchmark).

        Beta = Covariance(Fund, Benchmark) / Variance(Benchmark)

        Args:
            time_frame: Time frame for calculation
            end_date: End date (defaults to today)

        Returns:
            Beta value or None
        """
        if not end_date:
            end_date = date.today()

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None

        # Get fund returns
        fund_returns = self._get_daily_returns(start_date, end_date)
        if len(fund_returns) < 30:  # Need minimum data
            return None

        # Get benchmark returns
        benchmark_returns = self._get_benchmark_returns(start_date, end_date)
        if len(benchmark_returns) < 30 or len(benchmark_returns) != len(fund_returns):
            return None

        # Calculate covariance and variance
        covariance = np.cov(fund_returns, benchmark_returns)[0][1]
        benchmark_variance = np.var(benchmark_returns, ddof=1)

        if benchmark_variance == 0:
            return None

        beta = covariance / benchmark_variance

        return Decimal(str(beta))

    def calculate_alpha(self, time_frame: str = "1Y", end_date: Optional[date] = None) -> Optional[Decimal]:
        """
        Calculate alpha (excess return over benchmark).

        Alpha = FundReturn - (RiskFreeRate + Beta * (BenchmarkReturn - RiskFreeRate))

        Args:
            time_frame: Time frame for calculation
            end_date: End date (defaults to today)

        Returns:
            Alpha as a percentage or None
        """
        if not end_date:
            end_date = date.today()

        # Get fund return
        _, fund_return, _ = self.calculate_returns(time_frame, end_date)
        if fund_return is None:
            return None

        # Get beta
        beta = self.calculate_beta(time_frame, end_date)
        if beta is None:
            return None

        # Get benchmark return
        benchmark_return = self._get_benchmark_return(time_frame, end_date)
        if benchmark_return is None:
            return None

        # Calculate alpha
        expected_return = self.risk_free_rate + beta * (benchmark_return - self.risk_free_rate)
        alpha = fund_return - expected_return

        return alpha

    def calculate_r_squared(self, time_frame: str = "1Y", end_date: Optional[date] = None) -> Optional[Decimal]:
        """
        Calculate R-squared (correlation to benchmark).

        R² = 1 - (SSres / SStot)

        Args:
            time_frame: Time frame for calculation
            end_date: End date (defaults to today)

        Returns:
            R-squared value (0-1) or None
        """
        if not end_date:
            end_date = date.today()

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None

        # Get returns
        fund_returns = self._get_daily_returns(start_date, end_date)
        benchmark_returns = self._get_benchmark_returns(start_date, end_date)

        if len(fund_returns) < 30 or len(benchmark_returns) != len(fund_returns):
            return None

        # Calculate correlation coefficient and square it
        correlation = np.corrcoef(fund_returns, benchmark_returns)[0][1]
        r_squared = correlation**2

        return Decimal(str(r_squared))

    def calculate_max_drawdown(
        self, time_frame: str = "1Y", end_date: Optional[date] = None
    ) -> Tuple[Optional[Decimal], Optional[int], Optional[Decimal]]:
        """
        Calculate maximum drawdown metrics.

        Args:
            time_frame: Time frame for calculation
            end_date: End date (defaults to today)

        Returns:
            Tuple of (max_drawdown %, duration in days, current_drawdown %)
        """
        if not end_date:
            end_date = date.today()

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None, None, None

        # Get prices
        prices_qs = FundPerformance.objects.filter(
            fund=self.fund, date__gte=start_date, date__lte=end_date, interval="1D", is_active=True
        ).order_by("date")

        if prices_qs.count() < 2:
            return None, None, None

        prices = [float(p.close_price) for p in prices_qs]
        dates = [p.date for p in prices_qs]

        # Calculate cumulative returns
        cumulative = [prices[0]]
        for i in range(1, len(prices)):
            cumulative.append(max(cumulative[-1], prices[i]))

        # Calculate drawdowns
        drawdowns = []
        for i in range(len(prices)):
            if cumulative[i] > 0:
                dd = ((prices[i] - cumulative[i]) / cumulative[i]) * 100
                drawdowns.append(dd)
            else:
                drawdowns.append(0)

        # Find maximum drawdown
        max_dd = min(drawdowns) if drawdowns else 0
        max_dd_idx = drawdowns.index(max_dd) if drawdowns else 0

        # Calculate duration (find when peak was reached before max DD)
        peak_idx = max_dd_idx
        for i in range(max_dd_idx, -1, -1):
            if prices[i] == cumulative[max_dd_idx]:
                peak_idx = i
                break

        duration = (dates[max_dd_idx] - dates[peak_idx]).days if peak_idx != max_dd_idx else 0

        # Current drawdown
        current_dd = drawdowns[-1] if drawdowns else 0

        return Decimal(str(max_dd)), duration, Decimal(str(current_dd))

    def calculate_value_at_risk(
        self, time_frame: str = "1Y", end_date: Optional[date] = None, confidence: float = 0.95
    ) -> Optional[Decimal]:
        """
        Calculate Value at Risk (VaR) using historical simulation.

        VaR represents the maximum expected loss at a given confidence level.

        Args:
            time_frame: Time frame for calculation
            end_date: End date (defaults to today)
            confidence: Confidence level (0.95 for 95%, 0.99 for 99%)

        Returns:
            VaR as a percentage or None
        """
        if not end_date:
            end_date = date.today()

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None

        # Get daily returns
        returns = self._get_daily_returns(start_date, end_date)
        if len(returns) < 30:
            return None

        # Calculate VaR using historical simulation (percentile method)
        var = np.percentile(returns, (1 - confidence) * 100)

        return Decimal(str(var * 100))  # Convert to percentage

    def calculate_conditional_var(
        self, time_frame: str = "1Y", end_date: Optional[date] = None, confidence: float = 0.95
    ) -> Optional[Decimal]:
        """
        Calculate Conditional VaR (CVaR), also known as Expected Shortfall.

        CVaR is the average loss beyond the VaR threshold.

        Args:
            time_frame: Time frame for calculation
            end_date: End date (defaults to today)
            confidence: Confidence level

        Returns:
            CVaR as a percentage or None
        """
        if not end_date:
            end_date = date.today()

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None

        # Get daily returns
        returns = self._get_daily_returns(start_date, end_date)
        if len(returns) < 30:
            return None

        # Calculate VaR threshold
        var_threshold = np.percentile(returns, (1 - confidence) * 100)

        # Calculate average of returns below VaR
        tail_returns = [r for r in returns if r <= var_threshold]
        if not tail_returns:
            return None

        cvar = np.mean(tail_returns)

        return Decimal(str(cvar * 100))  # Convert to percentage

    def calculate_all_risk_metrics(
        self, time_frame: str = "1Y", end_date: Optional[date] = None
    ) -> Optional[FundMetrics]:
        """
        Calculate all risk metrics and update FundMetrics record.

        Args:
            time_frame: Time frame for calculations
            end_date: End date (defaults to today)

        Returns:
            Updated FundMetrics instance or None
        """
        # First calculate basic metrics using parent class
        metrics = self.calculate_all_metrics(time_frame, end_date)
        if not metrics:
            return None

        # Calculate risk metrics
        sharpe = self.calculate_sharpe_ratio(time_frame, end_date)
        sortino = self.calculate_sortino_ratio(time_frame, end_date)
        beta = self.calculate_beta(time_frame, end_date)
        alpha = self.calculate_alpha(time_frame, end_date)
        r_squared = self.calculate_r_squared(time_frame, end_date)

        max_dd, dd_duration, current_dd = self.calculate_max_drawdown(time_frame, end_date)

        var_95 = self.calculate_value_at_risk(time_frame, end_date, confidence=0.95)
        var_99 = self.calculate_value_at_risk(time_frame, end_date, confidence=0.99)
        cvar_95 = self.calculate_conditional_var(time_frame, end_date, confidence=0.95)

        downside_dev = self._calculate_downside_deviation(
            self._get_start_date_for_timeframe(time_frame, end_date), end_date
        )

        # Update metrics record
        metrics.sharpe_ratio = sharpe
        metrics.sortino_ratio = sortino
        metrics.beta = beta
        metrics.alpha = alpha
        metrics.r_squared = r_squared
        metrics.max_drawdown = max_dd
        metrics.max_drawdown_duration = dd_duration
        metrics.current_drawdown = current_dd
        metrics.var_95 = var_95
        metrics.var_99 = var_99
        metrics.cvar_95 = cvar_95
        metrics.downside_deviation = downside_dev
        metrics.benchmark_ticker = self.benchmark_ticker

        metrics.save(
            update_fields=[
                "sharpe_ratio",
                "sortino_ratio",
                "beta",
                "alpha",
                "r_squared",
                "max_drawdown",
                "max_drawdown_duration",
                "current_drawdown",
                "var_95",
                "var_99",
                "cvar_95",
                "downside_deviation",
                "benchmark_ticker",
            ]
        )

        return metrics

    # Helper methods

    def _calculate_downside_deviation(
        self, start_date: date, end_date: date, target_return: float = 0.0
    ) -> Optional[Decimal]:
        """
        Calculate downside deviation (standard deviation of negative returns).

        Args:
            start_date: Start date
            end_date: End date
            target_return: Target return threshold (default: 0)

        Returns:
            Downside deviation as annualized percentage
        """
        returns = self._get_daily_returns(start_date, end_date)
        if len(returns) < 2:
            return None

        # Only consider returns below target
        downside_returns = [r for r in returns if r < target_return]
        if len(downside_returns) < 2:
            return Decimal("0.0000")

        # Calculate standard deviation of downside returns
        downside_variance = np.var(downside_returns, ddof=1)
        downside_std = math.sqrt(downside_variance)

        # Annualize
        annualized_dd = downside_std * math.sqrt(252)

        return Decimal(str(annualized_dd * 100))

    def _get_benchmark_returns(self, start_date: date, end_date: date) -> List[float]:
        """
        Get daily returns for benchmark.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of benchmark returns
        """
        from feefifofunds.models import Fund

        # Get benchmark fund
        benchmark = Fund.objects.filter(ticker=self.benchmark_ticker, is_active=True).first()
        if not benchmark:
            return []

        # Get benchmark prices
        prices_qs = FundPerformance.objects.filter(
            fund=benchmark, date__gte=start_date, date__lte=end_date, interval="1D", is_active=True
        ).order_by("date")

        prices = [float(p.close_price) for p in prices_qs]

        if len(prices) < 2:
            return []

        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                daily_return = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(daily_return)

        return returns

    def _get_benchmark_return(self, time_frame: str, end_date: date) -> Optional[Decimal]:
        """
        Get benchmark return for a time frame.

        Args:
            time_frame: Time frame
            end_date: End date

        Returns:
            Benchmark return as percentage
        """
        from feefifofunds.models import Fund

        benchmark = Fund.objects.filter(ticker=self.benchmark_ticker, is_active=True).first()
        if not benchmark:
            return None

        start_date = self._get_start_date_for_timeframe(time_frame, end_date)
        if not start_date:
            return None

        # Get first and last prices
        prices_qs = FundPerformance.objects.filter(
            fund=benchmark, date__gte=start_date, date__lte=end_date, interval="1D", is_active=True
        ).order_by("date")

        if prices_qs.count() < 2:
            return None

        first_price = prices_qs.first().close_price
        last_price = prices_qs.last().close_price

        if not first_price or not last_price or first_price <= 0:
            return None

        # Calculate return
        benchmark_return = ((last_price - first_price) / first_price) * 100

        # Annualize if needed
        days = (end_date - start_date).days
        if days > 365:
            years = Decimal(str(days / 365.25))
            benchmark_return = ((Decimal("1") + benchmark_return / 100) ** (Decimal("1") / years) - 1) * 100

        return benchmark_return
