"""
Celery tasks for data fetching and updates.

Implements FUND-014: Create Daily Price Update Task
Implements FUND-015: Create Holdings Update Task
"""

from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

from feefifofunds.models import DataSync, Fund, FundPerformance
from feefifofunds.services.validators import DataValidator

# YahooFinance imported inside task functions to avoid import errors
# when yfinance package is not installed (e.g., during test collection)


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

    Returns:
        Dict with task results
    """
    from feefifofunds.services.data_sources.yahoo_finance import YahooFinance

    source = YahooFinance()
    validator = DataValidator()

    # Get all active funds
    funds = Fund.objects.filter(is_active=True)
    total_funds = funds.count()

    results = {
        "total_funds": total_funds,
        "successful": 0,
        "failed": 0,
        "failed_tickers": [],
        "records_created": 0,
        "records_updated": 0,
    }

    # Create sync record
    sync = source.create_sync_record(sync_type=DataSync.SyncType.PRICES)

    try:
        # Fetch prices for today and yesterday (to get previous close)
        end_date = date.today()
        start_date = end_date - timedelta(days=5)  # Extra buffer for weekends/holidays

        for fund in funds:
            try:
                # Fetch historical prices (last 5 days)
                price_data = source.fetch_historical_prices(
                    ticker=fund.ticker, start_date=start_date, end_date=end_date, interval="1d"
                )

                if not price_data:
                    results["failed"] += 1
                    results["failed_tickers"].append(fund.ticker)
                    continue

                # Validate and save data
                valid_data, invalid_data = validator.validate_batch(price_data)

                for perf in valid_data:
                    # Calculate quality score
                    quality_score = validator.calculate_data_quality_score(perf)

                    # Save to database
                    _, created = FundPerformance.objects.update_or_create(
                        fund=fund,
                        date=perf.date,
                        interval=perf.interval,
                        defaults={
                            "open_price": perf.open_price,
                            "high_price": perf.high_price,
                            "low_price": perf.low_price,
                            "close_price": perf.close_price,
                            "adjusted_close": perf.adjusted_close,
                            "volume": perf.volume,
                            "dividend": perf.dividend,
                            "split_ratio": perf.split_ratio,
                            "data_source": perf.source,
                            "data_quality_score": quality_score,
                        },
                    )

                    if created:
                        results["records_created"] += 1
                    else:
                        results["records_updated"] += 1

                # Update fund's current price and last update time
                if price_data:
                    latest = price_data[-1]
                    fund.current_price = latest.close_price
                    fund.last_price_update = timezone.now()
                    fund.save(update_fields=["current_price", "last_price_update"])

                results["successful"] += 1

            except Exception as e:
                results["failed"] += 1
                results["failed_tickers"].append(f"{fund.ticker}: {str(e)}")

        # Mark sync as complete
        sync.records_fetched = len(price_data) if price_data else 0
        sync.records_created = results["records_created"]
        sync.records_updated = results["records_updated"]
        sync.mark_complete(success=True)

    except Exception as e:
        sync.mark_complete(success=False, error_message=str(e))
        raise

    return results


@shared_task(
    name="feefifofunds.fetch_fund_data",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def fetch_fund_data_task(self, ticker: str):
    """
    Fetch complete fund data for a single fund.

    Args:
        ticker: Fund ticker symbol

    Returns:
        Dict with fetch results
    """
    from feefifofunds.services.data_sources.yahoo_finance import YahooFinance

    source = YahooFinance()
    validator = DataValidator()

    result = {"ticker": ticker, "success": False, "error": None}

    try:
        # Fetch fund info
        fund_data = source.fetch_fund_info(ticker)

        # Validate
        is_valid, errors = validator.validate_fund_data(fund_data)
        if not is_valid:
            result["error"] = f"Validation failed: {', '.join(errors)}"
            return result

        # Save to database
        fund, created = Fund.objects.update_or_create(
            ticker=fund_data.ticker,
            defaults={
                "name": fund_data.name,
                "fund_type": fund_data.fund_type,
                "asset_class": fund_data.asset_class,
                "category": fund_data.category,
                "description": fund_data.description,
                "inception_date": fund_data.inception_date,
                "issuer": fund_data.issuer,
                "expense_ratio": fund_data.expense_ratio,
                "management_fee": fund_data.management_fee,
                "current_price": fund_data.current_price,
                "previous_close": fund_data.previous_close,
                "currency": fund_data.currency,
                "aum": fund_data.aum,
                "avg_volume": fund_data.avg_volume,
                "exchange": fund_data.exchange,
                "website": fund_data.website,
                "isin": fund_data.isin,
                "last_updated": fund_data.fetched_at,
            },
        )

        result["success"] = True
        result["created"] = created

    except Exception as e:
        result["error"] = str(e)

    return result


@shared_task(name="feefifofunds.update_all_funds")
def update_all_funds_task():
    """
    Update all fund information (metadata, not prices).

    Run weekly to update fund details like AUM, expense ratios, etc.

    Returns:
        Dict with update results
    """
    funds = Fund.objects.filter(is_active=True)
    results = {"total": funds.count(), "updated": 0, "failed": 0}

    for fund in funds:
        try:
            fetch_fund_data_task.delay(fund.ticker)
            results["updated"] += 1
        except Exception:
            results["failed"] += 1

    return results
