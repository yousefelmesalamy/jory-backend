from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.cart.services import add_item, resolve_cart
from apps.core.exceptions import (
    CartItemUnavailableError,
    EmptyCartError,
    OutOfStockError,
    VoucherError,
)
from apps.orders.models import Order, OrderStatus, PaymentStatus
from apps.orders.services import generate_order_number, place_order
from apps.vouchers.models import DiscountType, Voucher, VoucherRedemption

pytestmark = pytest.mark.django_db

SHIPPING = override_settings(
    SHIPPING_FLAT_RATE=Decimal("30.00"), FREE_SHIPPING_THRESHOLD=Decimal("500.00")
)

ADDRESS = {
    "recipient_name": "Shopper One",
    "phone": "+201000000000",
    "country": "Egypt",
    "city": "Cairo",
    "area": "Maadi",
    "street_address": "12 Road 9",
    "postal_code": "11431",
    "notes": "Ring the bell twice.",
}


@pytest.fixture
def filled_cart(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 2)  # 2 x 250.00 == 500.00
    return cart


def test_order_numbers_are_prefixed_and_unique():
    numbers = {generate_order_number() for _ in range(50)}
    assert len(numbers) == 50
    assert all(number.startswith("JORY-") for number in numbers)


@SHIPPING
def test_placing_an_order_records_the_totals(user, filled_cart):
    order = place_order(user, filled_cart, ADDRESS)

    assert order.user == user
    assert order.status == OrderStatus.PENDING
    assert order.payment_status == PaymentStatus.UNPAID
    assert order.payment_method == "COD"
    assert order.subtotal == Decimal("500.00")
    assert order.discount_total == Decimal("0.00")
    assert order.shipping_cost == Decimal("0.00")  # free at the threshold
    assert order.grand_total == Decimal("500.00")


@SHIPPING
def test_placing_an_order_snapshots_the_address(user, filled_cart):
    order = place_order(user, filled_cart, ADDRESS)
    assert order.recipient_name == "Shopper One"
    assert order.city == "Cairo"
    assert order.notes == "Ring the bell twice."


@SHIPPING
def test_placing_an_order_snapshots_each_line(user, filled_cart, variant):
    order = place_order(user, filled_cart, ADDRESS)
    item = order.items.get()

    assert item.sku == variant.sku
    assert item.product_name == variant.product.name
    assert item.variant_label == variant.label
    assert item.unit_price == Decimal("250.00")
    assert item.quantity == 2
    assert item.line_total == Decimal("500.00")


@SHIPPING
def test_a_later_price_change_does_not_rewrite_the_order(user, filled_cart, variant):
    order = place_order(user, filled_cart, ADDRESS)

    variant.price = Decimal("999.00")
    variant.save()

    item = order.items.get()
    assert item.unit_price == Decimal("250.00")
    assert order.subtotal == Decimal("500.00")


@SHIPPING
def test_placing_an_order_decrements_stock(user, filled_cart, variant):
    before = variant.stock_quantity
    place_order(user, filled_cart, ADDRESS)
    variant.refresh_from_db()
    assert variant.stock_quantity == before - 2


@SHIPPING
def test_placing_an_order_empties_the_cart(user, filled_cart):
    place_order(user, filled_cart, ADDRESS)
    filled_cart.refresh_from_db()
    assert filled_cart.items.count() == 0
    assert filled_cart.voucher is None


def test_an_empty_cart_cannot_be_checked_out(user):
    cart, _ = resolve_cart(user=user, session_token=None)
    with pytest.raises(EmptyCartError):
        place_order(user, cart, ADDRESS)


@SHIPPING
def test_checkout_fails_when_stock_ran_out_after_the_cart_was_built(user, filled_cart, variant):
    variant.stock_quantity = 1
    variant.save()

    with pytest.raises(OutOfStockError):
        place_order(user, filled_cart, ADDRESS)

    assert Order.objects.count() == 0


@SHIPPING
def test_a_failed_checkout_leaves_stock_and_cart_untouched(user, filled_cart, variant):
    variant.stock_quantity = 1
    variant.save()

    with pytest.raises(OutOfStockError):
        place_order(user, filled_cart, ADDRESS)

    variant.refresh_from_db()
    assert variant.stock_quantity == 1
    assert filled_cart.items.count() == 1


@SHIPPING
def test_the_second_shopper_to_want_the_last_unit_is_refused(user, other_user, variant):
    # SQLite ignores select_for_update, so this runs sequentially. It proves the
    # in-transaction re-check, which is what actually protects the stock.
    variant.stock_quantity = 1
    variant.save()

    first_cart, _ = resolve_cart(user=user, session_token=None)
    add_item(first_cart, variant, 1)
    second_cart, _ = resolve_cart(user=other_user, session_token=None)
    add_item(second_cart, variant, 1)

    place_order(user, first_cart, ADDRESS)

    with pytest.raises(OutOfStockError):
        place_order(other_user, second_cart, ADDRESS)

    variant.refresh_from_db()
    assert variant.stock_quantity == 0
    assert Order.objects.count() == 1


@SHIPPING
def test_checkout_fails_when_a_variant_was_deactivated(user, filled_cart, variant):
    variant.is_active = False
    variant.save()
    with pytest.raises(CartItemUnavailableError):
        place_order(user, filled_cart, ADDRESS)


@SHIPPING
def test_a_voucher_is_applied_and_recorded(user, filled_cart):
    voucher = Voucher.objects.create(
        code="TEN", discount_type=DiscountType.PERCENT, value=Decimal("10")
    )
    filled_cart.voucher = voucher
    filled_cart.save()

    order = place_order(user, filled_cart, ADDRESS)

    assert order.discount_total == Decimal("50.00")
    assert order.grand_total == Decimal("450.00")
    assert order.voucher_code == "TEN"

    voucher.refresh_from_db()
    assert voucher.used_count == 1

    redemption = VoucherRedemption.objects.get(voucher=voucher, user=user)
    assert redemption.order == order
    assert redemption.discount_amount == Decimal("50.00")


@SHIPPING
def test_a_voucher_that_expired_between_apply_and_checkout_is_refused(user, filled_cart):
    voucher = Voucher.objects.create(
        code="GONE", discount_type=DiscountType.PERCENT, value=Decimal("10")
    )
    filled_cart.voucher = voucher
    filled_cart.save()

    voucher.valid_until = timezone.now() - timedelta(minutes=1)
    voucher.save()

    with pytest.raises(VoucherError):
        place_order(user, filled_cart, ADDRESS)
    assert Order.objects.count() == 0


@SHIPPING
def test_a_free_shipping_voucher_zeroes_the_shipping_on_the_order(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 1)  # 250.00, below the free-shipping threshold
    cart.voucher = Voucher.objects.create(code="SHIP", discount_type=DiscountType.FREE_SHIPPING)
    cart.save()

    order = place_order(user, cart, ADDRESS)
    assert order.shipping_cost == Decimal("0.00")
    assert order.discount_total == Decimal("0.00")
    assert order.grand_total == Decimal("250.00")
