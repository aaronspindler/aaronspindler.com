from functools import wraps
from django.utils.decorators import method_decorator
from .models import PageVisit

def track_page_visit(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        PageVisit.objects.create(
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR')).split(',')[0].strip(),
            page_name=request.path
        )

        return view_func(request, *args, **kwargs)
    
    return wrapper

def track_page_visit_cbv(cls):
    return method_decorator(track_page_visit, name='dispatch')(cls)
