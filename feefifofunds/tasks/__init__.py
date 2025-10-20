"""
Celery tasks for FeeFiFoFunds.

This package contains asynchronous tasks for data fetching, calculations, and processing.
"""

from .data_tasks import fetch_daily_prices_task, fetch_fund_data_task, update_all_funds_task

__all__ = [
    "fetch_daily_prices_task",
    "fetch_fund_data_task",
    "update_all_funds_task",
]
