from decimal import Decimal

import pytest
from django.test import override_settings

from apps.cart.services import add_item, resolve_cart
from apps.orders.models import OrderStatus
from apps.orders.services import place_order
from apps.reviews.models import Review

pytestmark = pytest.mark.django_db

SHIPPING = override_settings(SHIPPING_FLAT_RATE=Decimal("14.00"))

ADDRESS = {
    "recipient_name": "Shopper One", "phone": "+201000000000", "country": "Egypt",
    "city": "Cairo", "area": "Maadi", "street_address": "12 Road 9",
    "postal_code": "11431", "notes": "",
}

URL = "/api/products/ethiopia-yirgacheffe/reviews/"
PAYLOAD = {"rating": 5, "title": "Excellent", "body": "Jasmine and lemon, just as described."}


def deliver(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 1)
    order = place_order(user, cart, ADDRESS)
    order.status = OrderStatus.DELIVERED
    order.save()
    return order


@SHIPPING
def test_a_verified_purchaser_can_review(auth_client, user, product, variant):
    deliver(user, variant)
    response = auth_client.post(URL, PAYLOAD, format="json")

    assert response.status_code == 201
    assert response.data["rating"] == 5
    assert response.data["user"]["full_name"] == "Shopper One"
    assert Review.objects.filter(product=product, user=user).exists()


def test_someone_who_never_bought_it_cannot_review(auth_client, product):
    response = auth_client.post(URL, PAYLOAD, format="json")
    assert response.status_code == 403
    assert response.data["error"]["code"] == "review_not_permitted"


@SHIPPING
def test_an_undelivered_order_does_not_grant_the_right_to_review(auth_client, user, product, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 1)
    place_order(user, cart, ADDRESS)  # stays PENDING

    assert auth_client.post(URL, PAYLOAD, format="json").status_code == 403


def test_reviewing_requires_authentication(api_client, product):
    assert api_client.post(URL, PAYLOAD, format="json").status_code == 401


@SHIPPING
def test_a_second_review_of_the_same_product_is_refused(auth_client, user, product, variant):
    deliver(user, variant)
    auth_client.post(URL, PAYLOAD, format="json")

    response = auth_client.post(URL, PAYLOAD, format="json")
    assert response.status_code == 400


@SHIPPING
@pytest.mark.parametrize("rating", [0, 6])
def test_an_out_of_range_rating_is_refused(auth_client, user, product, variant, rating):
    deliver(user, variant)
    response = auth_client.post(URL, dict(PAYLOAD, rating=rating), format="json")
    assert response.status_code == 400


@SHIPPING
def test_posting_a_review_updates_the_product_rating(auth_client, user, product, variant):
    deliver(user, variant)
    auth_client.post(URL, dict(PAYLOAD, rating=4), format="json")

    detail = auth_client.get("/api/products/ethiopia-yirgacheffe/").data
    assert detail["rating_avg"] == "4.00"
    assert detail["rating_count"] == 1


def test_the_review_list_is_public(api_client, user, product):
    Review.objects.create(product=product, user=user, rating=4, title="Good")
    response = api_client.get(URL)

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Good"


def test_the_list_hides_unapproved_reviews(api_client, user, other_user, product):
    Review.objects.create(product=product, user=user, rating=4)
    Review.objects.create(product=product, user=other_user, rating=1, is_approved=False)

    assert api_client.get(URL).data["count"] == 1


def test_the_list_only_covers_the_named_product(api_client, user, product, equipment_product):
    Review.objects.create(product=equipment_product, user=user, rating=3)
    assert api_client.get(URL).data["count"] == 0


def test_an_unknown_product_slug_is_a_404(api_client):
    assert api_client.get("/api/products/nope/reviews/").status_code == 404


def test_an_author_can_edit_their_review(auth_client, user, product):
    review = Review.objects.create(product=product, user=user, rating=2, title="Meh")
    response = auth_client.patch(
        f"/api/reviews/{review.id}/", {"rating": 5, "title": "Grew on me"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["rating"] == 5

    product.refresh_from_db()
    assert product.rating_avg == Decimal("5.00")


def test_an_author_can_delete_their_review(auth_client, user, product):
    review = Review.objects.create(product=product, user=user, rating=2)
    assert auth_client.delete(f"/api/reviews/{review.id}/").status_code == 204

    product.refresh_from_db()
    assert product.rating_count == 0


def test_nobody_can_edit_someone_elses_review(auth_client, other_user, product):
    foreign = Review.objects.create(product=product, user=other_user, rating=1)

    assert auth_client.patch(
        f"/api/reviews/{foreign.id}/", {"rating": 5}, format="json"
    ).status_code == 404
    assert auth_client.delete(f"/api/reviews/{foreign.id}/").status_code == 404


def test_the_product_cannot_be_switched_when_editing(auth_client, user, product, equipment_product):
    review = Review.objects.create(product=product, user=user, rating=3)
    auth_client.patch(
        f"/api/reviews/{review.id}/", {"product": equipment_product.id}, format="json"
    )

    review.refresh_from_db()
    assert review.product == product
