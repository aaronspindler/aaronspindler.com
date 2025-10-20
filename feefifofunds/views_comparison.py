"""
Comparison views for FeeFiFoFunds.

Implements FUND-025: Implement Comparison View
Uses Django JsonResponse (no DRF per PR #307).
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .services.comparison import ComparisonEngine


@require_http_methods(["POST", "GET"])
def compare_funds_json(request):
    """
    Compare multiple funds.

    POST /feefifofunds/api/compare/
    Body: {"tickers": ["SPY", "VOO", "IVV"], "time_frame": "1Y"}

    GET /feefifofunds/api/compare/?tickers=SPY,VOO,IVV&time_frame=1Y

    Returns:
        JSON with comprehensive comparison data
    """
    # Get tickers
    if request.method == "POST":
        import json

        try:
            body = json.loads(request.body)
            tickers = body.get("tickers", [])
            time_frame = body.get("time_frame", "1Y")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:  # GET
        tickers_str = request.GET.get("tickers", "")
        tickers = [t.strip() for t in tickers_str.split(",") if t.strip()]
        time_frame = request.GET.get("time_frame", "1Y")

    # Validate
    if not tickers:
        return JsonResponse({"error": "No tickers provided"}, status=400)

    if len(tickers) < 2:
        return JsonResponse({"error": "At least 2 funds required for comparison"}, status=400)

    if len(tickers) > 10:
        return JsonResponse({"error": "Maximum 10 funds can be compared"}, status=400)

    try:
        # Create comparison engine
        engine = ComparisonEngine(tickers)

        # Generate comparison
        comparison = engine.generate_comparison_summary(time_frame)

        return JsonResponse(comparison)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Comparison failed: {str(e)}"}, status=500)
