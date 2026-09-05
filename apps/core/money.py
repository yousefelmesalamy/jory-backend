from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def to_money(value):
    """Quantize to 2 decimal places, rounding half up.

    Decimal defaults to ROUND_HALF_EVEN ("banker's rounding"), which surprises
    shoppers: 0.125 would become 0.12. Every money figure in the project goes
    through this function so the rule is applied in exactly one place.
    """
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)
