"""create profiles table

Revision ID: 12df74bdc219
Revises: aa9ca0622799
Create Date: 2026-07-05 22:56:29.410346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "12df74bdc219"
down_revision: Union[str, Sequence[str], None] = "aa9ca0622799"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column(
            "sex",
            sa.Enum(
                "MALE",
                "FEMALE",
                "OTHER",
                "PREFER_NOT_TO_SAY",
                name="sex",
            ),
            nullable=False,
        ),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("current_weight_kg", sa.Float(), nullable=False),
        sa.Column("goal_weight_kg", sa.Float(), nullable=False),
        sa.Column(
            "goal",
            sa.Enum(
                "LOSE",
                "MAINTAIN",
                "GAIN",
                name="goal",
            ),
            nullable=False,
        ),
        sa.Column(
            "activity_level",
            sa.Enum(
                "SEDENTARY",
                "LIGHT",
                "MODERATE",
                "VERY_ACTIVE",
                "ATHLETE",
                name="activitylevel",
            ),
            nullable=False,
        ),
        sa.Column("exercise_days_per_week", sa.Integer(), nullable=False),
        sa.Column(
            "preferred_unit",
            sa.Enum(
                "METRIC",
                "IMPERIAL",
                name="preferredunit",
            ),
            nullable=False,
            server_default="METRIC",
        ),
        sa.Column("bmi", sa.Float(), nullable=False),
        sa.Column("bmr", sa.Float(), nullable=False),
        sa.Column("tdee", sa.Float(), nullable=False),
        sa.Column("daily_calorie_target", sa.Integer(), nullable=False),
        sa.Column("daily_protein_target", sa.Float(), nullable=False),
        sa.Column("daily_carb_target", sa.Float(), nullable=False),
        sa.Column("daily_fat_target", sa.Float(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_profiles_user_id"),
        "profiles",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_profiles_user_id"),
        table_name="profiles",
    )
    op.drop_table("profiles")