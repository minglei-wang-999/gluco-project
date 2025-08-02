import pytest
from sqlalchemy import inspect
from datetime import datetime
from app.models.user_models import User
from app.models.nutrition_models import NutritionRecord, Ingredient
from app.utils.auth import get_password_hash


class TestUserModel:
    """Test cases for User model."""

    def test_create_user(self, test_db):
        """Test creating a new user."""
        # Create a test user
        hashed_password = get_password_hash("testpassword123")
        user = User(
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User",
            activation_token="test-token-123",
        )

        # Add and commit to database
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        # Verify user was created with correct default values
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active == False  # Should be inactive by default
        assert user.activation_token == "test-token-123"
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_activation(self, test_db):
        """Test user activation process."""
        # Create an inactive user with activation token
        hashed_password = get_password_hash("testpassword123")
        user = User(
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User",
            activation_token="test-token-123",
        )

        test_db.add(user)
        test_db.commit()

        # Verify user is initially inactive
        assert user.is_active == False

        # Simulate activation
        user.is_active = True
        user.activation_token = None  # Clear the token after activation
        test_db.commit()
        test_db.refresh(user)

        # Verify user is now active and token is cleared
        assert user.is_active == True
        assert user.activation_token is None

    def test_user_schema(self, test_db):
        """Test that the users table schema matches our expectations."""
        # Get inspector
        inspector = inspect(test_db.get_bind())

        # Check users table columns
        columns = {col["name"]: col for col in inspector.get_columns("users")}

        # Required fields
        assert "id" in columns
        assert not columns["id"]["nullable"]
        assert "email" in columns
        assert not columns["email"]["nullable"]
        assert "hashed_password" in columns
        assert not columns["hashed_password"]["nullable"]
        assert "is_active" in columns
        assert not columns["is_active"]["nullable"]

        # Optional fields
        assert "full_name" in columns
        assert columns["full_name"]["nullable"]

        # Timestamps
        assert "created_at" in columns
        assert columns["created_at"]["nullable"]  # Default value but nullable
        assert "updated_at" in columns
        assert columns["updated_at"]["nullable"]  # Default value but nullable

        # Check indexes
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("users")}
        assert any(
            idx["unique"] and "email" in idx["column_names"] for idx in indexes.values()
        ), "Email should have a unique index"


class TestNutritionRecordModel:
    """Test cases for NutritionRecord model."""

    @pytest.fixture
    def test_user(self, test_db):
        """Create a test user."""
        user = User(
            email="nutrition@test.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="Nutrition Tester",
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    def test_create_nutrition_record(self, test_db, test_user):
        """Test creating a new nutrition record with ingredients."""
        # Create a nutrition record
        record = NutritionRecord(
            user_id=test_user.id,
            total_carbs=50.5,
            total_protein=25.0,
            total_fat=15.0,
            total_gl=10.0,
            meal_gl_category="MEDIUM",
            impact_level="MODERATE",
            protein_level="GOOD",
            fat_level="MEDIUM",
            protein_explanation="Good protein content",
            fat_explanation="Moderate fat content",
            impact_explanation="Moderate impact on blood sugar",
            best_time="Best consumed for lunch",
        )

        # Add ingredients with different portion values
        ingredients = [
            Ingredient(
                nutrition_record=record,
                name="Chicken Breast",
                carbs_per_100g=0.0,
                protein_per_100g=25.0,
                fat_per_100g=3.0,
                gi=0,
                gl=0,
                gi_category="LOW",
                portion=100.0,
            ),
            Ingredient(
                nutrition_record=record,
                name="Rice",
                carbs_per_100g=45.0,
                protein_per_100g=4.0,
                fat_per_100g=0.5,
                gi=70,
                gl=31.5,
                gi_category="HIGH",
                portion=150.0,
            ),
        ]

        # Add and commit to database
        test_db.add(record)
        for ingredient in ingredients:
            test_db.add(ingredient)
        test_db.commit()
        test_db.refresh(record)

        # Verify record was created
        assert record.id is not None
        assert record.user_id == test_user.id
        assert record.total_carbs == 50.5
        assert record.created_at is not None
        assert record.updated_at is not None

        # Verify ingredients were created and linked
        assert len(record.ingredients) == 2

        # Verify first ingredient
        chicken = next(i for i in record.ingredients if i.name == "Chicken Breast")
        assert chicken.protein_per_100g == 25.0
        assert chicken.gi_category == "LOW"
        assert chicken.portion == 100.0

        # Verify second ingredient
        rice = next(i for i in record.ingredients if i.name == "Rice")
        assert rice.carbs_per_100g == 45.0
        assert rice.gi_category == "HIGH"
        assert rice.portion == 150.0

    def test_nutrition_record_timestamps(self, test_db, test_user):
        """Test that timestamps are automatically set."""
        record = NutritionRecord(
            user_id=test_user.id, total_carbs=30.0, total_protein=20.0, total_fat=10.0
        )

        test_db.add(record)
        test_db.commit()

        assert isinstance(record.created_at, datetime)
        assert isinstance(record.updated_at, datetime)
        assert record.created_at <= record.updated_at

    def test_nutrition_record_schema(self, test_db):
        """Test that the nutrition record schema matches our expectations."""
        # Get inspector
        inspector = inspect(test_db.get_bind())

        # Check nutrition_records table columns
        columns = {
            col["name"]: col for col in inspector.get_columns("nutrition_records")
        }

        # Required fields
        assert "id" in columns
        assert "user_id" in columns
        assert "weixin_user_id" in columns
        assert columns["user_id"][
            "nullable"
        ]  # Now nullable since we can have either user_id or weixin_user_id
        assert columns["weixin_user_id"]["nullable"]
        assert "total_carbs" in columns
        assert "total_protein" in columns
        assert "total_fat" in columns
        assert "total_gl" in columns
        assert "meal_gl_category" in columns
        assert "impact_level" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_ingredient_schema(self, test_db):
        """Test that the ingredients table schema matches our expectations."""
        # Get inspector
        inspector = inspect(test_db.get_bind())

        # Check ingredients table columns
        columns = {col["name"]: col for col in inspector.get_columns("ingredients")}

        # Required fields
        assert "id" in columns
        assert not columns["id"]["nullable"]
        assert "nutrition_record_id" in columns
        assert not columns["nutrition_record_id"]["nullable"]
        assert "name" in columns
        assert not columns["name"]["nullable"]

        # Optional fields
        assert "carbs_per_100g" in columns
        assert columns["carbs_per_100g"]["nullable"]
        assert "protein_per_100g" in columns
        assert columns["protein_per_100g"]["nullable"]
        assert "fat_per_100g" in columns
        assert columns["fat_per_100g"]["nullable"]
        assert "gi" in columns
        assert columns["gi"]["nullable"]
        assert "gl" in columns
        assert columns["gl"]["nullable"]
        assert "gi_category" in columns
        assert columns["gi_category"]["nullable"]
        assert "portion" in columns
        assert columns["portion"]["nullable"]
