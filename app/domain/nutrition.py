from decimal import ROUND_HALF_UP, Decimal

CANONICAL_MASS_UNIT = "g"
NUTRIENT_PRECISION = Decimal("0.001")


def normalize_mass(quantity: Decimal, unit: str) -> Decimal:
    factors = {"g": Decimal("1"), "kg": Decimal("1000"), "mg": Decimal("0.001")}
    try:
        normalized = quantity * factors[unit.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported mass unit: {unit}") from exc
    if normalized <= 0:
        raise ValueError("Quantity must be greater than zero")
    return normalized.quantize(NUTRIENT_PRECISION, rounding=ROUND_HALF_UP)


def calculate_amount_per_basis(amount_per_basis: Decimal, quantity_g: Decimal, basis_amount_g: Decimal) -> Decimal:
    if basis_amount_g <= 0:
        raise ValueError("Food nutrient basis must be greater than zero")
    return (amount_per_basis * quantity_g / basis_amount_g).quantize(NUTRIENT_PRECISION, rounding=ROUND_HALF_UP)
