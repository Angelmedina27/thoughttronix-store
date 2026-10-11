from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import AdminSignInForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ("ThoughtTronix", {"fields": ("job_title",)}),
    )
    list_display = ("username", "email", "job_title", "is_staff")


# The admin login gets the storefront's failed-attempt lockout.
admin.site.login_form = AdminSignInForm
