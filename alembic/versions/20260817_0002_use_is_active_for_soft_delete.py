"""Add is_active for soft deletion.

Revision ID: 20260817_0002
Revises: 20260817_0001
Create Date: 2026-08-17
"""

import sqlalchemy as sa

from alembic import op

revision = "20260817_0002"
down_revision = "20260817_0001"
branch_labels = None
depends_on = None


def _add_is_active(table: str, schema: str) -> None:
    op.add_column(
        table,
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema=schema,
    )


def upgrade() -> None:
    _add_is_active("app_user", "core")
    for table in ("nutrient_definition", "food", "food_serving", "food_nutrient", "meal"):
        _add_is_active(table, "nutrition")

    op.execute("UPDATE core.app_user SET is_active = FALSE WHERE status <> 'active' OR deleted_at IS NOT NULL")
    op.execute("UPDATE nutrition.nutrient_definition SET is_active = FALSE WHERE status <> 'active'")
    op.execute("UPDATE nutrition.food SET is_active = FALSE WHERE status <> 'active' OR deleted_at IS NOT NULL")
    op.execute("UPDATE nutrition.food_serving SET is_active = FALSE WHERE status <> 'active'")
    op.execute("UPDATE nutrition.meal SET is_active = FALSE WHERE deleted_at IS NOT NULL")
    op.execute(
        "UPDATE nutrition.food_serving AS serving SET is_active = FALSE "
        "FROM nutrition.food AS food WHERE serving.food_id = food.id AND NOT food.is_active"
    )
    op.execute(
        "UPDATE nutrition.food_nutrient AS nutrient SET is_active = FALSE "
        "FROM nutrition.food AS food WHERE nutrient.food_id = food.id AND NOT food.is_active"
    )

    op.drop_index("ix_nutrition_food_active_name", table_name="food", schema="nutrition")
    op.drop_index("ix_nutrition_meal_subject_active", table_name="meal", schema="nutrition")
    op.drop_index("ix_nutrition_food_serving_food", table_name="food_serving", schema="nutrition")
    op.drop_index("ix_nutrition_food_nutrient_food", table_name="food_nutrient", schema="nutrition")
    op.create_index(
        "ix_nutrition_food_active_name",
        "food",
        ["canonical_name"],
        schema="nutrition",
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "ix_nutrition_meal_subject_active",
        "meal",
        ["subject_id", "updated_at", "id"],
        schema="nutrition",
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "ix_nutrition_food_serving_food",
        "food_serving",
        ["food_id"],
        schema="nutrition",
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "ix_nutrition_food_nutrient_food",
        "food_nutrient",
        ["food_id"],
        schema="nutrition",
        postgresql_where=sa.text("is_active"),
    )

    # Keep legacy columns during the compatibility period. Application code no longer reads or writes them,
    # which lets existing installations migrate without discarding deletion timestamps or prior statuses.


def downgrade() -> None:
    op.execute("UPDATE core.app_user SET status = 'disabled', deleted_at = now() WHERE NOT is_active")
    op.execute("UPDATE nutrition.nutrient_definition SET status = 'inactive' WHERE NOT is_active")
    op.execute("UPDATE nutrition.food SET status = 'inactive', deleted_at = now() WHERE NOT is_active")
    op.execute("UPDATE nutrition.food_serving SET status = 'inactive' WHERE NOT is_active")
    op.execute("UPDATE nutrition.meal SET deleted_at = now() WHERE NOT is_active")

    op.drop_index("ix_nutrition_food_active_name", table_name="food", schema="nutrition")
    op.drop_index("ix_nutrition_meal_subject_active", table_name="meal", schema="nutrition")
    op.drop_index("ix_nutrition_food_serving_food", table_name="food_serving", schema="nutrition")
    op.drop_index("ix_nutrition_food_nutrient_food", table_name="food_nutrient", schema="nutrition")
    op.create_index(
        "ix_nutrition_food_active_name",
        "food",
        ["canonical_name"],
        schema="nutrition",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_nutrition_meal_subject_active",
        "meal",
        ["subject_id", "updated_at", "id"],
        schema="nutrition",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_nutrition_food_serving_food", "food_serving", ["food_id"], schema="nutrition")
    op.create_index("ix_nutrition_food_nutrient_food", "food_nutrient", ["food_id"], schema="nutrition")

    for table, schema in (
        ("meal", "nutrition"),
        ("food_nutrient", "nutrition"),
        ("food_serving", "nutrition"),
        ("food", "nutrition"),
        ("nutrient_definition", "nutrition"),
        ("app_user", "core"),
    ):
        op.drop_column(table, "is_active", schema=schema)
