"""Calculate revenue and gross profit using Decimal arithmetic."""

from dataclasses import dataclass
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext


# Bounded inputs need at most 26 significant digits for exact totals.
# Forty digits also leave guard digits for percentage rounding.
CALCULATION_PRECISION = 40
MAX_MONEY = Decimal("1000000000000")
MAX_QUANTITY = Decimal("1000000000")
MARGIN_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True)
class RevenueResult:
    revenue: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    gross_margin: Decimal | None


def _nonnegative_decimal(
    value: Decimal | str | int, name: str, maximum: Decimal, places: int
) -> Decimal:
    """Validate bounded exact decimal inputs without silently rounding them."""
    if isinstance(value, bool) or not isinstance(value, (Decimal, str, int)):
        raise ValueError(f"{name} must be Decimal, str or int; float is not accepted")
    if isinstance(value, int) and (value < 0 or value > maximum):
        raise ValueError(f"{name} must be between 0 and {maximum}")
    if isinstance(value, str) and len(value) > 128:
        raise ValueError(f"{name} input must not exceed 128 characters")
    try:
        number = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be a valid number") from exc
    if not number.is_finite() or number < 0 or number > maximum:
        raise ValueError(f"{name} must be finite and between 0 and {maximum}")
    if len(number.as_tuple().digits) > 128:
        raise ValueError(f"{name} must not exceed 128 coefficient digits")
    quantum = Decimal("0.01") if places == 2 else Decimal("0.001")
    canonical = number.quantize(quantum)
    if canonical != number:
        raise ValueError(f"{name} must have at most {places} decimal places")
    return canonical


def calculate_revenue(
    unit_price: Decimal | str | int,
    quantity: Decimal | str | int,
    unit_cost: Decimal | str | int,
) -> RevenueResult:
    """Return totals and gross margin as a percentage.

    Price/cost: 0..1e12 with at most 2 effective decimal places.
    Quantity: 0..1e9 with at most 3 effective decimal places.
    Decimal, string and integer inputs are accepted; floats are rejected.
    Trailing zeros do not count against the decimal-place limit.
    Zero revenue has an undefined margin, represented by None. Negative
    gross profit is allowed when cost exceeds revenue. Totals are exact,
    with up to 5 decimal places, rather than rounded to currency cents.
    Margin is rounded to 4 percentage decimal places using HALF_EVEN.
    A private fixed context makes results independent of caller settings.
    """
    with localcontext(Context(prec=CALCULATION_PRECISION, rounding=ROUND_HALF_EVEN)):
        price = _nonnegative_decimal(unit_price, "unit_price", MAX_MONEY, 2)
        units = _nonnegative_decimal(quantity, "quantity", MAX_QUANTITY, 3)
        cost = _nonnegative_decimal(unit_cost, "unit_cost", MAX_MONEY, 2)
        revenue = price * units
        total_cost = cost * units
        gross_profit = revenue - total_cost
        gross_margin = (
            (gross_profit * Decimal("100") / revenue).quantize(MARGIN_QUANTUM)
            if revenue else None
        )
    return RevenueResult(revenue, total_cost, gross_profit, gross_margin)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("unit_price", help="Selling price per unit")
    parser.add_argument("quantity", help="Number of units sold")
    parser.add_argument("unit_cost", help="Cost per unit")
    args = parser.parse_args()
    try:
        result = calculate_revenue(args.unit_price, args.quantity, args.unit_cost)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Revenue: {result.revenue}")
    print(f"Total cost: {result.total_cost}")
    print(f"Gross profit: {result.gross_profit}")
    margin = f"{result.gross_margin}%" if result.gross_margin is not None else "N/A (zero revenue)"
    print(f"Gross margin: {margin}")
