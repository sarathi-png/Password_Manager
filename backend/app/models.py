from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    district: Mapped[District] = relationship()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="employee")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    # scope: district_id set → district employee (sees district+blocks); block_id set → block employee (sees only its block)
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id"), nullable=True, index=True)
    block_id: Mapped[int | None] = mapped_column(ForeignKey("blocks.id"), nullable=True, index=True)

    district: Mapped[District | None] = relationship(foreign_keys=[district_id])
    block: Mapped[Block | None] = relationship(foreign_keys=[block_id])

    entries: Mapped[list["PasswordEntry"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class PasswordEntry(Base):
    __tablename__ = "password_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, default="", index=True)
    username_cipher: Mapped[str] = mapped_column(Text, nullable=False, default="")
    password_cipher: Mapped[str] = mapped_column(Text, nullable=False)
    notes_cipher: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="other", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    # admin-assigned scope; null = legacy/unassigned (visible to all until assigned)
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id"), nullable=True, index=True)
    block_id: Mapped[int | None] = mapped_column(ForeignKey("blocks.id"), nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    owner: Mapped[User] = relationship(back_populates="entries")
    district_obj: Mapped[District | None] = relationship(foreign_keys=[district_id])
    block_obj: Mapped[Block | None] = relationship(foreign_keys=[block_id])


class UserEntryTag(Base):
    """Private per-user manual tag (own). Works for both admin and employee, read-only entries but writable meta."""
    __tablename__ = "user_entry_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("password_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    user: Mapped[User] = relationship()
    entry: Mapped[PasswordEntry] = relationship()


class UserEntryMeta(Base):
    """Private per-user favorites/pins (read-only entries, but personal overlay)."""
    __tablename__ = "user_entry_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("password_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship()
    entry: Mapped[PasswordEntry] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped[User | None] = relationship(back_populates="audit_logs")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    detail: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="")