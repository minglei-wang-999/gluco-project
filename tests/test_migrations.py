import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect, text
import os
from app.database.database import Base


@pytest.fixture(scope="function")
def clean_db():
    """Create a fresh test database."""
    engine = create_engine(os.getenv("DATABASE_URL"))

    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        # Also drop alembic_version table if it exists
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()


class TestMigrations:
    """Test cases for database migrations."""

    def test_migrations_upgrade_and_downgrade(self, clean_db):
        """Test that all migrations can be applied and reverted."""
        # Upgrade to head using the correct Alembic configuration
        alembic_config = Config(
            os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        )
        command.upgrade(alembic_config, "head")

        # Get inspector from the clean database engine
        inspector = inspect(clean_db)

        # Check if all expected tables exist
        tables = inspector.get_table_names()
        expected_tables = {"users", "weixin_users", "nutrition_records", "ingredients", "tasks"}
        assert expected_tables.issubset(set(tables)), f"Missing tables. Found: {tables}"

        # Check users table columns
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        expected_user_columns = {
            "id",
            "email",
            "hashed_password",
            "is_active",
            "activation_token",
            "full_name",
            "created_at",
            "updated_at"
        }
        assert expected_user_columns.issubset(user_columns), f"Missing user columns. Found: {user_columns}"

        # Check weixin_users table columns
        weixin_user_columns = {col["name"] for col in inspector.get_columns("weixin_users")}
        expected_weixin_user_columns = {
            "id",
            "openid",
            "nickname",
            "avatar_url",
            "created_at",
            "updated_at"
        }
        assert expected_weixin_user_columns.issubset(weixin_user_columns), f"Missing weixin_user columns. Found: {weixin_user_columns}"

        # Check nutrition_records table columns
        nutrition_columns = {col["name"] for col in inspector.get_columns("nutrition_records")}
        expected_nutrition_columns = {
            "id",
            "user_id",
            "weixin_user_id",
            "meal_type",
            "meal_time",
            "pre_glucose",
            "post_glucose",
            "notes",
            "created_at",
            "updated_at",
            "total_carbs",
            "total_protein",
            "total_fat",
            "total_gl",
            "meal_gl_category",
            "impact_level",
            "protein_level",
            "fat_level",
            "protein_explanation",
            "fat_explanation",
            "impact_explanation",
            "best_time",
            "image_url"
        }
        assert expected_nutrition_columns.issubset(nutrition_columns), f"Missing nutrition columns. Found: {nutrition_columns}"

        # Check ingredients table columns
        ingredient_columns = {col["name"] for col in inspector.get_columns("ingredients")}
        expected_ingredient_columns = {
            "id",
            "nutrition_record_id",
            "name",
            "carbs_per_100g",
            "protein_per_100g",
            "fat_per_100g",
            "gi",
            "gl",
            "gi_category",
            "portion"
        }
        assert expected_ingredient_columns.issubset(ingredient_columns), f"Missing ingredient columns. Found: {ingredient_columns}"

        # Check tasks table columns
        task_columns = {col["name"] for col in inspector.get_columns("tasks")}
        expected_task_columns = {
            "id",
            "user_id",
            "weixin_user_id",
            "task_type",
            "status",
            "progress",
            "result",
            "error",
            "created_at",
            "updated_at",
            "params"
        }
        assert expected_task_columns.issubset(task_columns), f"Missing task columns. Found: {task_columns}"

        # Test downgrade back to the base migration
        command.downgrade(alembic_config, "base")
