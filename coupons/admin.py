from django.contrib import admin

from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "kind",
        "value",
        "product",
        "is_active",
        "starts_on",
        "ends_on",
    )
    list_filter = ("is_active", "kind")
    search_fields = ("code", "description")
