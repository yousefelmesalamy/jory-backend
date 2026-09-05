from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "session_token", "voucher", "updated_at"]
    search_fields = ["user__email", "session_token"]
    inlines = [CartItemInline]
