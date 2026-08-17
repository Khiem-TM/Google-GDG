from decimal import Decimal

import pytest

from app.domain.nutrition import calculate_amount_per_basis, normalize_mass


def test_BR_GEN_005_normalizes_mass_to_grams() -> None:
    assert normalize_mass(Decimal("0.4"), "kg") == Decimal("400.000")


def test_BR_MEAL_002_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        normalize_mass(Decimal("0"), "g")


def test_BR_FOOD_003_calculates_nutrient_from_basis() -> None:
    assert calculate_amount_per_basis(Decimal("185"), Decimal("400"), Decimal("100")) == Decimal("740.000")
