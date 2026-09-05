import uuid
from decimal import Decimal

import pytest
from django.test import override_settings

from apps.cart.models import Cart
from apps.cart.services import (
    add_item,
    calculate_totals,
    merge_carts,
    resolve_cart,
    set_quantity,
)
from apps.core.exceptions import CartItemUnavailableError, OutOfStockError
from apps.vouchers.models import DiscountType, Voucher

pytestmark = pytest.mark.django_db

# 30.00 flat, free over 500.00 — matches .env; pinned so the tests do not drift
# if the shop changes its rates.
SHIPPING = override_settings(
    SHIPPING_FLAT_RATE=Decimal("30.00"), FREE_SHIPPING_THRESHOLD=Decimal("500.00")
)


def test_resolve_creates_a_cart_for_a_new_user(user):
    cart, created = resolve_cart(user=user, session_token=None)
    assert created is True
    assert cart.user == user


def test_resolve_returns_the_same_cart_for_a_returning_user(user):
    first, _ = resolve_cart(user=user, session_token=None)
    second, created = resolve_cart(user=user, session_token=None)
    assert second == first
    assert created is False


def test_resolve_creates_a_guest_cart_with_a_token():
    cart, created = resolve_cart(user=None, session_token=None)
    assert created is True
    assert cart.session_token is not None
    assert cart.user is None


def test_resolve_returns_the_guest_cart_matching_a_token():
    first, _ = resolve_cart(user=None, session_token=None)
    second, created = resolve_cart(user=None, session_token=str(first.session_token))
    assert second == first
    assert created is False


def test_an_unknown_or_malformed_token_starts_a_fresh_cart():
    stranger, _ = resolve_cart(user=None, session_token=str(uuid.uuid4()))
    assert stranger.session_token is not None

    garbage, _ = resolve_cart(user=None, session_token="not-a-uuid")
    assert garbage.session_token is not None


def test_adding_an_item(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    item = add_item(cart, variant, 2)
    assert item.quantity == 2
    assert cart.items.count() == 1


def test_adding_the_same_variant_increments_instead_of_duplicating(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 2)
    item = add_item(cart, variant, 3)
    assert item.quantity == 5
    assert cart.items.count() == 1


def test_adding_more_than_the_stock_is_rejected(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    with pytest.raises(OutOfStockError):
        add_item(cart, variant, variant.stock_quantity + 1)


def test_incrementing_past_the_stock_is_rejected(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, variant.stock_quantity)
    with pytest.raises(OutOfStockError):
        add_item(cart, variant, 1)


def test_adding_an_inactive_variant_is_rejected(user, variant):
    variant.is_active = False
    variant.save()
    cart, _ = resolve_cart(user=user, session_token=None)
    with pytest.raises(CartItemUnavailableError):
        add_item(cart, variant, 1)


def test_setting_a_quantity(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    item = add_item(cart, variant, 1)
    assert set_quantity(item, 4).quantity == 4


def test_setting_a_quantity_to_zero_removes_the_line(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    item = add_item(cart, variant, 1)
    assert set_quantity(item, 0) is None
    assert cart.items.count() == 0


def test_setting_a_quantity_above_the_stock_is_rejected(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    item = add_item(cart, variant, 1)
    with pytest.raises(OutOfStockError):
        set_quantity(item, variant.stock_quantity + 1)


@SHIPPING
def test_totals_for_an_empty_cart(user):
    cart, _ = resolve_cart(user=user, session_token=None)
    assert calculate_totals(cart) == {
        "subtotal": Decimal("0.00"),
        "discount_total": Decimal("0.00"),
        "shipping_cost": Decimal("0.00"),
        "grand_total": Decimal("0.00"),
    }


@SHIPPING
def test_totals_charge_flat_shipping_below_the_threshold(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 1)  # 250.00
    totals = calculate_totals(cart)
    assert totals["subtotal"] == Decimal("250.00")
    assert totals["shipping_cost"] == Decimal("30.00")
    assert totals["grand_total"] == Decimal("280.00")


@SHIPPING
def test_shipping_is_free_at_the_threshold(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 2)  # 500.00
    totals = calculate_totals(cart)
    assert totals["shipping_cost"] == Decimal("0.00")
    assert totals["grand_total"] == Decimal("500.00")


@SHIPPING
def test_a_percent_voucher_discounts_the_subtotal_only(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 1)  # 250.00
    cart.voucher = Voucher.objects.create(
        code="TEN", discount_type=DiscountType.PERCENT, value=Decimal("10")
    )
    cart.save()

    totals = calculate_totals(cart)
    assert totals["discount_total"] == Decimal("25.00")
    assert totals["shipping_cost"] == Decimal("30.00")
    assert totals["grand_total"] == Decimal("255.00")


@SHIPPING
def test_a_free_shipping_voucher_zeroes_the_shipping_line(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 1)
    cart.voucher = Voucher.objects.create(code="SHIP", discount_type=DiscountType.FREE_SHIPPING)
    cart.save()

    totals = calculate_totals(cart)
    assert totals["discount_total"] == Decimal("0.00")
    assert totals["shipping_cost"] == Decimal("0.00")
    assert totals["grand_total"] == Decimal("250.00")


@SHIPPING
def test_a_voucher_that_stopped_qualifying_is_ignored_in_the_totals(user, variant):
    cart, _ = resolve_cart(user=user, session_token=None)
    add_item(cart, variant, 1)  # 250.00
    cart.voucher = Voucher.objects.create(
        code="BIGSPEND",
        discount_type=DiscountType.PERCENT,
        value=Decimal("10"),
        min_order_total=Decimal("1000.00"),
    )
    cart.save()

    # The shopper removed items after applying the code; no discount, no crash.
    totals = calculate_totals(cart)
    assert totals["discount_total"] == Decimal("0.00")
    assert totals["grand_total"] == Decimal("280.00")


def test_merging_moves_guest_lines_into_the_user_cart(user, product):
    small = product.variants.get(sku="JORY-ETH-250")
    large = product.variants.get(sku="JORY-ETH-1000")

    guest, _ = resolve_cart(user=None, session_token=None)
    add_item(guest, small, 1)
    add_item(guest, large, 1)

    mine, _ = resolve_cart(user=user, session_token=None)
    add_item(mine, small, 2)

    merged = merge_carts(guest, mine)
    assert merged == mine
    assert merged.items.count() == 2
    assert merged.items.get(variant=small).quantity == 3
    assert merged.items.get(variant=large).quantity == 1
    assert not Cart.objects.filter(pk=guest.pk).exists()


def test_merging_clamps_to_available_stock(user, variant):
    guest, _ = resolve_cart(user=None, session_token=None)
    add_item(guest, variant, variant.stock_quantity)

    mine, _ = resolve_cart(user=user, session_token=None)
    add_item(mine, variant, variant.stock_quantity)

    merged = merge_carts(guest, mine)
    assert merged.items.get(variant=variant).quantity == variant.stock_quantity


def test_merging_carries_over_a_voucher_when_the_user_cart_has_none(user, variant):
    voucher = Voucher.objects.create(
        code="TEN", discount_type=DiscountType.PERCENT, value=Decimal("10")
    )
    guest, _ = resolve_cart(user=None, session_token=None)
    add_item(guest, variant, 1)
    guest.voucher = voucher
    guest.save()

    mine, _ = resolve_cart(user=user, session_token=None)
    assert merge_carts(guest, mine).voucher == voucher
