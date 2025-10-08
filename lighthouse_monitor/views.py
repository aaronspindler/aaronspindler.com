import json
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import cache_page
from datetime import timedelta
from .models import LighthouseAudit


@cache_page(60 * 60)  # Cache for 1 hour
def badge_endpoint(request):
    """
    API endpoint for shields.io badge data.
    Returns the latest Lighthouse audit scores in shields.io endpoint format.
    """
    try:
        latest_audit = LighthouseAudit.objects.latest('audit_date')
        
        # Format scores as "P/A/BP/SEO"
        message = f"{latest_audit.performance_score}/{latest_audit.accessibility_score}/{latest_audit.best_practices_score}/{latest_audit.seo_score}"
        
        # Determine badge color based on average score
        avg_score = latest_audit.average_score
        if avg_score >= 90:
            color = "brightgreen"
        elif avg_score >= 70:
            color = "yellow"
        else:
            color = "red"
        
        return JsonResponse({
            "schemaVersion": 1,
            "label": "lighthouse",
            "message": message,
            "color": color
        })
    except LighthouseAudit.DoesNotExist:
        return JsonResponse({
            "schemaVersion": 1,
            "label": "lighthouse",
            "message": "no data",
            "color": "lightgrey"
        }, status=404)


def history_page(request):
    """
    Display Lighthouse audit history with chart visualization.
    Shows last 30 days of audit data.
    """
    # Get audits from the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    audits = LighthouseAudit.objects.filter(
        audit_date__gte=thirty_days_ago
    ).order_by('audit_date')
    
    # Prepare data for Chart.js
    chart_data = {
        'labels': [audit.audit_date.strftime('%Y-%m-%d %H:%M') for audit in audits],
        'performance': [audit.performance_score for audit in audits],
        'accessibility': [audit.accessibility_score for audit in audits],
        'best_practices': [audit.best_practices_score for audit in audits],
        'seo': [audit.seo_score for audit in audits],
    }
    
    context = {
        'audits': audits.reverse(),  # Show newest first in table
        'chart_data': json.dumps(chart_data),  # Serialize for JavaScript
        'latest_audit': audits.last() if audits.exists() else None,
    }
    
    return render(request, 'lighthouse_monitor/history.html', context)
