from django.conf import settings
from django.db import models

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel
from apps.vouchers.models import Voucher


class Cart(TimeStampedModel):
    """A basket. Exactly one of `user` or `session_token` identifies it.

    Guest carts are keyed by a UUID the client echoes back in `X-Cart-Token`
    rather than by a Django session, because the API is stateless and consumed
    cross-origin.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.CASCADE, related_name="cart",
    )
    session_token = models.UUIDField(null=True, blank=True, unique=True, default=None)
    voucher = models.ForeignKey(
        Voucher, null=True, blank=True, on_delete=models.SET_NULL, related_name="carts"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, session_token__isnull=True)
                    | models.Q(user__isnull=True, session_token__isnull=False)
                ),
                name="cart_belongs_to_user_or_session",
            )
        ]

    def __str__(self):
        if self.user_id:
            return f"Cart for {self.user.email}"
        return f"Guest cart {self.session_token}"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["created_at"]
        unique_together = [("cart", "variant")]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=1), name="cart_item_quantity_positive"
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.variant.sku}"

    @property
    def line_total(self):
        return self.variant.price * self.quantity
