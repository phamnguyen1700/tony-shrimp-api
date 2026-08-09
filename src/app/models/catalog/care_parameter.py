import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.catalog.shrimp import Shrimp


class CareLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class CareParameter(Base):
    __tablename__ = "care_parameters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    shrimp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shrimp.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    ph_min: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    ph_max: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    gh_min: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    gh_max: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    kh_min: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    kh_max: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    tds_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tds_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature_min: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    temperature_max: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    care_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CareLevel.BEGINNER.value,
    )

    shrimp: Mapped["Shrimp"] = relationship(back_populates="care_parameter")
