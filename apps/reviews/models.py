from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class Review(TimeStampedModel):
    """One shopper's verdict on one product they received."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=150, blank=True)
    body = models.TextField(blank=True)
    # Staff can hide abuse without destroying the record.
    is_approved = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("product", "user")]
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="review_rating_between_one_and_five",
            )
        ]

    def __str__(self):
        return f"{self.rating}/5 {self.product.name} by {self.user.email}"
