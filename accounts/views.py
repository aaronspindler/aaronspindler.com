from django.contrib import messages
from django.shortcuts import redirect


def signup_disabled(request):
    """
    View to handle signup attempts when registration is disabled.
    Redirects to login page with a message.
    """
    messages.info(
        request,
        "Registration is currently disabled. Please contact an administrator if you need an account.",
    )
    return redirect("account_login")
