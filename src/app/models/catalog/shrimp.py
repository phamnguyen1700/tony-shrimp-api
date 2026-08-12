import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.catalog.care_parameter import CareParameter
    from app.models.catalog.shrimp_image import ShrimpImage
    from app.models.catalog.shrimp_variant import ShrimpVariant


class CatalogStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Shrimp(Base):
    __tablename__ = "shrimp"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    species: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    line: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    colors: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)),
        nullable=False,
        default=list,
    )
    grade: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    rarity: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    catalog_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CatalogStatus.INACTIVE.value,
        index=True,
    )
    traits: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    variants: Mapped[list["ShrimpVariant"]] = relationship(
        back_populates="shrimp",
        cascade="all, delete-orphan",
    )
    care_parameter: Mapped["CareParameter | None"] = relationship(
        back_populates="shrimp",
        cascade="all, delete-orphan",
        uselist=False,
    )
    images: Mapped[list["ShrimpImage"]] = relationship(
        back_populates="shrimp",
        cascade="all, delete-orphan",
    )
