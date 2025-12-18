from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from utils.models import NotificationEmail, NotificationPhoneNumber
from utils.phone_numbers import clean_phone_number


@login_required
def add_phone(request):
    if request.subscription_metadata.get("sms_notifications", False):
        if request.method == "POST":
            phone_number = request.POST.get("phone_number")
            if phone_number:
                phone_number = clean_phone_number(phone_number)
                phone_number, created = NotificationPhoneNumber.objects.get_or_create(
                    user=request.user, phone_number=phone_number
                )
                if created:
                    phone_number.create_verification_message()
                    messages.success(request, "Phone number added successfully")
                else:
                    messages.info(request, "Phone number already exists")
            else:
                messages.error(request, "Phone number is required")
            return redirect("home")
        else:
            return HttpResponseNotAllowed(["POST"])
    else:
        messages.error(request, "SMS notifications are not available on your current plan.")
        return redirect("home")


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
        return redirect("home")
    else:
        return HttpResponseNotAllowed(["POST"])


@login_required
def delete_phone(request, phone_id):
    if request.method == "POST":
        phone_number = get_object_or_404(NotificationPhoneNumber, id=phone_id, user=request.user)
        phone_number.delete()
        messages.success(request, "Phone number deleted successfully")
        return redirect("home")
    else:
        return HttpResponseNotAllowed(["POST"])


@login_required
def delete_email(request, email_id):
    if request.method == "POST":
        email = get_object_or_404(NotificationEmail, id=email_id, user=request.user)
        email.delete()
        messages.success(request, "Email deleted successfully")
        return redirect("home")
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
        return redirect("home")

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

    return redirect("home")


def unsubscribe(request, unsubscribe_code):
    email = get_object_or_404(NotificationEmail, unsubscribe_code=unsubscribe_code)
    address = email.email
    email.delete()
    messages.success(request, f"{address} has been unsubscribed from all notifications")
    return redirect("home")


# Lighthouse monitoring views
import json

from django.views.decorators.cache import cache_page

from utils.models import LighthouseAudit


@cache_page(60 * 60)  # Cache for 1 hour
def lighthouse_badge_endpoint(request):
    """
    API endpoint for shields.io badge data.
    Returns the latest Lighthouse audit scores in shields.io endpoint format.
    """
    try:
        latest_audit = LighthouseAudit.objects.latest("audit_date")

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

        return JsonResponse(
            {
                "schemaVersion": 1,
                "label": "lighthouse",
                "message": message,
                "color": color,
            }
        )
    except LighthouseAudit.DoesNotExist:
        return JsonResponse(
            {
                "schemaVersion": 1,
                "label": "lighthouse",
                "message": "no data",
                "color": "lightgrey",
            },
            status=404,
        )


def lighthouse_history_page(request):
    """
    Display Lighthouse audit history with chart visualization.
    Shows all audit data.
    """
    # Get all audits
    audits = LighthouseAudit.objects.all().order_by("audit_date")

    # Prepare data for Chart.js
    chart_data = {
        "labels": [audit.audit_date.strftime("%Y-%m-%d") for audit in audits],
        "performance": [audit.performance_score for audit in audits],
        "accessibility": [audit.accessibility_score for audit in audits],
        "best_practices": [audit.best_practices_score for audit in audits],
        "seo": [audit.seo_score for audit in audits],
    }

    context = {
        "audits": audits.reverse(),  # Show newest first in table
        "chart_data": json.dumps(chart_data),  # Serialize for JavaScript
        "latest_audit": audits.last() if audits.exists() else None,
    }

    return render(request, "lighthouse_monitor/history.html", context)


# Search views
from utils.search import search_blog_posts, search_books, search_projects


@require_GET
def search_view(request):
    """
    Unified search view for blog posts, projects, and books.
    Supports full-text search.
    """
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip() or None
    content_type = request.GET.get("type", "all")  # all, blog, projects, books

    results = {"blog_posts": [], "projects": [], "books": []}

    # Search blog posts
    if content_type in ["all", "blog"]:
        results["blog_posts"] = search_blog_posts(query=query if query else None, category=category)

    # Search projects
    if content_type in ["all", "projects"]:
        results["projects"] = search_projects(query=query if query else None)

    # Search books
    if content_type in ["all", "books"]:
        results["books"] = search_books(query=query if query else None)

    context = {
        "query": query,
        "category": category,
        "content_type": content_type,
        "results": results,
        "total_results": len(results["blog_posts"]) + len(results["projects"]) + len(results["books"]),
    }

    return render(request, "blog/search_results.html", context)


@require_GET
def search_autocomplete(request):
    """
    API endpoint for search autocomplete suggestions.
    Returns top results from blog posts, projects, and books.
    """
    query = request.GET.get("q", "").strip()

    if not query or len(query) < 2:
        return JsonResponse({"suggestions": []})

    suggestions = []

    # Get blog post suggestions (limit to 5)
    blog_posts = search_blog_posts(query=query)[:5]
    for post in blog_posts:
        suggestions.append(
            {
                "title": post["blog_title"],
                "type": "Blog Post",
                "url": f"/b/{post['category']}/{post['template_name']}/",
                "category": post["category"],
            }
        )

    # Get project suggestions (limit to 3)
    projects = search_projects(query=query)[:3]
    for project in projects:
        suggestions.append(
            {
                "title": project["name"],
                "type": "Project",
                "url": project.get("link", "#"),
                "external": bool(project.get("link")),
            }
        )

    # Get book suggestions (limit to 2)
    books = search_books(query=query)[:2]
    for book in books:
        author_text = f" by {book['author']}" if book.get("author") else ""
        suggestions.append({"title": f"{book['name']}{author_text}", "type": "Book", "url": "/#books"})

    return JsonResponse({"suggestions": suggestions[:10]})
