from decimal import Decimal

import pytest
from django.test import override_settings

from apps.cart.services import add_item, resolve_cart
from apps.orders.models import OrderStatus
from apps.orders.services import place_order
from apps.reviews.models import Review
from apps.reviews.services import has_received_product, recalculate_product_rating

pytestmark = pytest.mark.django_db

SHIPPING = override_settings(
    SHIPPING_FLAT_RATE=Decimal("30.00"), FREE_SHIPPING_THRESHOLD=Decimal("500.00")
)

ADDRESS = {
    "recipient_name": "Shopper One", "phone": "+201000000000", "country": "Egypt",
    "city": "Cairo", "area": "Maadi", "street_address": "12 Road 9",
    "postal_code": "11431", "notes": "",
}


def buy(user, variant, quantity=1):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, quantity)
    return place_order(user, cart, ADDRESS)


def test_someone_who_never_ordered_has_not_received_it(user, product):
    assert has_received_product(user, product) is False


@SHIPPING
def test_a_pending_order_does_not_count_as_received(user, product, variant):
    buy(user, variant)
    assert has_received_product(user, product) is False


@SHIPPING
def test_a_shipped_order_does_not_count_as_received(user, product, variant):
    order = buy(user, variant)
    order.status = OrderStatus.SHIPPED
    order.save()
    assert has_received_product(user, product) is False


@SHIPPING
def test_a_delivered_order_counts_as_received(user, product, variant):
    order = buy(user, variant)
    order.status = OrderStatus.DELIVERED
    order.save()
    assert has_received_product(user, product) is True


@SHIPPING
def test_another_users_delivery_does_not_count(user, other_user, product, variant):
    order = buy(other_user, variant)
    order.status = OrderStatus.DELIVERED
    order.save()
    assert has_received_product(user, product) is False


@SHIPPING
def test_a_delivery_of_a_different_product_does_not_count(user, product, equipment_product, variant):
    order = buy(user, variant)
    order.status = OrderStatus.DELIVERED
    order.save()
    assert has_received_product(user, equipment_product) is False


def test_a_product_with_no_reviews_has_a_zero_rating(product):
    recalculate_product_rating(product)
    product.refresh_from_db()
    assert product.rating_avg == Decimal("0.00")
    assert product.rating_count == 0


def test_the_rating_is_the_mean_of_approved_reviews(user, other_user, product):
    Review.objects.create(product=product, user=user, rating=5)
    Review.objects.create(product=product, user=other_user, rating=4)

    product.refresh_from_db()
    assert product.rating_avg == Decimal("4.50")
    assert product.rating_count == 2


def test_the_average_rounds_to_two_places(user, other_user, staff_user, product):
    for reviewer, rating in ((user, 5), (other_user, 4), (staff_user, 4)):
        Review.objects.create(product=product, user=reviewer, rating=rating)

    product.refresh_from_db()
    assert product.rating_avg == Decimal("4.33")  # 13 / 3
    assert product.rating_count == 3


def test_unapproved_reviews_are_excluded(user, other_user, product):
    Review.objects.create(product=product, user=user, rating=5)
    Review.objects.create(product=product, user=other_user, rating=1, is_approved=False)

    product.refresh_from_db()
    assert product.rating_avg == Decimal("5.00")
    assert product.rating_count == 1


def test_editing_a_review_updates_the_rating(user, product):
    review = Review.objects.create(product=product, user=user, rating=5)
    review.rating = 2
    review.save()

    product.refresh_from_db()
    assert product.rating_avg == Decimal("2.00")


def test_deleting_a_review_updates_the_rating(user, other_user, product):
    Review.objects.create(product=product, user=user, rating=5)
    doomed = Review.objects.create(product=product, user=other_user, rating=1)
    doomed.delete()

    product.refresh_from_db()
    assert product.rating_avg == Decimal("5.00")
    assert product.rating_count == 1


def test_deleting_the_last_review_resets_the_rating(user, product):
    Review.objects.create(product=product, user=user, rating=5).delete()

    product.refresh_from_db()
    assert product.rating_avg == Decimal("0.00")
    assert product.rating_count == 0
