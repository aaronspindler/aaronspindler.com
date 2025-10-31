"""
Fund Comparison Engine.

Implements FUND-019: Build Fund Comparison Engine
Provides logic for comparing multiple funds across various metrics.
"""

from decimal import Decimal
from typing import List

from feefifofunds.models import Fund, FundHolding, FundMetrics


class ComparisonEngine:
    """
    Engine for comparing multiple funds.

    Provides side-by-side comparison of performance, risk, costs, and holdings.
    """

    def __init__(self, fund_tickers: List[str]):
        """
        Initialize comparison engine.

        Args:
            fund_tickers: List of fund ticker symbols to compare
        """
        self.fund_tickers = [t.upper() for t in fund_tickers]
        self.funds = Fund.objects.filter(ticker__in=self.fund_tickers, is_active=True)

        if self.funds.count() != len(self.fund_tickers):
            found = [f.ticker for f in self.funds]
            missing = [t for t in self.fund_tickers if t not in found]
            raise ValueError(f"Funds not found: {', '.join(missing)}")

    def compare_performance(self, time_frame: str = "1Y") -> dict:
        """
        Compare performance metrics across funds.

        Args:
            time_frame: Time frame for comparison

        Returns:
            Dictionary with comparison data
        """
        comparison = {"time_frame": time_frame, "funds": []}

        for fund in self.funds:
            metrics = (
                FundMetrics.objects.filter(fund=fund, time_frame=time_frame, is_active=True)
                .order_by("-calculation_date")
                .first()
            )

            fund_data = {
                "ticker": fund.ticker,
                "name": fund.name,
                "metrics": None,
            }

            if metrics:
                fund_data["metrics"] = {
                    "total_return": float(metrics.total_return) if metrics.total_return else None,
                    "annualized_return": float(metrics.annualized_return) if metrics.annualized_return else None,
                    "volatility": float(metrics.volatility) if metrics.volatility else None,
                    "sharpe_ratio": float(metrics.sharpe_ratio) if metrics.sharpe_ratio else None,
                    "max_drawdown": float(metrics.max_drawdown) if metrics.max_drawdown else None,
                }

            comparison["funds"].append(fund_data)

        return comparison

    def compare_costs(self) -> dict:
        """
        Compare costs and fees across funds.

        Returns:
            Dictionary with cost comparison
        """
        comparison = {"funds": []}

        for fund in self.funds:
            comparison["funds"].append(
                {
                    "ticker": fund.ticker,
                    "name": fund.name,
                    "expense_ratio": float(fund.expense_ratio) if fund.expense_ratio else None,
                    "management_fee": float(fund.management_fee) if fund.management_fee else None,
                    "front_load": float(fund.front_load) if fund.front_load else None,
                    "back_load": float(fund.back_load) if fund.back_load else None,
                    "total_cost": float(fund.total_cost_percent),
                }
            )

        return comparison

    def compare_risk_metrics(self, time_frame: str = "1Y") -> dict:
        """
        Compare risk metrics across funds.

        Args:
            time_frame: Time frame for comparison

        Returns:
            Dictionary with risk comparison
        """
        comparison = {"time_frame": time_frame, "funds": []}

        for fund in self.funds:
            metrics = (
                FundMetrics.objects.filter(fund=fund, time_frame=time_frame, is_active=True)
                .order_by("-calculation_date")
                .first()
            )

            fund_data = {
                "ticker": fund.ticker,
                "name": fund.name,
                "risk_metrics": None,
            }

            if metrics:
                fund_data["risk_metrics"] = {
                    "volatility": float(metrics.volatility) if metrics.volatility else None,
                    "beta": float(metrics.beta) if metrics.beta else None,
                    "sharpe_ratio": float(metrics.sharpe_ratio) if metrics.sharpe_ratio else None,
                    "sortino_ratio": float(metrics.sortino_ratio) if metrics.sortino_ratio else None,
                    "max_drawdown": float(metrics.max_drawdown) if metrics.max_drawdown else None,
                    "var_95": float(metrics.var_95) if metrics.var_95 else None,
                }

            comparison["funds"].append(fund_data)

        return comparison

    def analyze_holdings_overlap(self) -> dict:
        """
        Analyze overlap in fund holdings.

        Returns:
            Dictionary with overlap analysis
        """
        holdings_by_fund = {}

        # Get latest holdings for each fund
        for fund in self.funds:
            latest_holdings = FundHolding.objects.filter(fund=fund, is_active=True).order_by("-as_of_date", "-weight")

            if latest_holdings.exists():
                # Get unique as_of_date
                latest_date = latest_holdings.first().as_of_date
                holdings = latest_holdings.filter(as_of_date=latest_date)
                holdings_by_fund[fund.ticker] = set(h.ticker for h in holdings)
            else:
                holdings_by_fund[fund.ticker] = set()

        # Calculate overlaps
        overlaps = []
        fund_list = list(self.funds)
        for i in range(len(fund_list)):
            for j in range(i + 1, len(fund_list)):
                fund1 = fund_list[i]
                fund2 = fund_list[j]

                holdings1 = holdings_by_fund.get(fund1.ticker, set())
                holdings2 = holdings_by_fund.get(fund2.ticker, set())

                if holdings1 and holdings2:
                    overlap = holdings1.intersection(holdings2)
                    overlap_pct = (len(overlap) / min(len(holdings1), len(holdings2))) * 100

                    overlaps.append(
                        {
                            "fund1": fund1.ticker,
                            "fund2": fund2.ticker,
                            "common_holdings": len(overlap),
                            "overlap_percent": overlap_pct,
                            "holdings": list(overlap)[:10],  # Top 10
                        }
                    )

        return {"overlaps": overlaps}

    def generate_comparison_summary(self, time_frame: str = "1Y") -> dict:
        """
        Generate complete comparison summary.

        Args:
            time_frame: Time frame for metrics

        Returns:
            Comprehensive comparison dictionary
        """
        return {
            "tickers": self.fund_tickers,
            "time_frame": time_frame,
            "performance": self.compare_performance(time_frame),
            "risk": self.compare_risk_metrics(time_frame),
            "costs": self.compare_costs(),
            "holdings_overlap": self.analyze_holdings_overlap(),
            "summary": self._generate_winner_analysis(time_frame),
        }

    def _generate_winner_analysis(self, time_frame: str) -> dict:
        """
        Determine which fund "wins" in each category.

        Args:
            time_frame: Time frame for analysis

        Returns:
            Dictionary showing best fund in each category
        """
        analysis = {
            "best_return": None,
            "best_risk_adjusted": None,
            "lowest_cost": None,
            "lowest_risk": None,
        }

        # Get metrics for all funds
        funds_with_metrics = []
        for fund in self.funds:
            metrics = (
                FundMetrics.objects.filter(fund=fund, time_frame=time_frame, is_active=True)
                .order_by("-calculation_date")
                .first()
            )
            if metrics:
                funds_with_metrics.append((fund, metrics))

        if not funds_with_metrics:
            return analysis

        # Best return
        best_return_fund = max(
            funds_with_metrics, key=lambda x: x[1].annualized_return if x[1].annualized_return else Decimal("-999999")
        )
        analysis["best_return"] = {
            "ticker": best_return_fund[0].ticker,
            "value": float(best_return_fund[1].annualized_return),
        }

        # Best risk-adjusted (highest Sharpe)
        funds_with_sharpe = [(f, m) for f, m in funds_with_metrics if m.sharpe_ratio]
        if funds_with_sharpe:
            best_sharpe_fund = max(funds_with_sharpe, key=lambda x: x[1].sharpe_ratio)
            analysis["best_risk_adjusted"] = {
                "ticker": best_sharpe_fund[0].ticker,
                "sharpe_ratio": float(best_sharpe_fund[1].sharpe_ratio),
            }

        # Lowest cost
        funds_with_cost = [f for f in self.funds if f.expense_ratio]
        if funds_with_cost:
            lowest_cost_fund = min(funds_with_cost, key=lambda x: x.expense_ratio)
            analysis["lowest_cost"] = {
                "ticker": lowest_cost_fund.ticker,
                "expense_ratio": float(lowest_cost_fund.expense_ratio),
            }

        # Lowest risk (lowest volatility)
        funds_with_vol = [(f, m) for f, m in funds_with_metrics if m.volatility]
        if funds_with_vol:
            lowest_risk_fund = min(funds_with_vol, key=lambda x: x[1].volatility)
            analysis["lowest_risk"] = {
                "ticker": lowest_risk_fund[0].ticker,
                "volatility": float(lowest_risk_fund[1].volatility),
            }

        return analysis
