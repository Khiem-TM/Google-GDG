from decimal import Decimal


def require_positive_quantity(value: Decimal) -> None:
    if value <= 0:
        raise ValueError("Meal item quantity must be greater than zero")
