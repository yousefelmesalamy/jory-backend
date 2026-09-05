from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.vouchers.models import DiscountType, Voucher, VoucherRedemption

pytestmark = pytest.mark.django_db


def test_the_code_is_stored_upper_case_and_trimmed():
    voucher = Voucher.objects.create(
        code="  welcome10 ", discount_type=DiscountType.PERCENT, value=Decimal("10")
    )
    assert voucher.code == "WELCOME10"


def test_codes_are_unique():
    Voucher.objects.create(code="DUP", discount_type=DiscountType.PERCENT, value=Decimal("10"))
    with pytest.raises(IntegrityError):
        Voucher.objects.create(code="dup", discount_type=DiscountType.PERCENT, value=Decimal("5"))


def test_sensible_defaults():
    voucher = Voucher.objects.create(
        code="BASIC", discount_type=DiscountType.FIXED, value=Decimal("50")
    )
    assert voucher.is_active is True
    assert voucher.used_count == 0
    assert voucher.min_order_total == Decimal("0.00")
    assert voucher.usage_limit is None
    assert voucher.per_user_limit is None


def test_string_representation_is_the_code():
    voucher = Voucher.objects.create(
        code="SUMMER", discount_type=DiscountType.PERCENT, value=Decimal("15")
    )
    assert str(voucher) == "SUMMER"


def test_a_redemption_links_a_voucher_to_a_user(user):
    voucher = Voucher.objects.create(
        code="ONCE", discount_type=DiscountType.FIXED, value=Decimal("25")
    )
    redemption = VoucherRedemption.objects.create(
        voucher=voucher, user=user, discount_amount=Decimal("25.00")
    )
    assert list(voucher.redemptions.all()) == [redemption]
    assert list(user.voucher_redemptions.all()) == [redemption]


def test_free_shipping_vouchers_need_no_value():
    voucher = Voucher.objects.create(code="FREESHIP", discount_type=DiscountType.FREE_SHIPPING)
    assert voucher.value == Decimal("0.00")
