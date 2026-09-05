from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, Count

from apps.orders.models import OrderItem, OrderStatus

RATING_PLACES = Decimal("0.01")


def has_received_product(user, product):
    """True when this user has a DELIVERED order containing this product.

    Matches through `OrderItem.variant`, which is SET_NULL: if the variant was
    deleted from the catalog the right to review goes with it. Matching on the
    snapshotted SKU instead would hand reviewing rights to whoever a reissued
    SKU later belongs to.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return OrderItem.objects.filter(
        order__user=user,
        order__status=OrderStatus.DELIVERED,
        variant__product=product,
    ).exists()


def recalculate_product_rating(product):
    """Recompute the product's cached rating from its approved reviews."""
    stats = product.reviews.filter(is_approved=True).aggregate(
        average=Avg("rating"), total=Count("id")
    )
    average = stats["average"] or 0
    product.rating_avg = Decimal(str(average)).quantize(RATING_PLACES, rounding=ROUND_HALF_UP)
    product.rating_count = stats["total"]
    product.save(update_fields=["rating_avg", "rating_count", "updated_at"])
    return product
