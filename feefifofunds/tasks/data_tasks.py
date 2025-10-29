"""
Celery tasks for data fetching and updates.

CURRENTLY DISABLED: External data sources not implemented.

Implements FUND-014: Create Daily Price Update Task (stub)
Implements FUND-015: Create Holdings Update Task (stub)

These tasks are stubs awaiting implementation of reliable data sources.
"""

from celery import shared_task


@shared_task(
    name="feefifofunds.fetch_daily_prices",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def fetch_daily_prices_task(self):
    """
    Fetch daily prices for all active funds.

    Scheduled to run daily at 6 PM (after market close).
    Implements FUND-014: Create Daily Price Update Task

    CURRENTLY DISABLED: No data sources implemented.

    Returns:
        Dict with task results
    """
    return {
        "status": "disabled",
        "message": "Data fetching disabled - no reliable data sources available",
        "total_funds": 0,
        "successful": 0,
        "failed": 0,
    }


@shared_task(
    name="feefifofunds.fetch_fund_data",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def fetch_fund_data_task(self, ticker: str):
    """
    Fetch complete fund data for a single fund.

    CURRENTLY DISABLED: No data sources implemented.

    Args:
        ticker: Fund ticker symbol

    Returns:
        Dict with fetch results
    """
    return {
        "ticker": ticker,
        "success": False,
        "error": "Data fetching disabled - no reliable data sources available",
    }


@shared_task(name="feefifofunds.update_all_funds")
def update_all_funds_task():
    """
    Update all fund information (metadata, not prices).

    Run weekly to update fund details like AUM, expense ratios, etc.

    CURRENTLY DISABLED: No data sources implemented.

    Returns:
        Dict with update results
    """
    return {
        "status": "disabled",
        "message": "Data fetching disabled - no reliable data sources available",
        "total": 0,
        "updated": 0,
        "failed": 0,
    }
