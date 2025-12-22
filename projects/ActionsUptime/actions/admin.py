from django.contrib import admin

from .models import Action, ActionStatus


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('url', 'owner', 'interval', 'created_at', 'updated_at')
    list_filter = ('owner', 'created_at', 'updated_at', 'interval')
    search_fields = ('url', 'owner__email')
    readonly_fields = ('created_at', 'updated_at')
    

@admin.register(ActionStatus)
class ActionStatusAdmin(admin.ModelAdmin):
    list_display = ('action', 'status', 'created_at', 'updated_at', 'checker')
    list_filter = ('action', 'status', 'created_at', 'updated_at', 'checker')
    search_fields = ('action__url', 'action__owner__email')
    readonly_fields = ('created_at', 'updated_at')
