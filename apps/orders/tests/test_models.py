from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.orders.models import Order, OrderItem, OrderStatus, PaymentStatus

pytestmark = pytest.mark.django_db


SHIPPING = {
    "recipient_name": "Shopper One",
    "phone": "+201000000000",
    "country": "Egypt",
    "city": "Cairo",
    "area": "Maadi",
    "street_address": "12 Road 9",
    "postal_code": "11431",
}


def make_order(user, **overrides):
    fields = dict(
        order_number="JORY-TEST0001",
        user=user,
        subtotal=Decimal("250.00"),
        discount_total=Decimal("0.00"),
        shipping_cost=Decimal("30.00"),
        grand_total=Decimal("280.00"),
        **SHIPPING,
    )
    fields.update(overrides)
    return Order.objects.create(**fields)


def test_a_new_order_is_pending_unpaid_and_cash_on_delivery(user):
    order = make_order(user)
    assert order.status == OrderStatus.PENDING
    assert order.payment_status == PaymentStatus.UNPAID
    assert order.payment_method == "COD"


def test_order_numbers_are_unique(user):
    make_order(user)
    with pytest.raises(IntegrityError):
        make_order(user)


def test_string_representation_is_the_order_number(user):
    assert str(make_order(user)) == "JORY-TEST0001"


def test_only_a_pending_order_can_be_cancelled(user):
    order = make_order(user)
    assert order.can_be_cancelled is True

    for status in (
        OrderStatus.CONFIRMED,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
    ):
        order.status = status
        assert order.can_be_cancelled is False


def test_an_item_snapshots_the_product_details(user, variant):
    order = make_order(user)
    item = OrderItem.objects.create(
        order=order,
        variant=variant,
        product_name=variant.product.name,
        variant_label=variant.label,
        sku=variant.sku,
        unit_price=variant.price,
        quantity=2,
        line_total=variant.price * 2,
    )
    assert item.line_total == Decimal("500.00")
    assert list(order.items.all()) == [item]


def test_a_snapshot_survives_the_variant_being_deleted(user, variant):
    order = make_order(user)
    OrderItem.objects.create(
        order=order,
        variant=variant,
        product_name=variant.product.name,
        variant_label=variant.label,
        sku=variant.sku,
        unit_price=variant.price,
        quantity=1,
        line_total=variant.price,
    )

    sku = variant.sku
    variant.delete()

    item = order.items.get()
    assert item.variant is None
    assert item.sku == sku
    assert item.unit_price == Decimal("250.00")


def test_a_user_with_orders_cannot_be_deleted(user):
    make_order(user)
    with pytest.raises(IntegrityError):
        user.delete()


def test_a_redemption_can_point_at_an_order(user):
    from apps.vouchers.models import DiscountType, Voucher, VoucherRedemption

    order = make_order(user)
    voucher = Voucher.objects.create(
        code="TEN", discount_type=DiscountType.PERCENT, value=Decimal("10")
    )
    redemption = VoucherRedemption.objects.create(
        voucher=voucher, user=user, order=order, discount_amount=Decimal("25.00")
    )
    assert list(order.redemptions.all()) == [redemption]
