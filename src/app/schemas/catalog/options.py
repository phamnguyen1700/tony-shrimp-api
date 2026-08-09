from pydantic import BaseModel


class CatalogOptionsResponse(BaseModel):
    catalog_statuses: list[str]
    care_levels: list[str]
    sale_units: list[str]
    types: list[str]
    colors: list[str]
    grades: list[str]
    rarities: list[str]
    traits: list[str]
