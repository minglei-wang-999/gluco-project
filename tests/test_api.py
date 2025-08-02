import pytest
from sqlalchemy.orm import Session
import io
from PIL import Image
import os
from datetime import datetime, timedelta, timezone
from app.models.user_models import User
from app.utils.auth import get_password_hash, create_access_token, ALGORITHM, SECRET_KEY
from app.utils.email import send_activation_email
from unittest.mock import patch, MagicMock
import json

# test_db and client fixtures are imported from conftest.py automatically


@pytest.fixture(autouse=True)
def mock_jwt_secret(monkeypatch):
    """Mock JWT secret key for testing."""
    TEST_SECRET = "test_secret_key_123"
    # Mock both the environment variable and the actual secret key used in the auth module
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.setattr("app.utils.auth.SECRET_KEY", TEST_SECRET)
    monkeypatch.setattr(
        "app.utils.auth.ALGORITHM", "HS256"
    )  # Ensure algorithm is consistent
    return TEST_SECRET  # Return the secret so tests can use it if needed


@pytest.fixture
def test_user(test_db: Session):
    """Create a test user and return their token."""
    # Create test user
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # Create access token with user ID as integer
    token = create_access_token(data={"sub": user.id})
    return {"user": user, "token": token}


@pytest.fixture
def auth_headers(test_user):
    """Return authorization headers."""
    return {"Authorization": f"Bearer {test_user['token']}"}


def create_test_image():
    """Create a test image."""
    # Create a small test image
    img = Image.new("RGB", (100, 100), color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)
    return ("test.jpg", img_byte_arr, "image/jpeg")


@pytest.fixture
def test_email_user(test_db: Session):
    """Create a test user for email verification."""
    user = User(
        email="test_activation@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test Email User",
        is_active=False,
        activation_token="test-activation-token-123",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(autouse=True)
def mock_gpt_client(monkeypatch):
    """Mock GPTClient."""
    mock = MagicMock()
    mock.analyze_food.return_value = {
        "ingredients": [{"name": "apple", "amount": "1", "unit": "piece"}],
        "meal_type": "snack",
        "cooking_method": "raw",
    }
    monkeypatch.setattr("app.dependencies.get_gpt_client", lambda: mock)
    return mock


class TestJobs:
    """Test cases for jobs endpoint."""


    def test_save_meal_unauthorized(self, client):
        """Test that unauthorized meal saves are rejected."""
        # Create test image and analysis
        analysis = {
            "ingredients": [
                {
                    "name": "test",
                    "portion": 100.0,
                    "carbs_per_100g": 50.0,
                    "protein_per_100g": 20.0,
                    "fat_per_100g": 10.0,
                    "gi": 55,
                    "gl": 15.0,
                    "gi_category": "medium",
                    "gl_category": "medium",
                }
            ],
            "total_carbs": 50.0,
            "total_protein": 20.0,
            "total_fat": 10.0,
            "total_gl": 15.0,
            "meal_gl_category": "medium",
            "impact_level": "moderate",
            "protein_level": "good",
            "fat_level": "medium",
            "protein_explanation": "20g protein helps slow down glucose absorption",
            "fat_explanation": "10g fat affects glucose absorption rate",
            "impact_explanation": "Medium impact on blood sugar",
            "best_time": "Best consumed after exercise",
            "tips": ["Tip 1", "Tip 2"],
        }

        # Make request without auth token
        response = client.post(
            "/meals",
            json={
                "file_id": "test.jpg",
                "analysis": analysis,
            },
        )

        assert response.status_code == 401

    def test_save_meal_authorized(self, client, auth_headers, test_db):
        """Test saving meal with authorization."""
        # Create test image and analysis
        analysis = {
            "ingredients": [
                {
                    "name": "test",
                    "portion": 100.0,
                    "carbs_per_100g": 50.0,
                    "protein_per_100g": 20.0,
                    "fat_per_100g": 10.0,
                    "gi": 55.0,
                    "gl": 15.0,
                    "gi_category": "medium",
                    "gl_category": "medium",
                }
            ],
            "total_carbs": 50.0,
            "total_protein": 20.0,
            "total_fat": 10.0,
            "total_gl": 15.0,
            "meal_gl_category": "medium",
            "impact_level": "moderate",
            "protein_level": "good",
            "fat_level": "medium",
            "protein_explanation": "20g protein helps slow down glucose absorption",
            "fat_explanation": "10g fat affects glucose absorption rate",
            "impact_explanation": "Medium impact on blood sugar",
            "best_time": "Best consumed after exercise",
            "tips": ["Tip 1", "Tip 2"],
        }

        # Make request with auth token
        response = client.post(
            "/meals",
            json={
                "file_id": "test.jpg",
                "analysis": analysis,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data

        # Verify record was saved
        user = test_db.query(User).filter(User.email == "test@example.com").first()
        assert len(user.nutrition_records) == 1
        record = user.nutrition_records[0]

        # Verify saved data
        assert record.total_carbs == 50.0
        assert record.total_protein == 20.0
        assert record.total_fat == 10.0
        assert record.total_gl == 15.0
        assert record.meal_gl_category == "medium"
        assert record.impact_level == "moderate"
        assert record.protein_level == "good"
        assert record.fat_level == "medium"
        assert (
            record.protein_explanation
            == "20g protein helps slow down glucose absorption"
        )
        assert record.fat_explanation == "10g fat affects glucose absorption rate"
        assert record.impact_explanation == "Medium impact on blood sugar"
        assert record.best_time == "Best consumed after exercise"

        # Verify ingredient was saved
        assert len(record.ingredients) == 1
        ingredient = record.ingredients[0]
        assert ingredient.name == "test"
        assert ingredient.portion == 100.0
        assert ingredient.carbs_per_100g == 50.0
        assert ingredient.protein_per_100g == 20.0
        assert ingredient.fat_per_100g == 10.0
        assert ingredient.gi == 55.0
        assert ingredient.gl == 15.0
        assert ingredient.gi_category == "medium"

    def test_temp_url(self, client, auth_headers):
        """Test acquiring a temp url from a cloud id."""
        test_cloud_id = "cloud://test_file_id"
        expected_url = "https://temp.url/test_file_id"
        with patch("app.storage.weixin_cloud_storage.WeixinCloudStorage.get_download_url", return_value=expected_url):
            response = client.post(
                "/jobs/temp-url",
                json={"cloud_id": test_cloud_id},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["temp_url"] == expected_url


class TestUserRegistration:
    """Test cases for user registration and activation."""

    def test_register_user(self, client, test_db):
        """Test registering a new user."""
        user_data = {
            "email": "newuser@example.com",
            "password": "testpass123",
            "full_name": "New User",
        }

        response = client.post("/users/register", json=user_data)
        assert response.status_code == 201

        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["is_active"] == False

        # Verify user was created in database
        user = test_db.query(User).filter(User.email == user_data["email"]).first()
        assert user is not None
        assert user.activation_token is not None
        assert not user.is_active

    def test_register_existing_user(self, client, test_db, test_user):
        """Test registering with an email that's already taken."""
        user_data = {
            "email": test_user["user"].email,  # Use existing user's email
            "password": "testpass123",
            "full_name": "Another User",
        }

        response = client.post("/users/register", json=user_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_activate_user(self, client, test_db):
        """Test activating a user account."""
        # Create an inactive user
        activation_token = "test-activation-token"
        user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="Inactive User",
            is_active=False,
            activation_token=activation_token,
        )
        test_db.add(user)
        test_db.commit()

        # Activate the user via the endpoint
        response = client.post(f"/users/activate/{activation_token}")
        assert response.status_code == 200

        # Instead of refreshing the old instance, requery from the DB
        activated_user = (
            test_db.query(User).filter(User.email == "inactive@example.com").first()
        )
        assert activated_user.is_active
        assert activated_user.activation_token is None

    def test_activate_invalid_token(self, client):
        """Test activating with an invalid token."""
        response = client.post("/users/activate/invalid-token")
        assert response.status_code == 404
        assert "Invalid activation token" in response.json()["detail"]

    def test_activate_already_active(self, client, test_db):
        """Test activating an already active account."""
        # Create an active user with a token (shouldn't happen in practice)
        activation_token = "test-activation-token"
        user = User(
            email="active@example.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="Active User",
            is_active=True,
            activation_token=activation_token,
        )
        test_db.add(user)
        test_db.commit()

        # Try to activate
        response = client.post(f"/users/activate/{activation_token}")
        assert response.status_code == 400
        assert "Account already activated" in response.json()["detail"]


@pytest.fixture(autouse=True)
def mock_resend(monkeypatch):
    """Mock Resend for testing."""
    monkeypatch.setenv("RESEND_API_KEY", "dummy_api_key")
    mocked_resend = MagicMock()
    mocked_resend.return_value = {"id": "test_email_id"}
    monkeypatch.setattr("resend.Emails.send", mocked_resend)
    return mocked_resend


class TestEmailVerification:
    def test_send_activation_email(self, client, mock_resend, test_email_user):
        """Test sending activation email."""
        # Call the endpoint that triggers email sending
        response = client.post(
            "/auth/resend-activation", json={"email": test_email_user.email}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Activation email sent successfully"

        # Verify Resend was called correctly
        mock_resend.assert_called_once()

        # Verify email content
        sent_email = mock_resend.call_args[0][0]
        assert test_email_user.email == sent_email["to"]
        assert sent_email["from"] == os.getenv("MAIL_FROM", "onboarding@resend.dev")
        assert sent_email["subject"] == "Activate Your Account"
        assert "Welcome to Gluco!" in sent_email["html"]
        assert test_email_user.activation_token in sent_email["html"]
        assert "activate?token=" in sent_email["html"]
        assert "This link will expire in 24 hours" in sent_email["html"]

    def test_send_activation_email_no_token(self, client, test_db):
        """Test sending activation email to user without activation token."""
        # Create user without activation token
        user = User(
            email="no_token@example.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="No Token User",
            is_active=False,
        )
        test_db.add(user)
        test_db.commit()

        response = client.post("/auth/resend-activation", json={"email": user.email})
        assert response.status_code == 400
        assert response.json()["detail"] == "No activation token found"
