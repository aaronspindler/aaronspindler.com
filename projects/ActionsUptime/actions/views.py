from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from actions.models import Action
from actions.tasks import check_action_status_badge
from utils.models import NotificationEmail, NotificationPhoneNumber


@login_required
def actions_home(request):
    data = {}
    data['actions'] = Action.objects.filter(owner=request.user).values_list('private_id', flat=True)
    return render(request, "actions/actions_home.html", data)


@login_required
def add_action(request):
    if request.method == 'POST':
        url = request.POST.get('url')
        is_private = request.POST.get('is_private') == 'on'
        if url:
            validator = URLValidator()
            try:
                validator(url)
            except ValidationError:
                messages.error(request, "Invalid URL. Please enter a valid GitHub Actions URL.")
                return redirect('actions_home')
            
            if 'github.com/' not in url or '/actions/workflows/' not in url or not (url.endswith('.yml') or url.endswith('.yaml')):
                messages.error(request, "Please enter a valid GitHub Actions workflow URL.")
                return redirect('actions_home')
            
            branch = request.POST.get('branch', 'main')
        
            action, created = Action.objects.get_or_create(owner=request.user, url=url, branch=branch)
            if created:
                if request.subscription_metadata.get('private_actions', False):
                    action.is_private = is_private
                    action.save()
                check_action_status_badge.delay(action.id)
                messages.success(request, "Action added successfully!")
            else:
                messages.info(request, "Action already exists!")
    return redirect('actions_home')


@login_required
def delete_action(request, pk):
    if request.method == 'POST':
        action = get_object_or_404(Action, pk=pk, owner=request.user)
        action.delete()
        messages.success(request, "Action deleted successfully!")
    return redirect('actions_home')


@login_required
def action_available_notification_methods(request, pk):
    action = get_object_or_404(Action, pk=pk, owner=request.user)
    available_emails = NotificationEmail.objects.filter(user=request.user, verified=True)
    available_phone_numbers = NotificationPhoneNumber.objects.filter(user=request.user, verified=True)
    emails = []
    phone_numbers = []
    for email in available_emails:
        emails.append({
            "id": email.id,
            "email": email.email,
            "enabled": email in action.notify_emails.all(),
        })
    for phone_number in available_phone_numbers:
        phone_numbers.append({
            "id": phone_number.id,
            "phone_number": phone_number.phone_number,
            "enabled": phone_number in action.notify_phone_numbers.all(),
        })
    return JsonResponse({
        "emails": emails,
        "phone_numbers": phone_numbers,
    })


@login_required
def add_phone_notification(request, pk):
    if request.method == 'POST':
        action = get_object_or_404(Action, pk=pk, owner=request.user)
        phone_id = request.POST.get('phone_id')
        if phone_id:
            phone = get_object_or_404(NotificationPhoneNumber, pk=phone_id, user=request.user, verified=True)
            action.notify_phone_numbers.add(phone)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})


@login_required
def remove_phone_notification(request, pk):
    if request.method == 'POST':
        action = get_object_or_404(Action, pk=pk, owner=request.user)
        phone_id = request.POST.get('phone_id')
        if phone_id:
            phone = get_object_or_404(NotificationPhoneNumber, pk=phone_id, user=request.user, verified=True)
            action.notify_phone_numbers.remove(phone)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})


@login_required
def add_email_notification(request, pk):
    if request.method == 'POST':
        action = get_object_or_404(Action, pk=pk, owner=request.user)
        email_id = request.POST.get('email_id')
        if email_id:
            email = get_object_or_404(NotificationEmail, pk=email_id, user=request.user, verified=True)
            action.notify_emails.add(email)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})


@login_required
def remove_email_notification(request, pk):
    if request.method == 'POST':
        action = get_object_or_404(Action, pk=pk, owner=request.user)
        email_id = request.POST.get('email_id')
        if email_id:
            email = get_object_or_404(NotificationEmail, pk=email_id, user=request.user, verified=True)
            action.notify_emails.remove(email)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})


@login_required
def actions_status(request):
    actions = Action.objects.filter(owner=request.user)
    all_active = True
    for action in actions:
        most_recent_status = action.most_recent_status()
        if most_recent_status and most_recent_status.status != 'success':
            all_active = False
    data = {
        "all_active": all_active
    }
    return JsonResponse(data)


def action_status(request, private_id):
    action = get_object_or_404(Action, private_id=private_id)
    action_status = action.most_recent_status()
    if action_status and action_status.status == 'success':
        return HttpResponse('success')
    else:
        raise Http404('failed')
    

def action_details(request, private_id):
    action = get_object_or_404(Action, private_id=private_id)
    is_owner = request.user == action.owner
    data = {
        "interval": action.get_interval_display(),
        "is_owner": is_owner,
        "repo_name": action.repo_name,
        "branch": action.branch,
        "pretty_name": action.pretty_name,
        "last_checked": action.most_recent_status().get_iso_datetime() if action.most_recent_status() else None,
        "last_status": action.most_recent_status().status if action.most_recent_status() else None,
        "success_rate": action.get_percentage_success(),
        "url": action.url,
        "public_url": action.get_public_status_url(),
    }
    if is_owner:
        data['id'] = action.id
    return JsonResponse(data)
    

def action_graph(request, private_id):
    action = get_object_or_404(Action, private_id=private_id)
    timeline_type = request.GET.get('timeline_type', 'daily')
    data = {
        "timeline": action.get_action_status_timeline(timeline_type),
    }
    return JsonResponse(data)