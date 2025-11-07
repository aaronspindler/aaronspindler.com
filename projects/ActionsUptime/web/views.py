import json
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from web.forms import EndpointForm
from web.models import Endpoint, EndpointStatus, EndpointStatusCheckRequest
from utils.models import NotificationEmail, NotificationPhoneNumber
from django.views.decorators.csrf import csrf_exempt

@login_required
def endpoints_home(request):
    data = {}
    endpoints = Endpoint.objects.filter(owner=request.user)
    data['endpoints'] = endpoints.values_list('private_id', flat=True)
    all_active = True
    for endpoint in endpoints:
        most_recent_status = endpoint.get_most_recent_status()
        if most_recent_status and most_recent_status.status != 'success':
            all_active = False
    data['all_active'] = all_active
    return render(request, "web/endpoints_home.html", data)

@csrf_exempt
def endpoint_status_webhook(request, key):
    if request.method == 'POST':
        endpoint_status_check_request = EndpointStatusCheckRequest.objects.filter(key=key, received_response=False)
        if not endpoint_status_check_request.exists():
            return HttpResponse('success') 
        endpoint_status_check_request = endpoint_status_check_request.first()
        response = request.body
        try:
            json_response = json.loads(response)
            previous_status = endpoint_status_check_request.endpoint.get_most_recent_status()
            current_status = EndpointStatus.objects.create(
                endpoint=endpoint_status_check_request.endpoint,
                region=endpoint_status_check_request.region,
                **json_response
            )
            endpoint_status_check_request.delete()
            if previous_status != None:
                if current_status.status != previous_status.status:
                    endpoint_status_check_request.endpoint.send_notification(current_status)
        except Exception as e:
            endpoint_status_check_request.response = response
            endpoint_status_check_request.received_response = True
            endpoint_status_check_request.save()
        return HttpResponse('success')
    return HttpResponseNotAllowed(["POST"])

@login_required
def add_endpoint(request):
    form = EndpointForm(request=request)
    if request.method == 'POST':
        form = EndpointForm(request.POST, request=request)
        if form.is_valid():
            endpoint = form.save(commit=False)
            endpoint.owner = request.user
            endpoint.save()
            form.save_m2m()
            messages.success(request, "Endpoint added successfully!")
            return redirect('endpoints_home')
        else:
            messages.error(request, "Please correct the errors below.")
    return render(request, "web/add_endpoint.html", {"form": form})

@login_required
def edit_endpoint(request, pk):
    endpoint = get_object_or_404(Endpoint, pk=pk, owner=request.user)
    form = EndpointForm(request=request, instance=endpoint)
    if request.method == 'POST':
        form = EndpointForm(request.POST, request=request, instance=endpoint)
        if form.is_valid():
            form.save()
            messages.success(request, "Endpoint updated successfully!")
            return redirect('endpoints_home')
        else:
            messages.error(request, "Please correct the errors below.")
    return render(request, "web/edit_endpoint.html", {"form": form, "endpoint": endpoint})

@login_required
def endpoints_status(request):
    endpoints = Endpoint.objects.filter(owner=request.user)
    all_active = True
    for endpoint in endpoints:
        most_recent_status = endpoint.get_most_recent_status()
        if most_recent_status and most_recent_status.status != 'success':
            all_active = False
    data = {
        "all_active": all_active
    }
    return JsonResponse(data)

def endpoint_details(request, private_id):
    endpoint = get_object_or_404(Endpoint, private_id=private_id)
    is_owner = request.user == endpoint.owner
    data = {
        "interval": endpoint.get_interval_display(),
        "is_owner": is_owner,
        "last_checked": endpoint.get_most_recent_status().get_iso_datetime() if endpoint.get_most_recent_status() else None,
        "last_status": endpoint.get_most_recent_status().status if endpoint.get_most_recent_status() else None,
        "success_rate": endpoint.get_percentage_success(),
        "average_latency": endpoint.get_average_latency(),
        "url": endpoint.url,
    }
    if is_owner:
        data['id'] = endpoint.id
    return JsonResponse(data)
    
def endpoint_status_timeline(request, private_id):
    endpoint = get_object_or_404(Endpoint, private_id=private_id)
    timeline_type = request.GET.get('timeline_type', 'daily')
    data = {
        "timeline": endpoint.get_status_timeline(timeline_type),
    }
    return JsonResponse(data)

def endpoint_latency_timeline(request, private_id):
    endpoint = get_object_or_404(Endpoint, private_id=private_id)
    timeline_type = request.GET.get('timeline_type', 'daily')
    data = {
        "timeline": endpoint.get_latency_timeline_by_region(timeline_type),
    }
    return JsonResponse(data)

@login_required
def delete_endpoint(request, pk):
    if request.method == 'POST':
        endpoint = get_object_or_404(Endpoint, pk=pk, owner=request.user)
        endpoint.delete()
        messages.success(request, "Endpoint deleted successfully!")
    return redirect('endpoints_home')

@login_required
def endpoint_available_notification_methods(request, pk):
    endpoint = get_object_or_404(Endpoint, pk=pk, owner=request.user)
    available_emails = NotificationEmail.objects.filter(user=request.user, verified=True)
    available_phone_numbers = NotificationPhoneNumber.objects.filter(user=request.user, verified=True)
    emails = []
    phone_numbers = []
    for email in available_emails:
        emails.append({
            "id": email.id,
            "email": email.email,
            "enabled": email in endpoint.notify_emails.all(),
        })
    for phone_number in available_phone_numbers:
        phone_numbers.append({
            "id": phone_number.id,
            "phone_number": phone_number.phone_number,
            "enabled": phone_number in endpoint.notify_phone_numbers.all(),
        })
    return JsonResponse({
        "emails": emails,
        "phone_numbers": phone_numbers,
    })

@login_required
def add_phone_notification(request, pk):
    if request.method == 'POST':
        endpoint = get_object_or_404(Endpoint, pk=pk, owner=request.user)
        phone_id = request.POST.get('phone_id')
        if phone_id:
            phone = get_object_or_404(NotificationPhoneNumber, pk=phone_id, user=request.user, verified=True)
            endpoint.notify_phone_numbers.add(phone)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})

@login_required
def remove_phone_notification(request, pk):
    if request.method == 'POST':
        endpoint = get_object_or_404(Endpoint, pk=pk, owner=request.user)
        phone_id = request.POST.get('phone_id')
        if phone_id:
            phone = get_object_or_404(NotificationPhoneNumber, pk=phone_id, user=request.user, verified=True)
            endpoint.notify_phone_numbers.remove(phone)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})

@login_required
def add_email_notification(request, pk):
    if request.method == 'POST':
        endpoint = get_object_or_404(Endpoint, pk=pk, owner=request.user)
        email_id = request.POST.get('email_id')
        if email_id:
            email = get_object_or_404(NotificationEmail, pk=email_id, user=request.user, verified=True)
            endpoint.notify_emails.add(email)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})

@login_required
def remove_email_notification(request, pk):
    if request.method == 'POST':
        endpoint = get_object_or_404(Endpoint, pk=pk, owner=request.user)
        email_id = request.POST.get('email_id')
        if email_id:
            email = get_object_or_404(NotificationEmail, pk=email_id, user=request.user, verified=True)
            endpoint.notify_emails.remove(email)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})


def endpoint_status(request, private_id):
    endpoint = get_object_or_404(Endpoint, private_id=private_id)
    endpoint_status = endpoint.most_recent_status()
    if endpoint_status and endpoint_status.status == 'success':
        return HttpResponse('success')
    else:
        raise Http404('failed')