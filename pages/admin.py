"""
Admin configuration for pages app.

Provides admin interface for PageVisit model with geolocation capabilities
and batch processing actions.
"""
from django.contrib import admin
from django.shortcuts import redirect
from .models import PageVisit
from django.urls import path
import requests
import json

LOCAL_IPS = ['127.0.0.1', '10.0.2.2', '10.0.1.5']

@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    """Admin interface for PageVisit model with geolocation capabilities."""
    
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
        """
        Batch geolocate IP addresses that don't have geo_data.
        Uses ip-api.com batch API to process up to 100 IPs at a time.
        Excludes local IPs from geolocation.
        """
        ips = list(PageVisit.objects.filter(geo_data__isnull=True).values_list('ip_address', flat=True).distinct())
        ips = [ip for ip in ips if ip not in LOCAL_IPS]
        
        # Process IPs in chunks of 100 (API limit)
        for i in range(0, len(ips), 100):
            chunk = ips[i:i+100]
            formatted_chunk = json.dumps(chunk)
            try:
                response = requests.post('http://ip-api.com/batch', data=formatted_chunk)
                data = response.json()
                for response in data:
                    if response['status'] == 'success':
                        ip = response.pop('query')
                        response.pop('status')
                        PageVisit.objects.filter(ip_address=ip).update(geo_data=response)
            except Exception as e:
                self.message_user(request, f"Error geolocating chunk {i//100 + 1}: {e}", level='ERROR')
        return redirect('admin:pages_pagevisit_changelist')
    
    def clean_local_ips(self, request):
        """Remove all PageVisit records from local IP addresses."""
        PageVisit.objects.filter(ip_address__in=LOCAL_IPS).delete()
        self.message_user(request, "Local IP addresses cleaned.")
        return redirect('admin:pages_pagevisit_changelist')