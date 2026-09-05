from django.contrib import admin

from .models import Order, OrderItem

SNAPSHOT_FIELDS = [
    "order_number", "user", "subtotal", "discount_total", "shipping_cost",
    "grand_total", "voucher_code", "payment_method",
    "recipient_name", "phone", "country", "city", "area", "street_address", "postal_code",
]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # Snapshots: editing them would rewrite history.
    readonly_fields = [
        "variant", "product_name", "variant_label", "sku", "unit_price", "quantity", "line_total",
    ]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number", "user", "status", "payment_status", "grand_total", "city", "created_at",
    ]
    list_filter = ["status", "payment_status", "country", "city"]
    search_fields = ["order_number", "user__email", "recipient_name", "phone"]
    readonly_fields = SNAPSHOT_FIELDS
    inlines = [OrderItemInline]
    # Staff move an order through its lifecycle; they never rewrite its money.
    fields = SNAPSHOT_FIELDS + ["status", "payment_status", "notes"]
