import uuid

from django.conf import settings
from django.db import transaction

from apps.core.exceptions import CartItemUnavailableError, OutOfStockError, VoucherError
from apps.core.money import to_money
from apps.vouchers.models import DiscountType
from apps.vouchers.services import compute_discount, validate_voucher

from .models import Cart, CartItem


def resolve_cart(user, session_token):
    """Find or start the caller's cart.

    Authenticated shoppers get their one cart; guests are keyed by the UUID they
    echo back in `X-Cart-Token`. An unknown or malformed token starts a fresh
    cart rather than erroring, so a stale token in a browser is self-healing.
    """
    if user is not None and getattr(user, "is_authenticated", False):
        return Cart.objects.get_or_create(user=user)

    if session_token:
        try:
            return Cart.objects.get(session_token=uuid.UUID(str(session_token))), False
        except (Cart.DoesNotExist, ValueError, AttributeError):
            pass

    return Cart.objects.create(session_token=uuid.uuid4()), True


def _assert_available(variant, quantity):
    if not variant.is_active or not variant.product.is_active:
        raise CartItemUnavailableError(details={"sku": variant.sku})
    if quantity > variant.stock_quantity:
        raise OutOfStockError(
            f"Only {variant.stock_quantity} left of {variant.sku}.",
            details={"sku": variant.sku, "available": variant.stock_quantity},
        )


def add_item(cart, variant, quantity):
    """Add to the cart, incrementing an existing line rather than duplicating it."""
    existing = cart.items.filter(variant=variant).first()
    wanted = (existing.quantity if existing else 0) + quantity
    _assert_available(variant, wanted)

    if existing:
        existing.quantity = wanted
        existing.save(update_fields=["quantity", "updated_at"])
        return existing
    return CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)


def set_quantity(item, quantity):
    """Set an absolute quantity. Zero removes the line and returns None."""
    if quantity <= 0:
        item.delete()
        return None
    _assert_available(item.variant, quantity)
    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])
    return item


def calculate_totals(cart):
    """The authoritative money for a cart. The client never sends these figures."""
    subtotal = to_money(sum((item.line_total for item in cart.items.all()), to_money(0)))

    if subtotal <= 0:
        zero = to_money(0)
        return {
            "subtotal": zero,
            "discount_total": zero,
            "shipping_cost": zero,
            "grand_total": zero,
        }

    shipping = (
        to_money(0)
        if subtotal >= settings.FREE_SHIPPING_THRESHOLD
        else to_money(settings.SHIPPING_FLAT_RATE)
    )

    discount = to_money(0)
    voucher = cart.voucher
    if voucher is not None:
        try:
            # Re-validate: the cart may have shrunk below the minimum, or the
            # code may have expired, since it was applied. A cart must still
            # render — checkout re-validates and *does* raise.
            validate_voucher(voucher.code, cart.user, subtotal)
        except VoucherError:
            voucher = None
        else:
            if voucher.discount_type == DiscountType.FREE_SHIPPING:
                shipping = to_money(0)
            discount = compute_discount(voucher, subtotal, shipping)

    return {
        "subtotal": subtotal,
        "discount_total": discount,
        "shipping_cost": shipping,
        "grand_total": to_money(subtotal - discount + shipping),
    }


@transaction.atomic
def merge_carts(guest_cart, user_cart):
    """Fold a guest cart into the signed-in cart, summing quantities per variant."""
    for item in guest_cart.items.select_related("variant"):
        existing = user_cart.items.filter(variant=item.variant).first()
        wanted = (existing.quantity if existing else 0) + item.quantity
        wanted = min(wanted, item.variant.stock_quantity)  # clamp, never fail a login
        if existing:
            existing.quantity = wanted
            existing.save(update_fields=["quantity", "updated_at"])
        else:
            CartItem.objects.create(cart=user_cart, variant=item.variant, quantity=wanted)

    if user_cart.voucher is None and guest_cart.voucher is not None:
        user_cart.voucher = guest_cart.voucher
        user_cart.save(update_fields=["voucher", "updated_at"])

    guest_cart.delete()
    return user_cart
