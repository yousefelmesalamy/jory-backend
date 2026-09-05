from django.conf import settings
from django.db import models

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel

PAYMENT_METHOD_COD = "COD"


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    SHIPPED = "SHIPPED", "Shipped"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentStatus(models.TextChoices):
    UNPAID = "UNPAID", "Unpaid"
    PAID = "PAID", "Paid"


class Order(TimeStampedModel):
    """An immutable record of a completed purchase.

    Everything is snapshotted at checkout: a later price change, product rename
    or catalog deletion must never rewrite an order's history.
    """

    order_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )

    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    payment_method = models.CharField(max_length=10, default=PAYMENT_METHOD_COD)
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )

    # Shipping snapshot — deliberately copied, not a FK to Address, so editing
    # or deleting the address later cannot change where an order was sent.
    recipient_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100, blank=True)
    street_address = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    voucher_code = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    @property
    def can_be_cancelled(self):
        return self.status == OrderStatus.PENDING


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant, null=True, blank=True, on_delete=models.SET_NULL, related_name="order_items"
    )

    product_name = models.CharField(max_length=200)
    variant_label = models.CharField(max_length=120)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.sku}"
