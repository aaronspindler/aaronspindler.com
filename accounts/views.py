from django.contrib import messages
from django.shortcuts import redirect


def signup_disabled(request):
    messages.info(
        request,
        "Registration is currently disabled. Please contact an administrator if you need an account.",
    )
    return redirect("account_login")
