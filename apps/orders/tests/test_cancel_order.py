from decimal import Decimal

import pytest
from django.test import override_settings

from apps.cart.services import add_item, resolve_cart
from apps.core.exceptions import OrderNotCancellableError
from apps.orders.models import OrderStatus
from apps.orders.services import cancel_order, place_order
from apps.vouchers.models import DiscountType, Voucher, VoucherRedemption

pytestmark = pytest.mark.django_db

SHIPPING = override_settings(SHIPPING_FLAT_RATE=Decimal("14.00"))

ADDRESS = {
    "recipient_name": "Shopper One",
    "phone": "+201000000000",
    "country": "Egypt",
    "city": "Cairo",
    "area": "Maadi",
    "street_address": "12 Road 9",
    "postal_code": "11431",
    "notes": "",
}


@pytest.fixture
def placed_order(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 2)
    return place_order(user, cart, ADDRESS)


@SHIPPING
def test_cancelling_marks_the_order_cancelled(placed_order):
    assert cancel_order(placed_order).status == OrderStatus.CANCELLED


@SHIPPING
def test_cancelling_restores_the_stock(placed_order, variant):
    variant.refresh_from_db()
    after_purchase = variant.stock_quantity

    cancel_order(placed_order)

    variant.refresh_from_db()
    assert variant.stock_quantity == after_purchase + 2


@SHIPPING
def test_cancelling_releases_the_voucher(user, variant):
    voucher = Voucher.objects.create(
        code="TEN", discount_type=DiscountType.PERCENT, value=Decimal("10")
    )
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 2)
    cart.voucher = voucher
    cart.save()
    order = place_order(user, cart, ADDRESS)

    voucher.refresh_from_db()
    assert voucher.used_count == 1

    cancel_order(order)

    voucher.refresh_from_db()
    assert voucher.used_count == 0
    assert not VoucherRedemption.objects.filter(order=order).exists()


@SHIPPING
def test_a_confirmed_order_cannot_be_cancelled(placed_order):
    placed_order.status = OrderStatus.CONFIRMED
    placed_order.save()
    with pytest.raises(OrderNotCancellableError):
        cancel_order(placed_order)


@SHIPPING
def test_an_already_cancelled_order_cannot_be_cancelled_again(placed_order, variant):
    cancel_order(placed_order)
    variant.refresh_from_db()
    restored = variant.stock_quantity

    with pytest.raises(OrderNotCancellableError):
        cancel_order(placed_order)

    # A second cancellation must not credit the stock twice.
    variant.refresh_from_db()
    assert variant.stock_quantity == restored


@SHIPPING
def test_cancelling_survives_a_deleted_variant(placed_order, variant):
    variant.delete()
    assert cancel_order(placed_order).status == OrderStatus.CANCELLED
