"""Views for the Omas Coffee website."""

from django.shortcuts import render


def home(request):
    """Display the Omas Coffee homepage."""
    return render(request, "omas/home.html")
