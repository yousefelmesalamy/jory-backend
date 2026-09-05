import uuid

from django.conf import settings
from django.db import transaction

from apps.catalog.models import ProductVariant
from apps.core.exceptions import (
    CartItemUnavailableError,
    EmptyCartError,
    OrderNotCancellableError,
    OutOfStockError,
)
from apps.core.money import to_money
from apps.vouchers.models import DiscountType, VoucherRedemption
from apps.vouchers.services import compute_discount, validate_voucher

from .models import Order, OrderItem, OrderStatus

ORDER_NUMBER_PREFIX = "JORY-"


def generate_order_number():
    """A short, human-quotable reference."""
    return f"{ORDER_NUMBER_PREFIX}{uuid.uuid4().hex[:8].upper()}"


def _unique_order_number():
    for _ in range(10):
        number = generate_order_number()
        if not Order.objects.filter(order_number=number).exists():
            return number
    raise RuntimeError("Could not allocate a unique order number.")


@transaction.atomic
def place_order(user, cart, address_data):
    """Turn a cart into a COD order.

    Everything is re-checked inside the transaction: stock and availability can
    have changed since the cart was built, and a voucher can expire or run out
    between being applied and being used. Every total is recomputed here — the
    client's figures are never trusted.
    """
    items = list(cart.items.select_related("variant", "variant__product"))
    if not items:
        raise EmptyCartError()

    # Lock the variants for the rest of the transaction. SQLite ignores this;
    # on PostgreSQL it serialises concurrent checkouts of the same stock.
    locked = {
        variant.pk: variant
        for variant in ProductVariant.objects.select_for_update().filter(
            pk__in=[item.variant_id for item in items]
        )
    }

    subtotal = to_money(0)
    for item in items:
        variant = locked[item.variant_id]
        if not variant.is_active or not variant.product.is_active:
            raise CartItemUnavailableError(details={"sku": variant.sku})
        if item.quantity > variant.stock_quantity:
            raise OutOfStockError(
                f"Only {variant.stock_quantity} left of {variant.sku}.",
                details={"sku": variant.sku, "available": variant.stock_quantity},
            )
        subtotal += to_money(variant.price * item.quantity)

    subtotal = to_money(subtotal)
    shipping = (
        to_money(0)
        if subtotal >= settings.FREE_SHIPPING_THRESHOLD
        else to_money(settings.SHIPPING_FLAT_RATE)
    )

    discount = to_money(0)
    voucher = cart.voucher
    if voucher is not None:
        # Raises VoucherError — unlike the cart view, checkout must refuse.
        voucher = validate_voucher(voucher.code, user, subtotal)
        if voucher.discount_type == DiscountType.FREE_SHIPPING:
            shipping = to_money(0)
        discount = compute_discount(voucher, subtotal, shipping)

    order = Order.objects.create(
        order_number=_unique_order_number(),
        user=user,
        status=OrderStatus.PENDING,
        subtotal=subtotal,
        discount_total=discount,
        shipping_cost=shipping,
        grand_total=to_money(subtotal - discount + shipping),
        voucher_code=voucher.code if voucher else "",
        **address_data,
    )

    for item in items:
        variant = locked[item.variant_id]
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=variant.product.name,
            variant_label=variant.label,
            sku=variant.sku,
            unit_price=variant.price,
            quantity=item.quantity,
            line_total=to_money(variant.price * item.quantity),
        )
        variant.stock_quantity -= item.quantity
        variant.save(update_fields=["stock_quantity", "updated_at"])

    if voucher is not None:
        VoucherRedemption.objects.create(
            voucher=voucher, user=user, order=order, discount_amount=discount
        )
        voucher.used_count += 1
        voucher.save(update_fields=["used_count", "updated_at"])

    cart.items.all().delete()
    cart.voucher = None
    cart.save(update_fields=["voucher", "updated_at"])

    return order


@transaction.atomic
def cancel_order(order):
    """Cancel a pending order: restore its stock and release its voucher."""
    if not order.can_be_cancelled:
        raise OrderNotCancellableError(details={"status": order.status})

    for item in order.items.all():
        # The variant may have been deleted since; the snapshot still stands and
        # there is no stock row left to credit.
        if item.variant_id is None:
            continue
        variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
        variant.stock_quantity += item.quantity
        variant.save(update_fields=["stock_quantity", "updated_at"])

    for redemption in order.redemptions.select_related("voucher"):
        voucher = redemption.voucher
        if voucher.used_count > 0:
            voucher.used_count -= 1
            voucher.save(update_fields=["used_count", "updated_at"])
        redemption.delete()

    order.status = OrderStatus.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order
