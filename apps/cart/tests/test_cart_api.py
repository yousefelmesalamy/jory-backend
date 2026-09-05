from decimal import Decimal

import pytest
from django.test import override_settings

from apps.cart.models import Cart
from apps.vouchers.models import DiscountType, Voucher

pytestmark = pytest.mark.django_db

SHIPPING = override_settings(
    SHIPPING_FLAT_RATE=Decimal("30.00"), FREE_SHIPPING_THRESHOLD=Decimal("500.00")
)


def add(client, variant, quantity=1, token=None):
    headers = {"HTTP_X_CART_TOKEN": token} if token else {}
    return client.post(
        "/api/cart/items/", {"variant": variant.id, "quantity": quantity}, format="json", **headers
    )


def test_a_guest_gets_an_empty_cart_and_a_token(api_client):
    response = api_client.get("/api/cart/")
    assert response.status_code == 200
    assert response.data["items"] == []
    assert response["X-Cart-Token"]


def test_a_guest_keeps_their_cart_across_requests(api_client, variant):
    token = api_client.get("/api/cart/")["X-Cart-Token"]
    add(api_client, variant, 2, token=token)

    response = api_client.get("/api/cart/", HTTP_X_CART_TOKEN=token)
    assert response.data["items"][0]["quantity"] == 2


def test_two_guests_do_not_share_a_cart(api_client, variant):
    token = api_client.get("/api/cart/")["X-Cart-Token"]
    add(api_client, variant, 2, token=token)

    other = api_client.get("/api/cart/")  # no token sent
    assert other.data["items"] == []
    assert other["X-Cart-Token"] != token


def test_an_authenticated_shopper_gets_their_own_cart(auth_client, user, variant):
    add(auth_client, variant, 1)
    assert Cart.objects.get(user=user).items.count() == 1


@SHIPPING
def test_the_cart_reports_server_computed_totals(auth_client, variant):
    add(auth_client, variant, 1)
    totals = auth_client.get("/api/cart/").data["totals"]
    assert totals == {
        "subtotal": "250.00",
        "discount_total": "0.00",
        "shipping_cost": "30.00",
        "grand_total": "280.00",
    }


def test_adding_the_same_variant_twice_increments_one_line(auth_client, variant):
    add(auth_client, variant, 1)
    add(auth_client, variant, 2)
    response = auth_client.get("/api/cart/")
    assert len(response.data["items"]) == 1
    assert response.data["items"][0]["quantity"] == 3


def test_adding_more_than_the_stock_is_refused(auth_client, variant):
    response = add(auth_client, variant, variant.stock_quantity + 1)
    assert response.status_code == 409
    assert response.data["error"]["code"] == "out_of_stock"


def test_adding_an_unknown_variant_is_refused(auth_client):
    response = auth_client.post(
        "/api/cart/items/", {"variant": 999999, "quantity": 1}, format="json"
    )
    assert response.status_code == 400


def test_updating_a_quantity(auth_client, variant):
    item_id = add(auth_client, variant, 1).data["id"]
    response = auth_client.patch(f"/api/cart/items/{item_id}/", {"quantity": 4}, format="json")
    assert response.status_code == 200
    assert response.data["quantity"] == 4


def test_updating_to_zero_removes_the_line(auth_client, variant):
    item_id = add(auth_client, variant, 1).data["id"]
    response = auth_client.patch(f"/api/cart/items/{item_id}/", {"quantity": 0}, format="json")
    assert response.status_code == 204
    assert auth_client.get("/api/cart/").data["items"] == []


def test_deleting_a_line(auth_client, variant):
    item_id = add(auth_client, variant, 1).data["id"]
    assert auth_client.delete(f"/api/cart/items/{item_id}/").status_code == 204
    assert auth_client.get("/api/cart/").data["items"] == []


def test_a_shopper_cannot_touch_another_cart_line(auth_client, api_client, variant):
    token = api_client.get("/api/cart/")["X-Cart-Token"]
    foreign_id = add(api_client, variant, 1, token=token).data["id"]

    assert auth_client.patch(
        f"/api/cart/items/{foreign_id}/", {"quantity": 9}, format="json"
    ).status_code == 404
    assert auth_client.delete(f"/api/cart/items/{foreign_id}/").status_code == 404


@SHIPPING
def test_applying_a_voucher(auth_client, variant):
    Voucher.objects.create(code="TEN", discount_type=DiscountType.PERCENT, value=Decimal("10"))
    add(auth_client, variant, 1)

    response = auth_client.post("/api/cart/apply-voucher/", {"code": "ten"}, format="json")
    assert response.status_code == 200
    assert response.data["voucher"]["code"] == "TEN"
    assert response.data["totals"]["discount_total"] == "25.00"


def test_applying_an_unknown_voucher_is_refused(auth_client, variant):
    add(auth_client, variant, 1)
    response = auth_client.post("/api/cart/apply-voucher/", {"code": "NOPE"}, format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "voucher_not_found"


def test_applying_a_voucher_below_its_minimum_is_refused(auth_client, variant):
    Voucher.objects.create(
        code="BIG",
        discount_type=DiscountType.PERCENT,
        value=Decimal("10"),
        min_order_total=Decimal("1000.00"),
    )
    add(auth_client, variant, 1)

    response = auth_client.post("/api/cart/apply-voucher/", {"code": "BIG"}, format="json")
    assert response.status_code == 400
    assert response.data["error"]["code"] == "voucher_min_order"


def test_removing_a_voucher(auth_client, variant):
    Voucher.objects.create(code="TEN", discount_type=DiscountType.PERCENT, value=Decimal("10"))
    add(auth_client, variant, 1)
    auth_client.post("/api/cart/apply-voucher/", {"code": "TEN"}, format="json")

    response = auth_client.delete("/api/cart/voucher/")
    assert response.status_code == 200
    assert response.data["voucher"] is None
    assert response.data["totals"]["discount_total"] == "0.00"


def test_merging_a_guest_cart_on_login(api_client, auth_client, variant, product):
    large = product.variants.get(sku="JORY-ETH-1000")
    token = api_client.get("/api/cart/")["X-Cart-Token"]
    add(api_client, variant, 1, token=token)
    add(api_client, large, 1, token=token)

    add(auth_client, variant, 2)

    response = auth_client.post("/api/cart/merge/", {"cart_token": token}, format="json")
    assert response.status_code == 200

    quantities = {item["variant"]["sku"]: item["quantity"] for item in response.data["items"]}
    assert quantities == {"JORY-ETH-250": 3, "JORY-ETH-1000": 1}
    assert not Cart.objects.filter(session_token=token).exists()


def test_merging_requires_authentication(api_client):
    token = api_client.get("/api/cart/")["X-Cart-Token"]
    assert api_client.post("/api/cart/merge/", {"cart_token": token}, format="json").status_code == 401


def test_merging_an_unknown_token_is_a_no_op(auth_client, variant):
    add(auth_client, variant, 1)
    response = auth_client.post(
        "/api/cart/merge/", {"cart_token": "11111111-1111-1111-1111-111111111111"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["items"][0]["quantity"] == 1
