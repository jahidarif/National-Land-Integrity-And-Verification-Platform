"""Add role-based land management, drafts, documents and email-scoped chat."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "0002_managed_land_platform"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    if "role" not in user_columns:
        op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="User"))
    if "is_active" not in user_columns:
        op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "full_name" not in user_columns:
        op.add_column("users", sa.Column("full_name", sa.String(120), nullable=False, server_default="User"))
    op.execute(text("UPDATE users SET email = lower(trim(email))"))
    if "areas" not in inspector.get_table_names():
        op.create_table(
            "areas",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("mouza", sa.String(120), nullable=False),
            sa.Column("upazila", sa.String(120), nullable=False),
            sa.Column("district", sa.String(120), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "assigned_area_id" not in user_columns:
        op.add_column("users", sa.Column("assigned_area_id", sa.String(36), nullable=True))
        with op.batch_alter_table("users") as batch:
            batch.create_foreign_key("fk_users_assigned_area_id_areas", "areas", ["assigned_area_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_users_assigned_area_id", "users", ["assigned_area_id"])
    conv_columns = {c["name"] for c in sa.inspect(bind).get_columns("conversations")}
    if "user_email" not in conv_columns:
        op.add_column("conversations", sa.Column("user_email", sa.String(254), nullable=True))
        op.execute(text("UPDATE conversations SET user_email = (SELECT email FROM users WHERE users.id = conversations.user_id)"))
        with op.batch_alter_table("conversations") as batch:
            batch.alter_column("user_email", existing_type=sa.String(254), nullable=False)
            batch.create_foreign_key("fk_conversations_user_email_users", "users", ["user_email"], ["email"], ondelete="CASCADE", onupdate="CASCADE")
        op.create_index("ix_conversations_user_email_updated", "conversations", ["user_email", "updated_at"])
    # Normalize existing area rows before creating the case-insensitive functional index.
    area_rows = bind.execute(text("SELECT id, mouza, upazila, district FROM areas")).mappings().all()
    seen = {}
    for row in area_rows:
        values = [" ".join(str(row[key]).strip().split()) for key in ("mouza", "upazila", "district")]
        normalized_key = tuple(value.casefold() for value in values)
        if normalized_key in seen:
            raise RuntimeError(f"Cannot create uq_area_place_ci: areas {seen[normalized_key]} and {row['id']} become duplicates after normalization")
        seen[normalized_key] = row["id"]
        bind.execute(text("UPDATE areas SET mouza=:mouza, upazila=:upazila, district=:district WHERE id=:id"), {"mouza": values[0], "upazila": values[1], "district": values[2], "id": row["id"]})
    # Reuse the authoritative ORM metadata to create all remaining managed tables/indexes.
    from app.domain.models import Base
    Base.metadata.create_all(bind=bind, checkfirst=True)
    existing_constraints = {c.get("name") for c in sa.inspect(bind).get_check_constraints("users")}
    if "ck_area_only_officer" not in existing_constraints or "ck_users_role_values" not in existing_constraints:
        with op.batch_alter_table("users") as batch:
            if "ck_area_only_officer" not in existing_constraints:
                batch.create_check_constraint("ck_area_only_officer", "assigned_area_id IS NULL OR role = 'LandOfficer'")
            if "ck_users_role_values" not in existing_constraints:
                batch.create_check_constraint("ck_users_role_values", "role IN ('Admin', 'LandOfficer', 'User')")
    op.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_area_place_ci ON areas (lower(district), lower(upazila), lower(mouza))"))


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("documents", "land_create_drafts", "land_update_drafts", "land_transactions", "land_owners", "lands"):
        if sa.inspect(bind).has_table(table):
            op.drop_table(table)
    op.execute(text("DROP INDEX IF EXISTS uq_area_place_ci"))
    conv_columns = {c["name"] for c in sa.inspect(bind).get_columns("conversations")}
    if "user_email" in conv_columns:
        op.drop_index("ix_conversations_user_email_updated", table_name="conversations")
        with op.batch_alter_table("conversations") as batch:
            batch.drop_constraint("fk_conversations_user_email_users", type_="foreignkey")
            batch.drop_column("user_email")
    user_columns = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "assigned_area_id" in user_columns:
        op.drop_index("ix_users_assigned_area_id", table_name="users")
        with op.batch_alter_table("users") as batch:
            for constraint_name in ("ck_area_only_officer", "ck_users_role_values"):
                try: batch.drop_constraint(constraint_name, type_="check")
                except Exception: pass
            batch.drop_constraint("fk_users_assigned_area_id_areas", type_="foreignkey")
            batch.drop_column("assigned_area_id")
    if sa.inspect(bind).has_table("areas"):
        op.drop_table("areas")
    user_columns = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    for column in ("is_active", "role"):
        if column in user_columns:
            op.drop_column("users", column)
