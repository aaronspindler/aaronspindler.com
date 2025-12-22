from django.shortcuts import redirect, render

from accounts.models import CustomUser
from actions.models import Action
from utils.models import LambdaRegion, Notification, NotificationEmail, NotificationPhoneNumber
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages

from djstripe.models import Customer

from djstripe.models import APIKey

import stripe

from web.models import Endpoint


@login_required
def billing_portal(request):
    if request.method == 'POST':
        customer = request.user.get_customer()
        if customer:
            stripe.api_key = APIKey.objects.get(livemode=True).secret
            session = stripe.billing_portal.Session.create(
                customer=customer.id,
                return_url="https://actionsuptime.com",
            )
            return redirect(session.url)
    return None


def subscription_confirmation(request):
    stripe.api_key = APIKey.objects.get(livemode=True).secret
    session_id = request.GET.get("session_id")
    session = stripe.checkout.Session.retrieve(session_id)

    client_reference_id = session.client_reference_id
    if not client_reference_id:
        
        email = session.customer_details.email
        if email:
            user = CustomUser.objects.get(email=email)
            if not user:
                return render(request, "pages/subscription_confirmation.html", {"valid_user": False})
            
            customer = Customer.objects.filter(email=user.email, deleted=False).first()
            if customer:
                customer.subscriber = user
                customer.save()

    messages.success(request, f"You've successfully subscribed. Thanks for the support!")
    
    return render(request, "pages/subscription_confirmation.html", {"valid_user": True})


def home(request):
    data = {}
    if request.user.is_authenticated:
        data['notifications'] = Notification.objects.filter(action__owner=request.user).order_by('-created_at')[:5]
        data['notification_emails'] = NotificationEmail.objects.filter(user=request.user)
        data['notification_phone_numbers'] = NotificationPhoneNumber.objects.filter(user=request.user)
    else:
        data['regions'] = LambdaRegion.objects.filter(active=True).distinct('flag_code')
        try:
            data['actions'] = Action.objects.filter(pk__in=[10]).values_list('private_id', flat=True)
            data['endpoints'] = Endpoint.objects.filter(pk__in=[6, 2]).values_list('private_id', flat=True)
        except Action.DoesNotExist:
            pass
        
    return render(request, "pages/home.html", data)


@login_required
def notifications(request):
    notifications = Notification.objects.filter(action__owner=request.user).order_by('-created_at')
    paginator = Paginator(notifications, 30)  # Show 30 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    data = {
        'notifications': page_obj
    }
    return render(request, "pages/notifications.html", data)


def roadmap(request):
    return render(request, "pages/roadmap.html")


def support(request):
    return render(request, "pages/support.html")


def privacy_policy(request):
    return render(request, "pages/privacy_policy.html")


def terms_of_service(request):
    return render(request, "pages/terms_of_service.html")