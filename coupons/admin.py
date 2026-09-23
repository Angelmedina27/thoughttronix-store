from django.contrib import admin

from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "percent_off", "product", "is_active", "expires_at")
    list_filter = ("is_active", "product")
    search_fields = ("code",)
