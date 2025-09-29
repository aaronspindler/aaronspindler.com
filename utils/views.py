from django.utils import timezone
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
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