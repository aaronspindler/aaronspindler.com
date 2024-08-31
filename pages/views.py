from django.views.generic import TemplateView

from .decorators import track_page_visit_cbv

@track_page_visit_cbv
class HomePageView(TemplateView):
    template_name = "pages/home.html"
