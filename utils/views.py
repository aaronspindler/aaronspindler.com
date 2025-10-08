from django.utils import timezone
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from utils.models import NotificationEmail, NotificationPhoneNumber
from utils.phone_numbers import clean_phone_number

@login_required
def add_phone(request):
    if request.subscription_metadata.get('sms_notifications', False):
        if request.method == "POST":
            phone_number = request.POST.get("phone_number")
            if phone_number:
                phone_number = clean_phone_number(phone_number)
                phone_number, created = NotificationPhoneNumber.objects.get_or_create(user=request.user, phone_number=phone_number)
                if created:
                    phone_number.create_verification_message()
                    messages.success(request, "Phone number added successfully")
                else:
                    messages.info(request, "Phone number already exists")
            else:
                messages.error(request, "Phone number is required")
            return redirect('home')
        else:
            return HttpResponseNotAllowed(["POST"])
    else:
        messages.error(request, "SMS notifications are not available on your current plan.")
        return redirect('home')

@login_required
def add_email(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            email, created = NotificationEmail.objects.get_or_create(user=request.user, email=email)
            if created:
                email.create_verification_message()
                messages.success(request, "Email added successfully")
            else:
                messages.info(request, "Email already exists")
        else:
            messages.error(request, "Email is required")
        return redirect('home')
    else:
        return HttpResponseNotAllowed(["POST"])

@login_required
def delete_phone(request, phone_id):
    if request.method == "POST":
        phone_number = get_object_or_404(NotificationPhoneNumber, id=phone_id, user=request.user)
        phone_number.delete()
        messages.success(request, "Phone number deleted successfully")
        return redirect('home')
    else:
        return HttpResponseNotAllowed(["POST"])

@login_required
def delete_email(request, email_id):
    if request.method == "POST":
        email = get_object_or_404(NotificationEmail, id=email_id, user=request.user)
        email.delete()
        messages.success(request, "Email deleted successfully")
        return redirect('home')
    else:
        return HttpResponseNotAllowed(["POST"])

@login_required
def verify_phone(request, phone_id):
    # This will require the user to enter the code in the frontend
    if request.method == "POST":
        phone_number = get_object_or_404(NotificationPhoneNumber, id=phone_id)
        code = request.POST.get("code")
        if str(phone_number.verification_code) == code:
            phone_number.verified = True
            phone_number.verified_at = timezone.now()
            phone_number.save()
            messages.success(request, "Phone number verified successfully")
        else:
            messages.error(request, "Invalid verification code")
        return redirect('home')
        
    else:
        return HttpResponseNotAllowed(["POST"])

def verify_email(request, email_id, code=None):
    # This will use a magic link to verify an email address or a POST request with a code
    email = get_object_or_404(NotificationEmail, id=email_id)
    
    if request.method == "GET":
        verification_code = str(email.verification_code)
    elif request.method == "POST":
        verification_code = str(email.verification_code_small)
        code = request.POST.get("code")
    else:
        return HttpResponseNotAllowed(["GET", "POST"])
    
    if verification_code == code:
        email.verified = True
        email.verified_at = timezone.now()
        email.save()
        messages.success(request, "Email verified successfully")
    else:
        messages.error(request, "Invalid verification code")
    
    return redirect('home')

def unsubscribe(request, unsubscribe_code):
    email = get_object_or_404(NotificationEmail, unsubscribe_code=unsubscribe_code)
    address = email.email
    email.delete()
    messages.success(request, f"{address} has been unsubscribed from all notifications")
    return redirect('home')


# Lighthouse monitoring views
import json
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from datetime import timedelta
from utils.models import LighthouseAudit


@cache_page(60 * 60)  # Cache for 1 hour
def lighthouse_badge_endpoint(request):
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


def lighthouse_history_page(request):
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