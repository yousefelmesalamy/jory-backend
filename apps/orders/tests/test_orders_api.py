from decimal import Decimal

import pytest
from django.test import override_settings

from apps.accounts.models import Address
from apps.orders.models import Order, OrderStatus
from apps.vouchers.models import DiscountType, Voucher

pytestmark = pytest.mark.django_db

SHIPPING = override_settings(
    SHIPPING_FLAT_RATE=Decimal("30.00"), FREE_SHIPPING_THRESHOLD=Decimal("500.00")
)

INLINE_ADDRESS = {
    "recipient_name": "Shopper One",
    "phone": "+201000000000",
    "country": "Egypt",
    "city": "Cairo",
    "area": "Maadi",
    "street_address": "12 Road 9",
    "postal_code": "11431",
}


def fill_cart(client, variant, quantity=2):
    return client.post(
        "/api/cart/items/", {"variant": variant.id, "quantity": quantity}, format="json"
    )


def foreign_order(other_user, number):
    return Order.objects.create(
        order_number=number, user=other_user, subtotal=Decimal("10.00"),
        grand_total=Decimal("10.00"), recipient_name="Other", phone="x",
        country="Egypt", city="Giza", street_address="1 Nowhere",
    )


@SHIPPING
def test_checkout_creates_an_order(auth_client, variant):
    fill_cart(auth_client, variant)
    response = auth_client.post("/api/orders/", INLINE_ADDRESS, format="json")

    assert response.status_code == 201
    assert response.data["order_number"].startswith("JORY-")
    assert response.data["status"] == "PENDING"
    assert response.data["payment_method"] == "COD"
    assert response.data["grand_total"] == "500.00"
    assert response.data["placed_at"]
    assert len(response.data["items"]) == 1


@SHIPPING
def test_checkout_accepts_a_saved_address(auth_client, user, variant):
    address = Address.objects.create(
        user=user, full_name="Saved Name", phone="+201234567890", country="Egypt",
        city="Alexandria", area="Smouha", street_address="5 Corniche", postal_code="21500",
    )
    fill_cart(auth_client, variant)

    response = auth_client.post("/api/orders/", {"address_id": address.id}, format="json")
    assert response.status_code == 201
    assert response.data["city"] == "Alexandria"
    assert response.data["recipient_name"] == "Saved Name"


def test_checkout_rejects_another_users_address(auth_client, other_user, variant):
    foreign = Address.objects.create(
        user=other_user, full_name="Not Mine", phone="+20100", country="Egypt",
        city="Giza", street_address="1 Nowhere",
    )
    fill_cart(auth_client, variant)

    response = auth_client.post("/api/orders/", {"address_id": foreign.id}, format="json")
    assert response.status_code == 400


def test_checkout_requires_an_address(auth_client, variant):
    fill_cart(auth_client, variant)
    assert auth_client.post("/api/orders/", {}, format="json").status_code == 400


def test_checkout_requires_authentication(api_client, variant):
    assert api_client.post("/api/orders/", INLINE_ADDRESS, format="json").status_code == 401


def test_checkout_with_an_empty_cart_is_refused(auth_client):
    response = auth_client.post("/api/orders/", INLINE_ADDRESS, format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "empty_cart"


@SHIPPING
def test_checkout_is_refused_when_stock_ran_out(auth_client, variant):
    fill_cart(auth_client, variant)
    variant.stock_quantity = 1
    variant.save()

    response = auth_client.post("/api/orders/", INLINE_ADDRESS, format="json")
    assert response.status_code == 409
    assert response.data["error"]["code"] == "out_of_stock"


@SHIPPING
def test_the_client_cannot_dictate_the_total(auth_client, variant):
    fill_cart(auth_client, variant)
    response = auth_client.post(
        "/api/orders/", dict(INLINE_ADDRESS, grand_total="1.00", subtotal="1.00"), format="json"
    )
    assert response.status_code == 201
    assert response.data["grand_total"] == "500.00"


@SHIPPING
def test_checkout_empties_the_cart(auth_client, variant):
    fill_cart(auth_client, variant)
    auth_client.post("/api/orders/", INLINE_ADDRESS, format="json")
    assert auth_client.get("/api/cart/").data["items"] == []


@SHIPPING
def test_a_voucher_carries_onto_the_order(auth_client, variant):
    Voucher.objects.create(code="TEN", discount_type=DiscountType.PERCENT, value=Decimal("10"))
    fill_cart(auth_client, variant)
    auth_client.post("/api/cart/apply-voucher/", {"code": "TEN"}, format="json")

    response = auth_client.post("/api/orders/", INLINE_ADDRESS, format="json")
    assert response.data["voucher_code"] == "TEN"
    assert response.data["discount_total"] == "50.00"
    assert response.data["grand_total"] == "450.00"


@SHIPPING
def test_the_history_lists_only_my_orders(auth_client, other_user, variant):
    fill_cart(auth_client, variant)
    auth_client.post("/api/orders/", INLINE_ADDRESS, format="json")
    foreign_order(other_user, "JORY-OTHER01")

    assert auth_client.get("/api/orders/").data["count"] == 1


@SHIPPING
def test_retrieving_an_order_by_number(auth_client, variant):
    fill_cart(auth_client, variant)
    number = auth_client.post("/api/orders/", INLINE_ADDRESS, format="json").data["order_number"]

    response = auth_client.get(f"/api/orders/{number}/")
    assert response.status_code == 200
    assert response.data["order_number"] == number


def test_another_users_order_is_not_visible(auth_client, other_user):
    foreign = foreign_order(other_user, "JORY-OTHER02")
    assert auth_client.get(f"/api/orders/{foreign.order_number}/").status_code == 404


@SHIPPING
def test_cancelling_my_pending_order(auth_client, variant):
    fill_cart(auth_client, variant)
    number = auth_client.post("/api/orders/", INLINE_ADDRESS, format="json").data["order_number"]

    response = auth_client.post(f"/api/orders/{number}/cancel/")
    assert response.status_code == 200
    assert response.data["status"] == "CANCELLED"

    variant.refresh_from_db()
    assert variant.stock_quantity == 10  # restored to the fixture's level


@SHIPPING
def test_cancelling_a_shipped_order_is_refused(auth_client, variant):
    fill_cart(auth_client, variant)
    number = auth_client.post("/api/orders/", INLINE_ADDRESS, format="json").data["order_number"]

    order = Order.objects.get(order_number=number)
    order.status = OrderStatus.SHIPPED
    order.save()

    response = auth_client.post(f"/api/orders/{number}/cancel/")
    assert response.status_code == 409
    assert response.data["error"]["code"] == "order_not_cancellable"


def test_cancelling_another_users_order_is_not_possible(auth_client, other_user):
    foreign = foreign_order(other_user, "JORY-OTHER03")
    assert auth_client.post(f"/api/orders/{foreign.order_number}/cancel/").status_code == 404


@SHIPPING
def test_orders_are_read_only_over_rest(auth_client, variant):
    fill_cart(auth_client, variant)
    number = auth_client.post("/api/orders/", INLINE_ADDRESS, format="json").data["order_number"]
    assert auth_client.delete(f"/api/orders/{number}/").status_code == 405
