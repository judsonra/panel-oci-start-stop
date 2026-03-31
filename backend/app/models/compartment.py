from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Compartment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "compartments"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ocid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
