"""
JSON API views for FeeFiFoFunds.

Implements FUND-024: Create Fund List/Detail Endpoints
Uses Django JsonResponse instead of DRF (per PR #307 decision).

Access Control: All endpoints restricted to superusers only.
"""

from datetime import date, timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .decorators import superuser_required
from .models import Fund, FundPerformance


@require_http_methods(["GET"])
@superuser_required(json_response=True)
def fund_list_json(request):
    """
    JSON endpoint for fund list.

    GET /feefifofunds/api/funds/
    Query params:
        - q: Search query (ticker or name)
        - fund_type: Filter by fund type
        - asset_class: Filter by asset class
        - max_expense: Maximum expense ratio
        - limit: Number of results (default: 20)
        - offset: Pagination offset (default: 0)

    Returns:
        JSON with fund list and pagination info

    Access: Superusers only (returns 403 JSON error for non-superusers).
    """
    # Get query parameters
    search = request.GET.get("q", "")
    fund_type = request.GET.get("fund_type", "")
    asset_class = request.GET.get("asset_class", "")
    max_expense = request.GET.get("max_expense", "")
    limit = int(request.GET.get("limit", 20))
    offset = int(request.GET.get("offset", 0))

    # Build queryset
    funds = Fund.objects.filter(is_active=True)

    if search:
        funds = funds.filter(ticker__icontains=search) | funds.filter(name__icontains=search)

    if fund_type:
        funds = funds.filter(fund_type=fund_type)

    if asset_class:
        funds = funds.filter(asset_class=asset_class)

    if max_expense:
        try:
            funds = funds.filter(expense_ratio__lte=float(max_expense))
        except ValueError:
            pass

    # Get total count for pagination
    total = funds.count()

    # Apply pagination
    funds = funds.order_by("ticker")[offset : offset + limit]

    # Serialize funds
    funds_data = []
    for fund in funds:
        funds_data.append(
            {
                "ticker": fund.ticker,
                "name": fund.name,
                "slug": fund.slug,
                "fund_type": fund.fund_type,
                "asset_class": fund.asset_class,
                "expense_ratio": float(fund.expense_ratio) if fund.expense_ratio else None,
                "current_price": float(fund.current_price) if fund.current_price else None,
                "price_change_percent": float(fund.price_change_percent) if fund.price_change_percent else None,
                "aum": float(fund.aum) if fund.aum else None,
                "url": f"/feefifofunds/funds/{fund.slug}/",
            }
        )

    return JsonResponse(
        {
            "count": total,
            "next": offset + limit if offset + limit < total else None,
            "previous": offset - limit if offset >= limit else None,
            "results": funds_data,
        }
    )


@require_http_methods(["GET"])
@superuser_required(json_response=True)
def fund_detail_json(request, slug):
    """
    JSON endpoint for fund detail.

    GET /feefifofunds/api/funds/<slug>/

    Returns:
        JSON with complete fund details

    Access: Superusers only (returns 403 JSON error for non-superusers).
    """
    try:
        fund = Fund.objects.get(slug=slug, is_active=True)
    except Fund.DoesNotExist:
        return JsonResponse({"error": "Fund not found"}, status=404)

    # Get latest metrics
    latest_metrics = fund.get_latest_metrics()

    # Serialize fund
    fund_data = {
        "ticker": fund.ticker,
        "name": fund.name,
        "slug": fund.slug,
        "fund_type": fund.fund_type,
        "asset_class": fund.asset_class,
        "category": fund.category,
        "description": fund.description,
        "inception_date": fund.inception_date.isoformat() if fund.inception_date else None,
        "issuer": fund.issuer,
        "expense_ratio": float(fund.expense_ratio) if fund.expense_ratio else None,
        "management_fee": float(fund.management_fee) if fund.management_fee else None,
        "total_cost_percent": float(fund.total_cost_percent),
        "current_price": float(fund.current_price) if fund.current_price else None,
        "previous_close": float(fund.previous_close) if fund.previous_close else None,
        "price_change": float(fund.price_change) if fund.price_change else None,
        "price_change_percent": float(fund.price_change_percent) if fund.price_change_percent else None,
        "currency": fund.currency,
        "aum": float(fund.aum) if fund.aum else None,
        "avg_volume": fund.avg_volume,
        "exchange": fund.exchange,
        "website": fund.website,
        "last_updated": fund.last_updated.isoformat() if fund.last_updated else None,
    }

    # Add latest metrics if available
    if latest_metrics:
        fund_data["metrics"] = {
            "time_frame": latest_metrics.time_frame,
            "calculation_date": latest_metrics.calculation_date.isoformat(),
            "total_return": float(latest_metrics.total_return) if latest_metrics.total_return else None,
            "annualized_return": float(latest_metrics.annualized_return) if latest_metrics.annualized_return else None,
            "volatility": float(latest_metrics.volatility) if latest_metrics.volatility else None,
            "sharpe_ratio": float(latest_metrics.sharpe_ratio) if latest_metrics.sharpe_ratio else None,
            "sortino_ratio": float(latest_metrics.sortino_ratio) if latest_metrics.sortino_ratio else None,
            "beta": float(latest_metrics.beta) if latest_metrics.beta else None,
            "alpha": float(latest_metrics.alpha) if latest_metrics.alpha else None,
            "max_drawdown": float(latest_metrics.max_drawdown) if latest_metrics.max_drawdown else None,
        }

    return JsonResponse(fund_data)


@require_http_methods(["GET"])
@superuser_required(json_response=True)
def fund_performance_json(request, slug):
    """
    JSON endpoint for fund performance history.

    GET /feefifofunds/api/funds/<slug>/performance/
    Query params:
        - days: Number of days (default: 365)
        - interval: Data interval (default: 1D)

    Returns:
        JSON with OHLCV performance data

    Access: Superusers only (returns 403 JSON error for non-superusers).
    """
    try:
        fund = Fund.objects.get(slug=slug, is_active=True)
    except Fund.DoesNotExist:
        return JsonResponse({"error": "Fund not found"}, status=404)

    # Get parameters
    days = int(request.GET.get("days", 365))
    interval = request.GET.get("interval", "1D")

    # Get performance data
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    performance = FundPerformance.objects.filter(
        fund=fund, date__gte=start_date, date__lte=end_date, interval=interval, is_active=True
    ).order_by("date")

    # Serialize performance data
    performance_data = []
    for perf in performance:
        performance_data.append(
            {
                "date": perf.date.isoformat(),
                "open": float(perf.open_price) if perf.open_price else None,
                "high": float(perf.high_price) if perf.high_price else None,
                "low": float(perf.low_price) if perf.low_price else None,
                "close": float(perf.close_price),
                "adjusted_close": float(perf.adjusted_close) if perf.adjusted_close else None,
                "volume": perf.volume,
            }
        )

    return JsonResponse(
        {
            "ticker": fund.ticker,
            "interval": interval,
            "data": performance_data,
        }
    )


@require_http_methods(["GET"])
@superuser_required(json_response=True)
def fund_holdings_json(request, slug):
    """
    JSON endpoint for fund holdings.

    GET /feefifofunds/api/funds/<slug>/holdings/
    Query params:
        - top_n: Number of holdings to return (default: all)

    Returns:
        JSON with fund holdings

    Access: Superusers only (returns 403 JSON error for non-superusers).
    """
    try:
        fund = Fund.objects.get(slug=slug, is_active=True)
    except Fund.DoesNotExist:
        return JsonResponse({"error": "Fund not found"}, status=404)

    # Get parameters
    top_n = request.GET.get("top_n")
    if top_n:
        top_n = int(top_n)

    # Get holdings
    holdings = fund.get_holdings(top_n=top_n)

    # Serialize holdings
    holdings_data = []
    for holding in holdings:
        holdings_data.append(
            {
                "ticker": holding.ticker,
                "name": holding.name,
                "weight": float(holding.weight),
                "market_value": float(holding.market_value) if holding.market_value else None,
                "sector": holding.sector,
                "holding_type": holding.holding_type,
                "as_of_date": holding.as_of_date.isoformat(),
            }
        )

    return JsonResponse(
        {
            "ticker": fund.ticker,
            "holdings_count": len(holdings_data),
            "holdings": holdings_data,
        }
    )
