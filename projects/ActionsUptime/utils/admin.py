from django.contrib import admin

from django.contrib import admin
from .models import Email, LambdaRegion, Notification, NotificationConfig, TextMessage, NotificationEmail, NotificationPhoneNumber, HTTPStatusCode


@admin.register(NotificationConfig)
class NotificationConfigAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'updated_at', 'emails_enabled', 'text_messages_enabled')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('action', 'action_status', 'type', 'created_at')
    list_filter = ('type',)
    search_fields = ('action__url', 'action_status__status', 'message')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'template', 'subject', 'created', 'sent')
    list_filter = ('template', 'sent')
    search_fields = ('recipient', 'subject')
    readonly_fields = ('created', 'updated', 'sent')


@admin.register(TextMessage)
class TextMessageAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'created', 'sent')
    list_filter = ('sent',)
    search_fields = ('recipient', 'message')
    readonly_fields = ('created', 'updated', 'sent')


@admin.register(NotificationEmail)
class NotificationEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'created_at', 'verified', 'verified_at')
    list_filter = ('verified',)
    search_fields = ('email', 'user__email')
    readonly_fields = ('created_at', 'verified_at', 'verification_code')


@admin.register(NotificationPhoneNumber)
class NotificationPhoneNumberAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user', 'created_at', 'verified', 'verified_at')
    list_filter = ('verified',)
    search_fields = ('phone_number', 'user__email')
    readonly_fields = ('created_at', 'verified_at', 'verification_code')


@admin.register(HTTPStatusCode)
class HTTPStatusCodeAdmin(admin.ModelAdmin):
    list_display = ('code','description')
    search_fields = ('code', 'description')
    

@admin.register(LambdaRegion)
class LambdaRegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'active', 'flag')
    search_fields = ('name', 'code')

    def flag(self, obj):
        return obj.get_flag()

    flag.allow_tags = True
