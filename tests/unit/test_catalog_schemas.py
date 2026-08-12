from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.catalog.care_parameter import CareLevel
from app.models.catalog.shrimp import CatalogStatus
from app.models.catalog.shrimp_variant import SaleUnit
from app.schemas.catalog import (
    CareParameterCreate,
    ShrimpCreate,
    ShrimpImageCreate,
    ShrimpVariantCreate,
)


def test_shrimp_create_defaults_to_inactive_catalog_status() -> None:
    shrimp = ShrimpCreate(name="Red Boa", type="Caridina")

    assert shrimp.catalog_status == CatalogStatus.INACTIVE
    assert shrimp.colors == []
    assert shrimp.images == []


def test_shrimp_create_limits_images_to_four() -> None:
    images = [
        ShrimpImageCreate(r2_key=f"shrimp/red-boa/{index}.webp")
        for index in range(5)
    ]

    with pytest.raises(ValidationError):
        ShrimpCreate(name="Red Boa", type="Caridina", images=images)


def test_shrimp_create_limits_colors_to_ten() -> None:
    with pytest.raises(ValidationError):
        ShrimpCreate(
            name="Red Boa",
            type="Caridina",
            colors=[f"color-{index}" for index in range(11)],
        )


@pytest.mark.parametrize("sale_quantity", [1, 5, 10])
def test_variant_accepts_supported_sale_quantities(sale_quantity: int) -> None:
    variant = ShrimpVariantCreate(
        name="Pack",
        sale_unit=SaleUnit.PACK,
        sale_quantity=sale_quantity,
        price=Decimal("45.00"),
    )

    assert variant.sale_quantity == sale_quantity


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("sale_quantity", 2),
        ("price", Decimal("-1.00")),
        ("stock_quantity", -1),
    ],
)
def test_variant_rejects_invalid_commerce_fields(
    field_name: str,
    value: object,
) -> None:
    payload = {
        "name": "Each",
        "sale_unit": SaleUnit.EACH,
        "sale_quantity": 1,
        "price": Decimal("45.00"),
        "stock_quantity": 0,
    }
    payload[field_name] = value

    with pytest.raises(ValidationError):
        ShrimpVariantCreate(**payload)


def test_care_parameter_default_level_is_beginner() -> None:
    care_parameter = CareParameterCreate()

    assert care_parameter.care_level == CareLevel.BEGINNER
