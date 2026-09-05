from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class DiscountType(models.TextChoices):
    PERCENT = "PERCENT", "Percentage off the subtotal"
    FIXED = "FIXED", "Fixed amount off the subtotal"
    FREE_SHIPPING = "FREE_SHIPPING", "Free shipping"


class Voucher(TimeStampedModel):
    """A discount code. `usage_limit` and `per_user_limit` are null for unlimited."""

    code = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_order_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class VoucherRedemption(TimeStampedModel):
    """One use of a voucher, written at checkout and released on cancellation."""

    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name="redemptions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="voucher_redemptions"
    )
    order = models.ForeignKey(
        "orders.Order", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="redemptions",
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.voucher.code} by {self.user.email}"
