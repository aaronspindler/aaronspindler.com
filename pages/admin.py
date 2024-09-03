from django.contrib import admin
from django.shortcuts import redirect
from .models import PageVisit
from django.urls import path

@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = ('page_name', 'ip_address', 'created_at', 'geo_data')
    list_filter = ('page_name', 'created_at', 'ip_address')
    search_fields = ('page_name', 'ip_address', 'geo_data')
    readonly_fields = ('created_at', 'ip_address', 'page_name', 'geo_data')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "geolocate_ips/",
                self.admin_site.admin_view(
                    self.geolocate_ips,
                ),
                name="pages_pagevisit_geolocate_ips",
            ),
            path(
                "clean_local_ips/",
                self.admin_site.admin_view(
                    self.clean_local_ips,
                ),
                name="pages_pagevisit_clean_local_ips",
            ),
            
        ]
        return custom_urls + urls

    def geolocate_ips(self, request):
        from django.core.management import call_command
        call_command('geolocate_ips')
        self.message_user(request, "Geolocation process initiated.")
        return redirect('admin:pages_pagevisit_changelist')
    
    def clean_local_ips(self, request):
        from .models import PageVisit
        PageVisit.objects.filter(ip_address__in=['127.0.0.1', '10.0.2.2', '10.0.1.5']).delete()
        self.message_user(request, "Local IP addresses cleaned.")
        return redirect('admin:pages_pagevisit_changelist')


