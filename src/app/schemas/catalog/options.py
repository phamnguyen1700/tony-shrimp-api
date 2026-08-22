from pydantic import BaseModel


class CatalogOptionsResponse(BaseModel):
    catalog_statuses: list[str]
    care_levels: list[str]
    sale_units: list[str]
    lines: list[str]
    colors: list[str]
    grades: list[str]
    rarities: list[str]
    traits: list[str]


class CatalogFilterOptionsResponse(BaseModel):
    species: list[str]
    lines: list[str]
    colors: list[str]
    grades: list[str]
    rarities: list[str]
    traits: list[str]
    availability: list[str]
