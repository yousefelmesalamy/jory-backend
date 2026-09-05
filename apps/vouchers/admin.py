from django.contrib import admin

from .models import Voucher, VoucherRedemption


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = [
        "code", "discount_type", "value", "min_order_total",
        "used_count", "usage_limit", "is_active", "valid_until",
    ]
    list_filter = ["discount_type", "is_active"]
    search_fields = ["code", "description"]
    readonly_fields = ["used_count"]  # incremented by checkout, not by hand


@admin.register(VoucherRedemption)
class VoucherRedemptionAdmin(admin.ModelAdmin):
    list_display = ["voucher", "user", "discount_amount", "created_at"]
    search_fields = ["voucher__code", "user__email"]
