from decimal import Decimal

from django.utils import timezone

from apps.core.exceptions import (
    VoucherExhaustedError,
    VoucherExpiredError,
    VoucherInactiveError,
    VoucherMinOrderError,
    VoucherNotFoundError,
    VoucherNotStartedError,
    VoucherUserLimitError,
)
from apps.core.money import to_money

from .models import DiscountType, Voucher, VoucherRedemption


def validate_voucher(code, user, subtotal):
    """Return the usable Voucher for `code`, or raise a VoucherError saying why not.

    Called twice in a purchase: once when the shopper applies the code, and again
    inside checkout — a code can expire or run out between the two.
    """
    try:
        voucher = Voucher.objects.get(code=code.strip().upper())
    except Voucher.DoesNotExist:
        raise VoucherNotFoundError(details={"code": code})

    if not voucher.is_active:
        raise VoucherInactiveError()

    now = timezone.now()
    if voucher.valid_from and now < voucher.valid_from:
        raise VoucherNotStartedError()
    if voucher.valid_until and now > voucher.valid_until:
        raise VoucherExpiredError()

    if subtotal < voucher.min_order_total:
        raise VoucherMinOrderError(
            f"This voucher needs a subtotal of at least {voucher.min_order_total}.",
            details={"min_order_total": str(voucher.min_order_total)},
        )

    if voucher.usage_limit is not None and voucher.used_count >= voucher.usage_limit:
        raise VoucherExhaustedError()

    # Anonymous shoppers cannot be counted; the limit is enforced at checkout,
    # which requires a login.
    if (
        user is not None
        and getattr(user, "is_authenticated", False)
        and voucher.per_user_limit is not None
    ):
        used = VoucherRedemption.objects.filter(voucher=voucher, user=user).count()
        if used >= voucher.per_user_limit:
            raise VoucherUserLimitError()

    return voucher


def compute_discount(voucher, subtotal, shipping_cost):
    """Money taken off the subtotal. Shipping is never discounted here — a
    FREE_SHIPPING voucher zeroes the shipping line in the cart totals instead."""
    if voucher is None:
        return to_money(0)

    if voucher.discount_type == DiscountType.PERCENT:
        return to_money(subtotal * voucher.value / Decimal("100"))

    if voucher.discount_type == DiscountType.FIXED:
        return to_money(min(voucher.value, subtotal))

    return to_money(0)
