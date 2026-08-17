"""Create the CRUD demo schemas and persistence tables.

Revision ID: 20260817_0001
Revises:
Create Date: 2026-08-17
"""

import sqlalchemy as sa

from alembic import op

revision = "20260817_0001"
down_revision = None
branch_labels = None
depends_on = None


def _uuid() -> sa.Uuid:
    return sa.Uuid()


def upgrade() -> None:
    for schema in ("core", "nutrition", "audit"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    op.create_table(
        "app_user",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        schema="core",
    )
    op.create_index("ix_core_app_user_email", "app_user", ["email"], unique=True, schema="core")

    op.create_table(
        "nutrient_definition",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("canonical_unit", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="nutrition",
    )
    op.create_index("ix_nutrition_nutrient_definition_code", "nutrient_definition", ["code"], unique=True, schema="nutrition")
    op.create_table(
        "food",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("food_kind", sa.String(32), nullable=False, server_default="ingredient"),
        sa.Column("basis_amount", sa.Numeric(18, 6), nullable=False, server_default="100"),
        sa.Column("basis_unit", sa.String(16), nullable=False, server_default="g"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("source_name", sa.String(128), nullable=False, server_default="demo_fixture"),
        sa.Column("source_version", sa.String(64), nullable=False, server_default="v1"),
        sa.Column("catalog_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("basis_amount > 0", name="food_positive_basis_amount"),
        schema="nutrition",
    )
    op.create_index("ix_nutrition_food_active_name", "food", ["canonical_name"], schema="nutrition", postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_table(
        "food_serving",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("food_id", _uuid(), sa.ForeignKey("nutrition.food.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("canonical_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("canonical_unit", sa.String(16), nullable=False, server_default="g"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("food_id", "code", name="uq_food_serving_food_code"),
        sa.CheckConstraint("canonical_amount > 0", name="food_serving_positive_amount"),
        schema="nutrition",
    )
    op.create_index("ix_nutrition_food_serving_food", "food_serving", ["food_id"], schema="nutrition")
    op.create_table(
        "food_nutrient",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("food_id", _uuid(), sa.ForeignKey("nutrition.food.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("nutrient_definition_id", _uuid(), sa.ForeignKey("nutrition.nutrient_definition.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_per_basis", sa.Numeric(18, 6), nullable=False),
        sa.Column("basis_amount", sa.Numeric(18, 6), nullable=False, server_default="100"),
        sa.Column("basis_unit", sa.String(16), nullable=False, server_default="g"),
        sa.Column("source_version", sa.String(64), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("food_id", "nutrient_definition_id", name="uq_food_nutrient_food_definition"),
        sa.CheckConstraint("amount_per_basis >= 0", name="food_nutrient_non_negative_amount"),
        schema="nutrition",
    )
    op.create_index("ix_nutrition_food_nutrient_food", "food_nutrient", ["food_id"], schema="nutrition")

    op.create_table(
        "meal",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("subject_id", _uuid(), sa.ForeignKey("core.app_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("current_revision_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        schema="nutrition",
    )
    op.create_index("ix_nutrition_meal_subject_active", "meal", ["subject_id", "updated_at", "id"], schema="nutrition", postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_table(
        "meal_revision",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("meal_id", _uuid(), sa.ForeignKey("nutrition.meal.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("meal_type", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("meal_id", "revision_no", name="uq_meal_revision_meal_revision"),
        schema="nutrition",
    )
    op.create_index("ix_nutrition_meal_revision_meal", "meal_revision", ["meal_id", "revision_no"], schema="nutrition")
    op.create_table(
        "meal_item",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("meal_revision_id", _uuid(), sa.ForeignKey("nutrition.meal_revision.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("food_id", _uuid(), sa.ForeignKey("nutrition.food.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("food_serving_id", _uuid(), sa.ForeignKey("nutrition.food_serving.id", ondelete="RESTRICT")),
        sa.Column("ordinal", sa.SmallInteger(), nullable=False),
        sa.Column("display_name_snapshot", sa.String(255), nullable=False),
        sa.Column("quantity_canonical", sa.Numeric(18, 6), nullable=False),
        sa.Column("canonical_unit", sa.String(16), nullable=False, server_default="g"),
        sa.Column("original_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("original_unit", sa.String(16), nullable=False),
        sa.Column("catalog_version", sa.Integer(), nullable=False),
        sa.Column("estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("meal_revision_id", "ordinal", name="uq_meal_item_revision_ordinal"),
        sa.CheckConstraint("quantity_canonical > 0", name="meal_item_positive_quantity"),
        schema="nutrition",
    )
    op.create_index("ix_nutrition_meal_item_revision", "meal_item", ["meal_revision_id", "ordinal"], schema="nutrition")
    op.create_table(
        "meal_item_nutrient_snapshot",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("meal_item_id", _uuid(), sa.ForeignKey("nutrition.meal_item.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("nutrient_definition_id", _uuid(), sa.ForeignKey("nutrition.nutrient_definition.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_canonical", sa.Numeric(18, 6), nullable=False),
        sa.Column("canonical_unit", sa.String(16), nullable=False),
        sa.Column("food_catalog_version", sa.Integer(), nullable=False),
        sa.Column("calculation_version", sa.String(32), nullable=False, server_default="meal_snapshot_v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("meal_item_id", "nutrient_definition_id", name="uq_item_snapshot_item_nutrient"),
        schema="nutrition",
    )
    op.create_index("ix_nutrition_item_snapshot_item", "meal_item_nutrient_snapshot", ["meal_item_id"], schema="nutrition")
    op.create_table(
        "meal_nutrient_snapshot",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("meal_revision_id", _uuid(), sa.ForeignKey("nutrition.meal_revision.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("nutrient_definition_id", _uuid(), sa.ForeignKey("nutrition.nutrient_definition.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_canonical", sa.Numeric(18, 6), nullable=False),
        sa.Column("canonical_unit", sa.String(16), nullable=False),
        sa.Column("calculation_version", sa.String(32), nullable=False, server_default="meal_snapshot_v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("meal_revision_id", "nutrient_definition_id", name="uq_meal_snapshot_revision_nutrient"),
        schema="nutrition",
    )
    op.create_index("ix_nutrition_meal_snapshot_revision", "meal_nutrient_snapshot", ["meal_revision_id"], schema="nutrition")

    op.create_table(
        "audit_event",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("subject_id", _uuid(), sa.ForeignKey("core.app_user.id", ondelete="RESTRICT")),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", _uuid(), nullable=False),
        sa.Column("aggregate_version", sa.Integer()),
        sa.Column("request_id", sa.String(64)),
        sa.Column("metadata_redacted", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64)),
        schema="audit",
    )
    op.create_table(
        "outbox_event",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("event_id", _uuid(), nullable=False, unique=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", _uuid(), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("subject_id", _uuid(), sa.ForeignKey("core.app_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("delivery_state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="audit",
    )
    op.create_index("ix_audit_outbox_delivery", "outbox_event", ["delivery_state", "available_at", "id"], schema="audit")
    op.create_table(
        "idempotency_record",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("subject_id", _uuid(), sa.ForeignKey("core.app_user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer()),
        sa.Column("response_data", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("subject_id", "operation", "idempotency_key", name="uq_idempotency_subject_operation_key"),
        schema="audit",
    )


def downgrade() -> None:
    for table, schema in (
        ("idempotency_record", "audit"), ("outbox_event", "audit"), ("audit_event", "audit"),
        ("meal_nutrient_snapshot", "nutrition"), ("meal_item_nutrient_snapshot", "nutrition"),
        ("meal_item", "nutrition"), ("meal_revision", "nutrition"), ("meal", "nutrition"),
        ("food_nutrient", "nutrition"), ("food_serving", "nutrition"), ("food", "nutrition"),
        ("nutrient_definition", "nutrition"), ("app_user", "core"),
    ):
        op.drop_table(table, schema=schema)
    for schema in ("audit", "nutrition", "core"):
        op.execute(f"DROP SCHEMA {schema}")
