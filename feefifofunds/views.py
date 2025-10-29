"""
Views for FeeFiFoFunds frontend.

Implements FUND-032: Base Templates and basic views.
"""

from django.shortcuts import render
from django.views.generic import DetailView, ListView

from .models import Fund


def home(request):
    """
    Home page view.

    Shows popular funds, quick stats, and search.
    """
    # Get popular funds (top 6 by AUM)
    popular_funds = Fund.objects.filter(is_active=True).order_by("-aum")[:6]

    # Calculate stats
    stats = {
        "total_funds": Fund.objects.filter(is_active=True).count(),
        "data_points": 0,  # Will calculate from FundPerformance later
        "last_update": "Today",  # Will get from actual data later
    }

    context = {
        "popular_funds": popular_funds,
        "stats": stats,
    }

    return render(request, "feefifofunds/home.html", context)


class FundListView(ListView):
    """
    Fund list view with filtering and sorting.

    Implements FUND-033 (basic version, full implementation in FUND-033 PR).
    """

    model = Fund
    template_name = "feefifofunds/fund_list.html"
    context_object_name = "funds"
    paginate_by = 20

    def get_queryset(self):
        """Filter and sort funds based on query parameters."""
        queryset = Fund.objects.filter(is_active=True)

        # Search
        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(ticker__icontains=search_query) | queryset.filter(name__icontains=search_query)

        # Filter by fund type
        fund_type = self.request.GET.get("fund_type")
        if fund_type:
            queryset = queryset.filter(fund_type=fund_type)

        # Filter by asset class
        asset_class = self.request.GET.get("asset_class")
        if asset_class:
            queryset = queryset.filter(asset_class=asset_class)

        # Filter by max expense ratio
        max_expense = self.request.GET.get("max_expense")
        if max_expense:
            try:
                queryset = queryset.filter(expense_ratio__lte=float(max_expense))
            except ValueError:
                pass

        # Sorting
        sort_by = self.request.GET.get("sort", "ticker")
        queryset = queryset.order_by(sort_by)

        return queryset


class FundDetailView(DetailView):
    """
    Fund detail view.

    Implements FUND-034 (basic version, full implementation in FUND-034 PR).
    """

    model = Fund
    template_name = "feefifofunds/fund_detail.html"
    context_object_name = "fund"

    def get_queryset(self):
        """Only show active funds."""
        return Fund.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)

        # Get latest metrics (will be populated by FUND-017)
        context["latest_metrics"] = self.object.get_latest_metrics()

        # Get recent performance (last 30 days)
        context["recent_performance"] = self.object.get_latest_performance(limit=30)

        # Get top holdings
        context["top_holdings"] = self.object.get_holdings(top_n=10)

        return context


def compare_view(request):
    """
    Fund comparison view.

    Implements FUND-035 (placeholder, full implementation in FUND-035 PR).
    """
    context = {
        "message": "Comparison tool will be fully implemented in FUND-035",
    }

    return render(request, "feefifofunds/compare.html", context)
