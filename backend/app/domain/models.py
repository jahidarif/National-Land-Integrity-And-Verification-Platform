"""Land Integrity platform models (SQLAlchemy 2.x).  Authoritative data model for the build prompt.

Conventions
- Base and Timestamped are your existing classes (Timestamped supplies created_at / updated_at; if you use
  Project B's Timestamped, which also supplies `id`, drop the duplicate `id` lines).
- RefreshToken (jti-based) and Message are taken unchanged from Project A and are not repeated here.
- ORM entities are data classes with no behaviour. They are the one exemption from the backend rule
  "one class per file": all entities live together in this single models.py.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (JSON, BigInteger, Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey,
                        Index, Integer, Numeric, String, Text, UniqueConstraint, event, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .timestamped import Timestamped
from .value_objects.role import Role


def _uuid() -> str:
    return str(uuid.uuid4())


# `date` is also a column name in LandTransaction; annotating with the alias keeps the column nullable.
DateType = date

# JSONB on PostgreSQL, plain JSON elsewhere (e.g. the SQLite test database).
_JSON = JSON().with_variant(JSONB(), "postgresql")


# ───────────────────────── AREAS ─────────────────────────
class Area(Timestamped, Base):
    __tablename__ = "areas"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mouza: Mapped[str] = mapped_column(String(120), nullable=False)
    upazila: Mapped[str] = mapped_column(String(120), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False)

    officers: Mapped[list["User"]] = relationship(back_populates="assigned_area")
    lands: Mapped[list["Land"]] = relationship(back_populates="area")
    create_drafts: Mapped[list["LandCreateDraft"]] = relationship(back_populates="area")


# An area is identified by ALL THREE fields together, ignoring letter case.
# Services also trim and collapse internal whitespace before saving, so
# "Demo  Mouza 01" and "demo mouza 01" cannot both exist in the same upazila and district.
Index("uq_area_place_ci", func.lower(Area.district), func.lower(Area.upazila), func.lower(Area.mouza), unique=True)


# ───────────────────────── USERS ─────────────────────────
class User(Timestamped, Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)  # store lowercased
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Stored as "Admin" | "LandOfficer" | "User".
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]), default=Role.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # NULL = officer with no area yet (admin leaves it empty). Only officers may have an area.
    assigned_area_id: Mapped[str | None] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL"), index=True, nullable=True)

    assigned_area: Mapped[Area | None] = relationship(back_populates="officers")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan",
        foreign_keys="Conversation.user_id")  # Conversation also has a user_email FK
    # Only role "User" owns documents (enforced in the upload use case).
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("assigned_area_id IS NULL OR role = 'LandOfficer'", name="ck_area_only_officer"),
    )


@event.listens_for(User.role, "set", active_history=True)
def _role_is_immutable(target, value, oldvalue, initiator):
    """Role can be chosen once (on create) and never changed afterwards."""
    if isinstance(oldvalue, Role) and oldvalue != value:
        raise ValueError("A user's role cannot be changed.")


# ───────────────────────── LANDS ─────────────────────────
class Land(Timestamped, Base):
    __tablename__ = "lands"
    # The human Land ID (e.g. LAND-BD-DEMO-0001) IS the primary key. Exposed as `landId` in JSON.
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    area_id: Mapped[str] = mapped_column(ForeignKey("areas.id", ondelete="RESTRICT"), index=True, nullable=False)

    # parcel
    jl_no: Mapped[str | None] = mapped_column(String(40))
    record_type: Mapped[str] = mapped_column(String(10), nullable=False)       # RS / BS
    dag_no: Mapped[str] = mapped_column(String(40), nullable=False)
    khatian_no: Mapped[str | None] = mapped_column(String(40))
    area_decimal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    land_class: Mapped[str | None] = mapped_column(String(40))

    # documents
    khatian_ref: Mapped[str | None] = mapped_column(String(60))
    khatian_status: Mapped[str | None] = mapped_column(String(40))
    deed_no: Mapped[str | None] = mapped_column(String(60))
    deed_date: Mapped[date | None] = mapped_column(Date)
    deed_registration_office: Mapped[str | None] = mapped_column(String(160))
    mutation_ref: Mapped[str | None] = mapped_column(String(60))
    mutation_status: Mapped[str | None] = mapped_column(String(40))
    dcr_ref: Mapped[str | None] = mapped_column(String(60))
    dcr_status: Mapped[str | None] = mapped_column(String(40))
    dakhila_ref: Mapped[str | None] = mapped_column(String(60))
    dakhila_status: Mapped[str | None] = mapped_column(String(40))

    # ownership / succession
    ownership_status: Mapped[str | None] = mapped_column(String(40))
    death_indicator: Mapped[str | None] = mapped_column(String(10))
    successor_process: Mapped[str | None] = mapped_column(String(40))
    mutation_after_succession: Mapped[str | None] = mapped_column(String(40))
    succession_status: Mapped[str | None] = mapped_column(String(40))

    # case / mortgage
    case_exists: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    case_ref: Mapped[str | None] = mapped_column(String(60))
    case_type: Mapped[str | None] = mapped_column(String(60))
    case_status: Mapped[str | None] = mapped_column(String(40))
    mortgage_exists: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mortgage_ref: Mapped[str | None] = mapped_column(String(60))
    mortgage_status: Mapped[str | None] = mapped_column(String(40))

    # price
    last_sold_price_bdt: Mapped[int | None] = mapped_column()
    last_sold_date: Mapped[date | None] = mapped_column(Date)
    last_sold_deed_ref: Mapped[str | None] = mapped_column(String(60))
    reserved_price_bdt: Mapped[int | None] = mapped_column()
    reserved_price_date: Mapped[date | None] = mapped_column(Date)
    price_flag: Mapped[str | None] = mapped_column(String(40))

    # verification (values entered by officers; not computed)
    overall_status: Mapped[str | None] = mapped_column(String(60), index=True)
    risk_level: Mapped[str | None] = mapped_column(String(10), index=True)
    verification_flags: Mapped[str | None] = mapped_column(String(400))        # ';'-joined, as in the JSON
    document_level_status: Mapped[str | None] = mapped_column(String(40))
    ownership_check: Mapped[str | None] = mapped_column(String(40))
    succession_check: Mapped[str | None] = mapped_column(String(40))
    case_check: Mapped[str | None] = mapped_column(String(40))
    mortgage_check: Mapped[str | None] = mapped_column(String(40))
    price_check: Mapped[str | None] = mapped_column(String(40))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_version: Mapped[str | None] = mapped_column(String(60))
    source_snapshot_version: Mapped[str | None] = mapped_column(String(60))

    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    area: Mapped[Area] = relationship(back_populates="lands")
    owners: Mapped[list["LandOwner"]] = relationship(back_populates="land", cascade="all, delete-orphan")
    transactions: Mapped[list["LandTransaction"]] = relationship(
        back_populates="land", cascade="all, delete-orphan", order_by="LandTransaction.date")
    update_draft: Mapped["LandUpdateDraft | None"] = relationship(
        back_populates="land", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (UniqueConstraint("area_id", "record_type", "dag_no", name="uq_land_parcel"),)


class LandOwner(Base):
    """One row per (land, owner mail). Replaces users.owned_land_ids."""
    __tablename__ = "land_owners"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    land_id: Mapped[str] = mapped_column(ForeignKey("lands.id", ondelete="CASCADE"), nullable=False)
    # Deliberately NOT a FK to users: an officer can register an owner before they sign up.
    owner_email: Mapped[str] = mapped_column(String(254), index=True, nullable=False)  # lowercased
    owner_ref: Mapped[str | None] = mapped_column(String(60))                          # SYN-OWNER-002-A
    share_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    is_deceased: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    land: Mapped[Land] = relationship(back_populates="owners")

    __table_args__ = (UniqueConstraint("land_id", "owner_email", name="uq_land_owner"),)


class LandTransaction(Base):
    __tablename__ = "land_transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    land_id: Mapped[str] = mapped_column(ForeignKey("lands.id", ondelete="CASCADE"), index=True, nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)  # TX-0001-02
    transaction_type: Mapped[str | None] = mapped_column(String(30))
    date: Mapped[DateType | None] = mapped_column(Date)
    amount_bdt: Mapped[int | None] = mapped_column()
    deed_ref: Mapped[str | None] = mapped_column(String(60))
    seller_ref: Mapped[str | None] = mapped_column(String(60))
    buyer_ref: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str | None] = mapped_column(String(40))

    land: Mapped[Land] = relationship(back_populates="transactions")


# ───────────────────────── DRAFTS ─────────────────────────
# A draft holds the WHOLE land form (land fields + owners[] + transactions[]) as one JSON payload.
# Drafts never touch lands, land_owners or land_transactions, never emit change events, and are invisible
# to Users, the Admin and Maira. "Send to final record" validates the payload strictly, writes the real
# rows in one transaction and deletes the draft.
class LandUpdateDraft(Timestamped, Base):
    """In-progress update of an EXISTING land. At most one per land, keyed by land id."""
    __tablename__ = "land_update_drafts"
    land_id: Mapped[str] = mapped_column(ForeignKey("lands.id", ondelete="CASCADE"), primary_key=True)
    payload: Mapped[dict] = mapped_column(_JSON, nullable=False, default=dict)
    # lands.updated_at when the draft was started. Publishing is refused (409) if the land changed since.
    base_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    land: Mapped[Land] = relationship(back_populates="update_draft")


class LandCreateDraft(Timestamped, Base):
    """In-progress NEW land that does not exist yet. Keyed by its own draft id."""
    __tablename__ = "land_create_drafts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Taken from the officer's assigned area on the server, never from the client.
    area_id: Mapped[str] = mapped_column(ForeignKey("areas.id", ondelete="RESTRICT"), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(_JSON, nullable=False, default=dict)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    area: Mapped[Area] = relationship(back_populates="create_drafts")


# ───────────────────────── DOCUMENTS ─────────────────────────
class Document(Timestamped, Base):
    """A file a User uploaded for themselves (the User view's Documents page).

    The bytes live in a private S3 bucket under `storage_key`; this row is the record. Every query is scoped by
    user_id, so a document is never reachable by another account. The storage key is never sent to the browser.
    Users pick documents from here (or from their computer) when attaching files to the chatbot.
    """
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # e.g. users/<user_id>/documents/<document_id>/<safe_filename>
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User] = relationship(back_populates="documents")

    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_document_size"),
        Index("ix_documents_user_created", "user_id", "created_at"),
    )


# ───────────────────────── CHAT ─────────────────────────
class Conversation(Timestamped, Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    # Lookup by mail. FK to users.email keeps it consistent; cascades if the mail ever changes.
    user_email: Mapped[str] = mapped_column(
        ForeignKey("users.email", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(180), default="New conversation", nullable=False)

    user: Mapped[User] = relationship(back_populates="conversations", foreign_keys=[user_id])
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
        Index("ix_conversations_user_email_updated", "user_email", "updated_at"),
    )


# Project A authentication/chat support entities retained unchanged in purpose.
class RefreshToken(Timestamped, Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    jti: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class Message(Timestamped, Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    __table_args__ = (Index("ix_messages_conversation_sequence", "conversation_id", "sequence_no", unique=True),)
