from decimal import Decimal

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import Fund


def fund_list(request):
    """
    List all funds with filtering capabilities.
    Supports filtering by fund_type, asset_class, geographic_focus, and MER range.
    """
    funds = Fund.objects.select_related("provider").filter(is_active=True)

    # Get filter parameters from query string
    fund_type = request.GET.get("fund_type")
    asset_class = request.GET.get("asset_class")
    geographic_focus = request.GET.get("geographic_focus")
    max_mer = request.GET.get("max_mer")

    # Apply filters
    if fund_type:
        funds = funds.filter(fund_type=fund_type)

    if asset_class:
        funds = funds.filter(asset_class=asset_class)

    if geographic_focus:
        funds = funds.filter(geographic_focus=geographic_focus)

    if max_mer:
        try:
            max_mer_decimal = Decimal(max_mer)
            funds = funds.filter(mer__lte=max_mer_decimal)
        except (ValueError, TypeError):
            pass

    # Get unique values for filter dropdowns
    fund_types = Fund.FUND_TYPE_CHOICES
    asset_classes = Fund.ASSET_CLASS_CHOICES
    geographic_focuses = Fund.GEOGRAPHIC_FOCUS_CHOICES

    context = {
        "funds": funds.order_by("fund_type", "mer"),
        "fund_types": fund_types,
        "asset_classes": asset_classes,
        "geographic_focuses": geographic_focuses,
        "selected_fund_type": fund_type,
        "selected_asset_class": asset_class,
        "selected_geographic_focus": geographic_focus,
        "selected_max_mer": max_mer,
    }

    return render(request, "feefifofunds/fund_list.html", context)


def fund_detail(request, slug):
    """
    Display detailed information about a specific fund.
    """
    fund = get_object_or_404(Fund.objects.select_related("provider"), slug=slug)

    # Calculate fee impact examples
    initial_investment = 10000
    years = 25
    fee_impact = fund.calculate_fee_impact(initial_investment, years)

    # Find similar funds for comparison
    similar_funds = (
        Fund.objects.filter(asset_class=fund.asset_class, geographic_focus=fund.geographic_focus, is_active=True)
        .exclude(pk=fund.pk)
        .select_related("provider")
        .order_by("mer")[:5]
    )

    context = {
        "fund": fund,
        "fee_impact": fee_impact,
        "similar_funds": similar_funds,
        "initial_investment": initial_investment,
        "years": years,
    }

    return render(request, "feefifofunds/fund_detail.html", context)


def compare_funds(request):
    """
    Compare multiple funds side-by-side.
    Accepts fund IDs via GET parameters (e.g., ?funds=1&funds=2&funds=3).
    """
    fund_ids = request.GET.getlist("funds")

    funds = []
    if fund_ids:
        funds = Fund.objects.filter(id__in=fund_ids, is_active=True).select_related("provider")

    # Calculate fee impact for each fund (example: $10,000 over 25 years)
    initial_investment = 10000
    years = 25

    comparison_data = []
    for fund in funds:
        fee_impact = fund.calculate_fee_impact(initial_investment, years)
        comparison_data.append(
            {
                "fund": fund,
                "fee_impact": fee_impact,
            }
        )

    # Get all funds for selection dropdown
    all_funds = Fund.objects.filter(is_active=True).select_related("provider").order_by("ticker")

    context = {
        "comparison_data": comparison_data,
        "all_funds": all_funds,
        "initial_investment": initial_investment,
        "years": years,
    }

    return render(request, "feefifofunds/compare.html", context)


def search_funds(request):
    """
    API endpoint for searching/autocomplete funds.
    Returns JSON with matching funds.
    """
    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"results": []})

    # Search by ticker, name, or provider
    funds = (
        Fund.objects.filter(
            Q(ticker__icontains=query)
            | Q(name__icontains=query)
            | Q(provider__name__icontains=query)
            | Q(description__icontains=query),
            is_active=True,
        )
        .select_related("provider")
        .order_by("ticker")[:20]
    )

    results = [
        {
            "id": fund.id,
            "ticker": fund.ticker,
            "name": fund.name,
            "provider": fund.provider.name,
            "fund_type": fund.get_fund_type_display(),
            "mer": str(fund.mer),
            "slug": fund.slug,
        }
        for fund in funds
    ]

    return JsonResponse({"results": results})


def calculate_fee_impact(request):
    """
    API endpoint to calculate fee impact for a given fund and parameters.
    Accepts GET parameters: fund_id, initial_investment, years, annual_return
    """
    try:
        fund_id = request.GET.get("fund_id")
        initial_investment = Decimal(request.GET.get("initial_investment", 10000))
        years = int(request.GET.get("years", 25))
        annual_return = float(request.GET.get("annual_return", 7.0))

        if not fund_id:
            return JsonResponse({"error": "fund_id is required"}, status=400)

        fund = get_object_or_404(Fund, pk=fund_id, is_active=True)

        # Calculate fee impact
        fee_impact = fund.calculate_fee_impact(
            initial_investment=float(initial_investment), years=years, annual_return=annual_return
        )

        # Add fund details to response
        response_data = {
            "fund": {
                "id": fund.id,
                "ticker": fund.ticker,
                "name": fund.name,
                "mer": str(fund.mer),
            },
            "parameters": {
                "initial_investment": str(initial_investment),
                "years": years,
                "annual_return": annual_return,
            },
            "results": fee_impact,
        }

        return JsonResponse(response_data)

    except (ValueError, TypeError) as e:
        return JsonResponse({"error": f"Invalid parameters: {e!s}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {e!s}"}, status=500)
