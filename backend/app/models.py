from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.types import TypeDecorator, Text as TextType


class SearchVectorType(TypeDecorator):
    """Type that uses TSVECTOR on PostgreSQL and Text on SQLite."""
    impl = TextType
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(TextType())
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

    # smart search: include password in search vector (opt-in per user)
    search_include_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    district: Mapped[District | None] = relationship(foreign_keys=[district_id])
    block: Mapped[Block | None] = relationship(foreign_keys=[block_id])

    entries: Mapped[list["PasswordEntry"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class Category(Base):
    """Hierarchical category tree: e.g. Education -> LokOS -> LokOS-School"""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=999, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    parent: Mapped["Category | None"] = relationship(back_populates="children", remote_side="Category.id")
    children: Mapped[list["Category"]] = relationship(back_populates="parent", cascade="all, delete-orphan")


class Profile(Base):
    """Netflix-style profile: groups users and entries together."""
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    created_by: Mapped[User | None] = relationship()
    users: Mapped[list["UserProfile"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    entries: Mapped[list["PasswordEntry"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class UserProfile(Base):
    """Join table: which users can access which profiles, with per-profile PIN."""
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    pin_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    user: Mapped[User] = relationship()
    profile: Mapped[Profile] = relationship(back_populates="users")


class PasswordEntry(Base):
    __tablename__ = "password_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, default="", index=True)
    username_cipher: Mapped[str] = mapped_column(Text, nullable=False, default="")
    password_cipher: Mapped[str] = mapped_column(Text, nullable=False)
    notes_cipher: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="other", index=True)
    # smart grouping
    host: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    exact_host: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    registrable_domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    host_group_key: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    smart_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    smart_subcategory_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    # admin-assigned scope; null = legacy/unassigned (visible to all until assigned)
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id"), nullable=True, index=True)
    block_id: Mapped[int | None] = mapped_column(ForeignKey("blocks.id"), nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # full-text search vector (PostgreSQL TSVECTOR, SQLite Text)
    search_vector: Mapped[str | None] = mapped_column(SearchVectorType, nullable=True)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    owner: Mapped[User] = relationship(back_populates="entries")
    district_obj: Mapped[District | None] = relationship(foreign_keys=[district_id])
    block_obj: Mapped[Block | None] = relationship(foreign_keys=[block_id])
    smart_category: Mapped[Category | None] = relationship(foreign_keys=[smart_category_id])
    smart_subcategory: Mapped[Category | None] = relationship(foreign_keys=[smart_subcategory_id])

    # profile scoping; null = unassigned (legacy entries)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id"), nullable=True, index=True)
    profile: Mapped[Profile | None] = relationship(back_populates="entries")


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


class UserCategoryOverride(Base):
    """Private per-user category/subcategory override (visible only on that user's phone). Admin writes global PasswordEntry.smart_*."""
    __tablename__ = "user_category_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("password_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    subcategory_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship()
    entry: Mapped[PasswordEntry] = relationship()
    category: Mapped[Category | None] = relationship(foreign_keys=[category_id])
    subcategory: Mapped[Category | None] = relationship(foreign_keys=[subcategory_id])


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