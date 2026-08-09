import uuid

from pydantic import BaseModel, Field

from app.models.catalog.care_parameter import CareLevel


class CareParameterCreate(BaseModel):
    ph_min: float | None = Field(default=None, ge=0)
    ph_max: float | None = Field(default=None, ge=0)
    gh_min: float | None = Field(default=None, ge=0)
    gh_max: float | None = Field(default=None, ge=0)
    kh_min: float | None = Field(default=None, ge=0)
    kh_max: float | None = Field(default=None, ge=0)
    tds_min: int | None = Field(default=None, ge=0)
    tds_max: int | None = Field(default=None, ge=0)
    temperature_min: float | None = None
    temperature_max: float | None = None
    care_level: CareLevel = CareLevel.BEGINNER


class CareParameterUpdate(BaseModel):
    ph_min: float | None = Field(default=None, ge=0)
    ph_max: float | None = Field(default=None, ge=0)
    gh_min: float | None = Field(default=None, ge=0)
    gh_max: float | None = Field(default=None, ge=0)
    kh_min: float | None = Field(default=None, ge=0)
    kh_max: float | None = Field(default=None, ge=0)
    tds_min: int | None = Field(default=None, ge=0)
    tds_max: int | None = Field(default=None, ge=0)
    temperature_min: float | None = None
    temperature_max: float | None = None
    care_level: CareLevel | None = None


class CareParameterResponse(BaseModel):
    id: uuid.UUID
    shrimp_id: uuid.UUID
    ph_min: float | None
    ph_max: float | None
    gh_min: float | None
    gh_max: float | None
    kh_min: float | None
    kh_max: float | None
    tds_min: int | None
    tds_max: int | None
    temperature_min: float | None
    temperature_max: float | None
    care_level: str
