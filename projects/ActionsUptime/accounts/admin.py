from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['email', 'username', 'paid']
    list_filter = ['paid']
    fieldsets = UserAdmin.fieldsets + (
        ('Payment Information', {'fields': ('paid',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Payment Information', {'fields': ('paid',)}),
    )