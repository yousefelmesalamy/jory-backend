from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.exceptions import VoucherError
from apps.vouchers.models import DiscountType, Voucher, VoucherRedemption
from apps.vouchers.services import compute_discount, validate_voucher

pytestmark = pytest.mark.django_db


@pytest.fixture
def percent_voucher():
    return Voucher.objects.create(
        code="TEN", discount_type=DiscountType.PERCENT, value=Decimal("10")
    )


def error_code(excinfo):
    return excinfo.value.code


def test_a_valid_code_is_returned(percent_voucher, user):
    assert validate_voucher("TEN", user, Decimal("100.00")) == percent_voucher


def test_lookup_is_case_insensitive(percent_voucher, user):
    assert validate_voucher("ten", user, Decimal("100.00")) == percent_voucher


def test_an_unknown_code_is_rejected(user):
    with pytest.raises(VoucherError) as excinfo:
        validate_voucher("NOPE", user, Decimal("100.00"))
    assert error_code(excinfo) == "voucher_not_found"


def test_an_inactive_voucher_is_rejected(percent_voucher, user):
    percent_voucher.is_active = False
    percent_voucher.save()
    with pytest.raises(VoucherError) as excinfo:
        validate_voucher("TEN", user, Decimal("100.00"))
    assert error_code(excinfo) == "voucher_inactive"


def test_a_voucher_that_has_not_started_is_rejected(percent_voucher, user):
    percent_voucher.valid_from = timezone.now() + timedelta(days=1)
    percent_voucher.save()
    with pytest.raises(VoucherError) as excinfo:
        validate_voucher("TEN", user, Decimal("100.00"))
    assert error_code(excinfo) == "voucher_not_started"


def test_an_expired_voucher_is_rejected(percent_voucher, user):
    percent_voucher.valid_until = timezone.now() - timedelta(days=1)
    percent_voucher.save()
    with pytest.raises(VoucherError) as excinfo:
        validate_voucher("TEN", user, Decimal("100.00"))
    assert error_code(excinfo) == "voucher_expired"


def test_a_voucher_inside_its_window_is_accepted(percent_voucher, user):
    percent_voucher.valid_from = timezone.now() - timedelta(days=1)
    percent_voucher.valid_until = timezone.now() + timedelta(days=1)
    percent_voucher.save()
    assert validate_voucher("TEN", user, Decimal("100.00")) == percent_voucher


def test_a_subtotal_below_the_minimum_is_rejected(percent_voucher, user):
    percent_voucher.min_order_total = Decimal("200.00")
    percent_voucher.save()
    with pytest.raises(VoucherError) as excinfo:
        validate_voucher("TEN", user, Decimal("199.99"))
    assert error_code(excinfo) == "voucher_min_order"


def test_a_subtotal_exactly_at_the_minimum_is_accepted(percent_voucher, user):
    percent_voucher.min_order_total = Decimal("200.00")
    percent_voucher.save()
    assert validate_voucher("TEN", user, Decimal("200.00")) == percent_voucher


def test_a_globally_exhausted_voucher_is_rejected(percent_voucher, user):
    percent_voucher.usage_limit = 2
    percent_voucher.used_count = 2
    percent_voucher.save()
    with pytest.raises(VoucherError) as excinfo:
        validate_voucher("TEN", user, Decimal("100.00"))
    assert error_code(excinfo) == "voucher_exhausted"


def test_a_user_over_their_personal_limit_is_rejected(percent_voucher, user):
    percent_voucher.per_user_limit = 1
    percent_voucher.save()
    VoucherRedemption.objects.create(
        voucher=percent_voucher, user=user, discount_amount=Decimal("10.00")
    )
    with pytest.raises(VoucherError) as excinfo:
        validate_voucher("TEN", user, Decimal("100.00"))
    assert error_code(excinfo) == "voucher_user_limit"


def test_another_users_redemption_does_not_count_against_me(percent_voucher, user, other_user):
    percent_voucher.per_user_limit = 1
    percent_voucher.save()
    VoucherRedemption.objects.create(
        voucher=percent_voucher, user=other_user, discount_amount=Decimal("10.00")
    )
    assert validate_voucher("TEN", user, Decimal("100.00")) == percent_voucher


def test_an_anonymous_user_skips_the_per_user_check(percent_voucher):
    percent_voucher.per_user_limit = 1
    percent_voucher.save()
    assert validate_voucher("TEN", None, Decimal("100.00")) == percent_voucher


def test_percent_discount(percent_voucher):
    assert compute_discount(percent_voucher, Decimal("250.00"), Decimal("30.00")) == Decimal("25.00")


def test_percent_discount_rounds_half_up(percent_voucher):
    percent_voucher.value = Decimal("15")
    # 15% of 83.50 == 12.525
    assert compute_discount(percent_voucher, Decimal("83.50"), Decimal("30.00")) == Decimal("12.53")


def test_fixed_discount():
    voucher = Voucher.objects.create(
        code="FIFTY", discount_type=DiscountType.FIXED, value=Decimal("50")
    )
    assert compute_discount(voucher, Decimal("250.00"), Decimal("30.00")) == Decimal("50.00")


def test_a_fixed_discount_never_exceeds_the_subtotal():
    voucher = Voucher.objects.create(
        code="HUGE", discount_type=DiscountType.FIXED, value=Decimal("500")
    )
    # A total must never go negative, and shipping must never be discounted.
    assert compute_discount(voucher, Decimal("120.00"), Decimal("30.00")) == Decimal("120.00")


def test_free_shipping_discounts_nothing_from_the_subtotal():
    voucher = Voucher.objects.create(code="SHIP", discount_type=DiscountType.FREE_SHIPPING)
    assert compute_discount(voucher, Decimal("250.00"), Decimal("30.00")) == Decimal("0.00")


def test_a_percent_discount_never_touches_shipping(percent_voucher):
    percent_voucher.value = Decimal("100")
    assert compute_discount(percent_voucher, Decimal("200.00"), Decimal("30.00")) == Decimal("200.00")
