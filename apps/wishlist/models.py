from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class WishlistItem(TimeStampedModel):
    """A product a shopper saved for later."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("user", "product")]

    def __str__(self):
        return f"{self.user.email} saved {self.product.name}"
