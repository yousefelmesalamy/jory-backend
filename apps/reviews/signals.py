from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review
from .services import recalculate_product_rating


# Signals rather than explicit calls in the view: a review edited or removed in
# the Django admin must update the product's rating too.
@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def update_product_rating(sender, instance, **kwargs):
    recalculate_product_rating(instance.product)
