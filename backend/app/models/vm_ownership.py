from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VMOwnership(Base):
    """Which user owns a libvirt domain. A domain with no row here is unassigned.

    Keyed by the libvirt UUID rather than a foreign key, because the domain itself lives in
    libvirt, not in this database.
    """

    __tablename__ = "vm_ownership"

    vm_uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    assigned_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
