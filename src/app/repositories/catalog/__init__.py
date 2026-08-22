from app.repositories.catalog.care_parameter_repository import (
    create_care_parameter,
    get_care_parameter_by_shrimp_id,
    update_care_parameter,
)
from app.repositories.catalog.options_repository import (
    list_distinct_array_values,
    list_distinct_scalar_values,
    list_distinct_traits,
)
from app.repositories.catalog.shrimp_image_repository import (
    create_shrimp_image,
    delete_shrimp_image,
    get_shrimp_image_by_id,
    update_shrimp_image,
)
from app.repositories.catalog.shrimp_repository import (
    create_shrimp,
    delete_shrimp,
    get_shrimp_by_id,
    get_shrimp_by_slug,
    list_shrimp,
    list_shrimp_for_filter_options,
    update_shrimp,
)
from app.repositories.catalog.shrimp_variant_repository import (
    create_shrimp_variant,
    delete_shrimp_variant,
    get_shrimp_variant_by_id,
    update_shrimp_variant,
)

__all__ = [
    "create_care_parameter",
    "create_shrimp",
    "create_shrimp_image",
    "create_shrimp_variant",
    "delete_shrimp",
    "delete_shrimp_image",
    "delete_shrimp_variant",
    "get_care_parameter_by_shrimp_id",
    "get_shrimp_by_id",
    "get_shrimp_by_slug",
    "get_shrimp_image_by_id",
    "get_shrimp_variant_by_id",
    "list_distinct_array_values",
    "list_distinct_scalar_values",
    "list_distinct_traits",
    "list_shrimp",
    "list_shrimp_for_filter_options",
    "update_care_parameter",
    "update_shrimp",
    "update_shrimp_image",
    "update_shrimp_variant",
]
