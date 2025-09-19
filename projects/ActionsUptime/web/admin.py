from django.contrib import admin

from utils.models import LambdaRegion

from .models import Endpoint, EndpointStatus, EndpointStatusCheckRequest

@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ('url', 'owner', 'interval', 'http_method')
    list_filter = ('interval', 'http_method', 'check_ssl', 'check_ssl', 'check_domain_expiration', 'follow_redirects', 'auth_type')
    search_fields = ('url', 'owner__email')
    readonly_fields = ('created_at', 'updated_at', 'private_id')
    filter_horizontal = ('notify_emails', 'notify_phone_numbers', 'up_status_codes')

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "enabled_regions":
            kwargs["queryset"] = LambdaRegion.objects.filter(active=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

@admin.register(EndpointStatus)
class EndpointStatusAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'status', 'status_code', 'region', 'check_start_time', 'duration_ms', 'ssl_valid', 'ssl_expiration', 'domain_expiration')
    list_filter = ('status', 'status_code', 'ssl_valid', 'endpoint__url', 'region')
    search_fields = ('endpoint__url',)
    readonly_fields = ('created_at', 'updated_at', 'check_start_time', 'check_end_time', 'duration_ms', 'ssl_valid', 'ssl_expiration', 'domain_expiration')


@admin.register(EndpointStatusCheckRequest)
class EndpointStatusCheckRequestAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'endpoint', 'region', 'received_response')
    list_filter = ('region', 'received_response')
    search_fields = ('endpoint__url', 'key')
    readonly_fields = ('created_at',)