from decimal import Decimal

import pytest

from apps.core.money import to_money


def test_it_quantizes_to_two_places():
    assert to_money(Decimal("10")) == Decimal("10.00")


def test_it_rounds_half_up_not_half_even():
    # Decimal's default is ROUND_HALF_EVEN, which would give 0.12 here.
    assert to_money(Decimal("0.125")) == Decimal("0.13")
    assert to_money(Decimal("0.135")) == Decimal("0.14")


def test_it_accepts_ints_and_strings():
    assert to_money(7) == Decimal("7.00")
    assert to_money("3.456") == Decimal("3.46")


def test_it_leaves_exact_values_alone():
    assert to_money(Decimal("249.99")) == Decimal("249.99")


@pytest.mark.parametrize("value", [Decimal("0"), 0, "0.00"])
def test_zero_is_zero(value):
    assert to_money(value) == Decimal("0.00")
