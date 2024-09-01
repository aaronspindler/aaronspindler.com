from django.contrib import admin
from .models import PageVisit

@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = ('page_name', 'ip_address', 'created_at')
    list_filter = ('page_name', 'created_at', 'ip_address')
    search_fields = ('page_name', 'ip_address')
    readonly_fields = ('created_at', 'ip_address', 'page_name')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

