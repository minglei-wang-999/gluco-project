import os
import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
import base64
import json
import time
import requests
import re
from unittest.mock import ANY
import sqlalchemy as sa

# Define test order using pytest.mark
pytestmark = pytest.mark.order

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

from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.main import app
from app.database.subscription import Subscription, PaymentRecord
from app.schemas.subscription import SubscriptionStatus, PaymentStatus
from app.config.subscription_plans import SUBSCRIPTION_PLANS
from app.dependencies import get_db
from app.models.user_models import WeixinUser
from app.utils.auth import create_access_token
from app.services.subscription_service import SubscriptionService


@pytest.mark.order("subscription")
class TestSubscriptionSystem:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, db_session):
        """Clean up the database before and after each test"""
        def clean_tables():
            try:
                # Get database engine and inspector
                engine = db_session.get_bind()
                
                # Ensure tables exist by creating them if needed
                from app.database.database import Base
                Base.metadata.create_all(bind=engine)
                
                inspector = sa.inspect(engine)
                table_names = inspector.get_table_names()
                
                # Clear rows from tables in order to respect foreign key constraints
                if "payment_records" in table_names:
                    db_session.execute(text("DELETE FROM payment_records"))
                if "subscriptions" in table_names:
                    db_session.execute(text("DELETE FROM subscriptions"))
                if "ingredients" in table_names:
                    db_session.execute(text("DELETE FROM ingredients"))
                if "nutrition_records" in table_names:
                    db_session.execute(text("DELETE FROM nutrition_records"))
                if "tasks" in table_names:
                    db_session.execute(text("DELETE FROM tasks"))
                if "weixin_users" in table_names:
                    db_session.execute(text("DELETE FROM weixin_users"))
                db_session.commit()
            except:
                db_session.rollback()
                raise

        # Clean up before test
        clean_tables()
        for plan in SUBSCRIPTION_PLANS.values():
            plan["available"] = True
        yield

    @pytest.fixture
    def db_session(self):
        """Get a database session"""
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    def client(self, db_session):
        """Create a test client with a custom database session"""
        def override_get_db():
            try:
                yield db_session
            finally:
                pass  # Don't close the session here, it's managed by the db_session fixture

        app.dependency_overrides[get_db] = override_get_db
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.clear()

    @pytest.fixture
    def test_user(self, db_session):
        """Create a test WeChat user"""
        user = WeixinUser(
            openid="test_user_openid"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def auth_headers(self, test_user):
        """Get authentication headers for the test user"""
        token = create_access_token(
            data={"sub": f"weixin:{test_user.openid}"},
            expires_delta=timedelta(days=1)
        )
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_client(self, monkeypatch):
        """Create test client with mocked WeChat credentials"""
        monkeypatch.setenv("WEIXIN_APPID", "test_appid")
        monkeypatch.setenv("WEIXIN_SECRET", "test_secret")
        
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    @pytest.fixture
    def mock_weixin_auth(self, monkeypatch):
        """Mock WeChat authentication"""
        # Mock environment variables
        monkeypatch.setenv("WEIXIN_APPID", "test_appid")
        monkeypatch.setenv("WEIXIN_SECRET", "test_secret")

        async def mock_get_openid(code: str):
            return "test_openid"

        with patch("app.routers.weixin_auth.get_weixin_openid", mock_get_openid):
            yield

    def test_get_subscription_status_no_subscription(self, client, test_user, auth_headers):
        """Test getting subscription status for user without subscription"""
        response = client.get("/subscriptions/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"
        assert data["plan_id"] is None
        assert data["expires_at"] is None
        assert data["next_expires_at"] is None
        assert "available_actions" in data
        assert len(data["available_actions"]) > 0
        # Verify all plans except trial are available for new users
        assert all(action["action"] == "upgrade" for action in data["available_actions"])
        assert all(action["credit"] == "0" for action in data["available_actions"])

    def test_get_subscription_status_with_trial(self, client, test_user, auth_headers, db_session):
        """Test getting subscription status with trial subscription"""
        # Create trial subscription
        subscription_service = SubscriptionService(db_session)
        subscription_service.create_trial_subscription(test_user.openid)
        
        response = client.get("/subscriptions/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["plan_id"] == "trial"
        assert data["expires_at"] is not None
        assert data["next_expires_at"] is None
        
        # Verify available actions
        assert "available_actions" in data
        actions = data["available_actions"]
        assert len(actions) > 0
        assert all(action["action"] == "upgrade" for action in actions)
        assert all(action["credit"] == "0" for action in actions)  # No credit for trial
        assert "monthly" in [action["plan_id"] for action in actions]
        assert "yearly" in [action["plan_id"] for action in actions]
        assert "lifetime" in [action["plan_id"] for action in actions]

    def test_get_subscription_status_with_active_subscription(self, client, test_user, auth_headers, db_session):
        """Test getting subscription status with active monthly subscription"""
        # Use date-aligned times to avoid partial day calculations
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        expires_at = current_time + timedelta(days=2)  # Exactly 2 days
        
        # Create active monthly subscription
        subscription = Subscription(
            user_id=test_user.openid,
            plan_id="monthly",
            status="active",
            start_date=current_time,
            expires_at=expires_at
        )
        db_session.add(subscription)
        db_session.commit()
        
        response = client.get("/subscriptions/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["plan_id"] == "monthly"
        assert data["expires_at"] is not None
        assert data["next_expires_at"] is None
        
        # Verify available actions
        actions = data["available_actions"]
        assert len(actions) > 0
        
        # Should have renewal option for current plan
        renewal_action = next((a for a in actions if a["action"] == "renewal"), None)
        assert renewal_action is not None
        assert renewal_action["plan_id"] == "monthly"
        assert renewal_action["credit"] == "0"  # No credit for renewal
        assert renewal_action["payment"] == "9.9"  # Full price for renewal
        
        # Should have upgrade options
        upgrade_actions = [a for a in actions if a["action"] == "upgrade"]
        assert len(upgrade_actions) > 0
        assert all(a["plan_id"] in ["yearly", "lifetime"] for a in upgrade_actions)
        
        # Verify credit calculation for upgrades
        # Exactly 15 days remaining out of 30 days = 50% credit
        expected_credit = Decimal("0.66")  # 9.90 * (2/30)
        for action in upgrade_actions:
            assert Decimal(action["credit"]) == expected_credit, f"Expected credit {expected_credit} but got {action['credit']}"

    def test_subscription_upgrade_from_monthly_to_yearly(self, client, test_user, auth_headers, db_session):
        """Test upgrading from monthly to yearly subscription"""
        # Use date-aligned times to avoid partial day calculations
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        expires_at = current_time + timedelta(days=15)  # Exactly 15 days
        
        # Create active monthly subscription
        subscription = Subscription(
            user_id=test_user.openid,
            plan_id="monthly",
            status="active",
            start_date=current_time,
            expires_at=expires_at
        )
        db_session.add(subscription)
        db_session.commit()
        
        # Add a buffer time to account for database operations and time differences
        buffer_time = timedelta(seconds=2)
        test_start_time = datetime.utcnow()
        
        # Calculate expected credit and payment
        expected_credit = Decimal("4.95")  # 9.90 * (15/30)
        expected_payment = Decimal("99") - expected_credit  # yearly price - credit
        
        # Try to upgrade
        request_data = {
            "action": "upgrade",
            "plan_id": "yearly",
            "payment": str(expected_payment)
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        new_subscription = response.json()
        
        # Get the current time after the request
        test_end_time = datetime.utcnow()
        
        # Verify new subscription is active and properly timed
        assert new_subscription["status"] == "active"
        subscription_start_date = datetime.fromisoformat(new_subscription["start_date"])
        assert test_start_time - buffer_time <= subscription_start_date <= test_end_time + buffer_time, \
            f"Subscription start date {subscription_start_date} not within expected range " \
            f"[{test_start_time - buffer_time} to {test_end_time + buffer_time}]"
        assert datetime.fromisoformat(new_subscription["expires_at"]) > datetime.utcnow()
        assert datetime.fromisoformat(new_subscription["expires_at"]) > expires_at  # New subscription should last longer

        # Verify old subscription is expired and properly timed
        db_session.refresh(subscription)
        assert subscription.status == "expired"
        assert subscription.expires_at <= test_end_time + buffer_time, \
            f"Old subscription expiry {subscription.expires_at} should be before {test_end_time + buffer_time}"

    def test_subscription_renewal_monthly(self, client, test_user, auth_headers, db_session):
        """Test renewing monthly subscription"""
        current_time = datetime.utcnow()
        expires_at = current_time + timedelta(days=2)  # 2 days remaining
        
        # Create active monthly subscription
        subscription = Subscription(
            user_id=test_user.openid,
            plan_id="monthly",
            status="active",
            expires_at=expires_at
        )
        db_session.add(subscription)
        db_session.commit()
        
        # Try to renew
        request_data = {
            "action": "renewal",
            "plan_id": "monthly",
            "payment": "9.9"  # Full price for renewal
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "active"
        assert datetime.fromisoformat(data["start_date"]).date() == datetime.utcnow().date()
        assert datetime.fromisoformat(data["expires_at"]).date() == expires_at.date()
        assert datetime.fromisoformat(data["next_expires_at"]).date() == (expires_at + timedelta(days=30)).date()
        assert data["available_actions"] == []

    def test_invalid_payment_amount(self, client, test_user, auth_headers, db_session):
        """Test attempting to update subscription with incorrect payment amount"""
        # Create active monthly subscription
        subscription = Subscription(
            user_id=test_user.openid,
            plan_id="monthly",
            status="active",
            expires_at=datetime.utcnow() + timedelta(days=15)
        )
        db_session.add(subscription)
        db_session.commit()
        
        # Try to upgrade with incorrect payment amount
        request_data = {
            "action": "upgrade",
            "plan_id": "yearly",
            "payment": "50.00"  # Incorrect payment amount
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 400
        assert "Payment amount mismatch" in response.json()["detail"]

    def test_invalid_action(self, client, test_user, auth_headers, db_session):
        """Test attempting invalid subscription action"""
        # Create active yearly subscription
        subscription = Subscription(
            user_id=test_user.openid,
            plan_id="yearly",
            status="active",
            expires_at=datetime.utcnow() + timedelta(days=300)
        )
        db_session.add(subscription)
        db_session.commit()
        
        # Try to "upgrade" to monthly (not allowed)
        request_data = {
            "action": "upgrade",
            "plan_id": "monthly",
            "payment": "9.9"
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 400
        assert "Invalid action" in response.json()["detail"]

    def test_new_user_gets_trial_subscription(self, test_client, db_session, mock_weixin_auth):
        """Test that new users get a trial subscription by default"""
        # Register a new user through WeChat login
        from app.utils.invitation_code import generate_invite_code
        invite_code = generate_invite_code(datetime.utcnow() + timedelta(days=6))
        response = test_client.post("/weixin/auth/login", json={"code": "test_code", "invite_code": invite_code})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["openid"] == "test_openid"

        # Verify subscription in database
        subscription = db_session.query(Subscription).filter(
            Subscription.user_id == "test_openid"
        ).first()
        assert subscription is not None
        assert subscription.status == "active"
        assert subscription.plan_id == "trial"
        assert subscription.expires_at is not None

    def test_subscription_upgrade_from_trial_to_monthly(self, client, test_user, auth_headers, db_session):
        """Test upgrading from a trial subscription to a monthly subscription"""
        # Create a trial subscription first
        subscription_service = SubscriptionService(db_session)
        subscription_service.create_trial_subscription(test_user.openid)

        # Verify trial subscription exists
        trial_subscription = db_session.query(Subscription).filter(
            Subscription.user_id == test_user.openid,
            Subscription.plan_id == "trial"
        ).first()
        assert trial_subscription is not None
        assert trial_subscription.status == "active"

        # Add a buffer time to account for database operations and time differences
        buffer_time = timedelta(seconds=2)
        test_start_time = datetime.utcnow()

        # Try to create a monthly subscription
        request_data = {
            "action": "upgrade",
            "plan_id": "monthly",
            "payment": "9.9"
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Get the current time after the request
        test_end_time = datetime.utcnow()
        
        assert data["status"] == "active"
        subscription_start_date = datetime.fromisoformat(data["start_date"])
        assert test_start_time - buffer_time <= subscription_start_date <= test_end_time + buffer_time, \
            f"Subscription start date {subscription_start_date} not within expected range " \
            f"[{test_start_time - buffer_time} to {test_end_time + buffer_time}]"
        assert datetime.fromisoformat(data["expires_at"]).date() == (datetime.utcnow() + timedelta(days=30)).date()
        assert data["next_expires_at"] is None
        assert len(data["available_actions"]) > 0

    def test_subscription_upgrade_from_trial_to_yearly(self, client, test_user, auth_headers, db_session):
        """Test upgrading from trial to yearly subscription"""
        # Create a trial subscription first
        subscription_service = SubscriptionService(db_session)
        subscription_service.create_trial_subscription(test_user.openid)

        # Verify trial subscription exists
        trial_subscription = db_session.query(Subscription).filter(
            Subscription.user_id == test_user.openid,
            Subscription.plan_id == "trial"
        ).first()
        assert trial_subscription is not None
        assert trial_subscription.status == "active"

        # Add a buffer time to account for database operations and time differences
        buffer_time = timedelta(seconds=2)
        test_start_time = datetime.utcnow()

        # Try to upgrade to yearly
        request_data = {
            "action": "upgrade",
            "plan_id": "yearly",
            "payment": "99"  # Full price for yearly (no credit for trial)
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Get the current time after the request
        test_end_time = datetime.utcnow()

        # Verify response data
        assert data["status"] == "active"
        subscription_start_date = datetime.fromisoformat(data["start_date"])
        assert test_start_time - buffer_time <= subscription_start_date <= test_end_time + buffer_time, \
            f"Subscription start date {subscription_start_date} not within expected range " \
            f"[{test_start_time - buffer_time} to {test_end_time + buffer_time}]"
        
        # Check expires_at is approximately 365 days from now
        expires_at = datetime.fromisoformat(data["expires_at"])
        expected_expiry = test_end_time + timedelta(days=365)
        assert abs((expires_at - expected_expiry).days) <= 1, \
            f"Expiry date {expires_at} should be about 365 days from {test_end_time}"
            
        assert data["next_expires_at"] is None
        assert len(data["available_actions"]) > 0  # Should have upgrade to lifetime option

        # Verify trial subscription is expired
        db_session.refresh(trial_subscription)
        assert trial_subscription.status == "expired"
        assert trial_subscription.expires_at <= test_end_time + buffer_time, \
            f"Trial subscription expiry {trial_subscription.expires_at} should be before {test_end_time + buffer_time}"

        # Verify available actions include upgrade to lifetime
        upgrade_actions = [a for a in data["available_actions"] if a["action"] == "upgrade"]
        assert len(upgrade_actions) == 1
        assert upgrade_actions[0]["plan_id"] == "lifetime"

    def test_subscription_upgrade_from_trial_to_lifetime(self, client, test_user, auth_headers, db_session):
        """Test upgrading from trial to lifetime subscription"""
        # Create a trial subscription first
        subscription_service = SubscriptionService(db_session)
        subscription_service.create_trial_subscription(test_user.openid)

        # Verify trial subscription exists
        trial_subscription = db_session.query(Subscription).filter(
            Subscription.user_id == test_user.openid,
            Subscription.plan_id == "trial"
        ).first()
        assert trial_subscription is not None
        assert trial_subscription.status == "active"

        # Add a buffer time to account for database operations and time differences
        buffer_time = timedelta(seconds=2)
        test_start_time = datetime.utcnow()

        # Try to upgrade to lifetime
        request_data = {
            "action": "upgrade",
            "plan_id": "lifetime",
            "payment": "19.9"  # Full price for lifetime (no credit for trial)
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Get the current time after the request
        test_end_time = datetime.utcnow()

        # Verify response data
        assert data["status"] == "active"
        subscription_start_date = datetime.fromisoformat(data["start_date"])
        assert test_start_time - buffer_time <= subscription_start_date <= test_end_time + buffer_time, \
            f"Subscription start date {subscription_start_date} not within expected range " \
            f"[{test_start_time - buffer_time} to {test_end_time + buffer_time}]"
        assert datetime.fromisoformat(data["expires_at"]).year >= 2100  # Lifetime expires in the next century
        assert data["next_expires_at"] is None
        assert len(data["available_actions"]) == 0  # No actions available for lifetime

        # Verify trial subscription is expired
        db_session.refresh(trial_subscription)
        assert trial_subscription.status == "expired"
        assert trial_subscription.expires_at <= test_end_time + buffer_time, \
            f"Trial subscription expiry {trial_subscription.expires_at} should be before {test_end_time + buffer_time}"

        # Verify no future subscriptions exist
        future_subscriptions = db_session.query(Subscription).filter(
            Subscription.user_id == test_user.openid,
            Subscription.status.in_(["active", "future"])
        ).all()
        assert len(future_subscriptions) == 1  # Only the lifetime subscription should exist
        assert future_subscriptions[0].plan_id == "lifetime"

    def test_subscription_upgrade_from_monthly_to_lifetime(self, client, test_user, auth_headers, db_session):
        """Test upgrading from monthly to lifetime subscription"""
        # Use date-aligned times to avoid partial day calculations
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        expires_at = current_time + timedelta(days=15)  # Exactly 15 days
        
        # Create active monthly subscription
        subscription = Subscription(
            user_id=test_user.openid,
            plan_id="monthly",
            status="active",
            start_date=current_time,
            expires_at=expires_at
        )
        db_session.add(subscription)
        db_session.commit()
        
        # Add a buffer time to account for database operations and time differences
        buffer_time = timedelta(seconds=2)
        test_start_time = datetime.utcnow()
        
        # Calculate expected credit and payment
        expected_credit = Decimal("4.95")  # 9.90 * (15/30)
        expected_payment = Decimal("19.9") - expected_credit  # lifetime price - credit
        
        # Try to upgrade
        request_data = {
            "action": "upgrade",
            "plan_id": "lifetime",
            "payment": str(expected_payment)
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        new_subscription = response.json()
        
        # Get the current time after the request
        test_end_time = datetime.utcnow()
        
        # Verify new subscription is active and properly timed
        assert new_subscription["status"] == "active"
        subscription_start_date = datetime.fromisoformat(new_subscription["start_date"])
        assert test_start_time - buffer_time <= subscription_start_date <= test_end_time + buffer_time, \
            f"Subscription start date {subscription_start_date} not within expected range " \
            f"[{test_start_time - buffer_time} to {test_end_time + buffer_time}]"
        assert datetime.fromisoformat(new_subscription["expires_at"]).year >= 2100  # Lifetime expires in the next century
        assert len(new_subscription["available_actions"]) == 0  # No actions available for lifetime

        # Verify old subscription is expired and properly timed
        db_session.refresh(subscription)
        assert subscription.status == "expired"
        assert subscription.expires_at <= test_end_time + buffer_time, \
            f"Old subscription expiry {subscription.expires_at} should be before {test_end_time + buffer_time}"

    def test_subscription_upgrade_from_yearly_to_lifetime(self, client, test_user, auth_headers, db_session):
        """Test upgrading from yearly to lifetime subscription"""
        # Use date-aligned times to avoid partial day calculations
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        expires_at = current_time + timedelta(days=180)  # Exactly 180 days (half year)
        
        # Create active yearly subscription
        subscription = Subscription(
            user_id=test_user.openid,
            plan_id="yearly",
            status="active",
            start_date=current_time,
            expires_at=expires_at
        )
        db_session.add(subscription)
        db_session.commit()
        
        # Add a buffer time to account for database operations and time differences
        buffer_time = timedelta(seconds=2)
        test_start_time = datetime.utcnow()
        
        # Calculate expected credit and payment
        expected_credit = Decimal("48.82")  # 99 * (180/365)
        expected_payment = max(Decimal("9.9") - expected_credit, Decimal("0"))  # lifetime price - credit
        
        # Try to upgrade
        request_data = {
            "action": "upgrade",
            "plan_id": "lifetime",
            "payment": str(expected_payment)
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        new_subscription = response.json()
        
        # Get the current time after the request
        test_end_time = datetime.utcnow()
        
        # Verify new subscription is active and properly timed
        assert new_subscription["status"] == "active"
        subscription_start_date = datetime.fromisoformat(new_subscription["start_date"])
        
        # The subscription start date should be within the test execution window (plus buffer)
        assert test_start_time - buffer_time <= subscription_start_date <= test_end_time + buffer_time, \
            f"Subscription start date {subscription_start_date} not within expected range " \
            f"[{test_start_time - buffer_time} to {test_end_time + buffer_time}]"
            
        assert datetime.fromisoformat(new_subscription["expires_at"]).year >= 2100  # Lifetime expires in the next century
        assert len(new_subscription["available_actions"]) == 0  # No actions available for lifetime

        # Verify old subscription is expired and properly timed
        db_session.refresh(subscription)
        assert subscription.status == "expired"
        assert subscription.expires_at <= test_end_time + buffer_time, \
            f"Old subscription expiry {subscription.expires_at} should be before {test_end_time + buffer_time}"

    def test_subscription_renewal_yearly(self, client, test_user, auth_headers, db_session):
        """Test renewing yearly subscription"""
        # Use date-aligned times to avoid partial day calculations
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        expires_at = current_time + timedelta(days=30)  # 30 days remaining
        
        # Create active yearly subscription
        subscription = Subscription(
            user_id=test_user.openid,
            plan_id="yearly",
            status="active",
            start_date=current_time,
            expires_at=expires_at
        )
        db_session.add(subscription)
        db_session.commit()
        
        # Try to renew
        request_data = {
            "action": "renewal",
            "plan_id": "yearly",
            "payment": "99"  # Full price for yearly renewal
        }
        
        response = client.post("/subscriptions/update", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Verify response data
        assert data["status"] == "active"
        assert datetime.fromisoformat(data["start_date"]).date() == datetime.utcnow().date()
        assert datetime.fromisoformat(data["expires_at"]).date() == expires_at.date()
        # Next expiry should be current expiry + 365 days
        assert datetime.fromisoformat(data["next_expires_at"]).date() == (expires_at + timedelta(days=365)).date()
        
        # Verify current subscription remains active until expiry
        db_session.refresh(subscription)
        assert subscription.status == "active"
        assert subscription.expires_at.date() == expires_at.date()
        
        # Verify future subscription is created
        future_subscription = db_session.query(Subscription).filter(
            Subscription.user_id == test_user.openid,
            Subscription.status == "future",
            Subscription.plan_id == "yearly"
        ).first()
        assert future_subscription is not None
        assert future_subscription.start_date.date() == expires_at.date()
        assert future_subscription.expires_at.date() == (expires_at + timedelta(days=365)).date()

    def test_renewal_window_monthly_subscription(self, client, test_user, auth_headers, db_session):
        """Test renewal window for monthly subscription"""
        # Use date-aligned times to avoid partial day calculations
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        test_cases = [
            (4, False),  # 4 days remaining - should NOT show renewal
            (3, True),   # 3 days remaining - should show renewal
            (2, True),   # 2 days remaining - should show renewal
            (1, True),   # 1 day remaining - should show renewal
        ]
        
        for days_remaining, should_show_renewal in test_cases:
            # Create active monthly subscription
            subscription = Subscription(
                user_id=test_user.openid,
                plan_id="monthly",
                status="active",
                start_date=current_time,
                expires_at=current_time + timedelta(days=days_remaining)
            )
            db_session.add(subscription)
            db_session.commit()
            
            response = client.get("/subscriptions/status", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            
            # Check renewal action availability
            renewal_action = next(
                (a for a in data["available_actions"] if a["action"] == "renewal"),
                None
            )
            
            if should_show_renewal:
                assert renewal_action is not None, f"Renewal should be available with {days_remaining} days remaining"
                assert renewal_action["plan_id"] == "monthly"
                assert renewal_action["payment"] == "9.9"
            else:
                assert renewal_action is None, f"Renewal should NOT be available with {days_remaining} days remaining"
            
            # Cleanup for next iteration
            db_session.query(Subscription).delete()
            db_session.commit()

    def test_renewal_window_yearly_subscription(self, client, test_user, auth_headers, db_session):
        """Test renewal window for yearly subscription"""
        # Use date-aligned times to avoid partial day calculations
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        test_cases = [
            (31, False),  # 31 days remaining - should NOT show renewal
            (30, True),   # 30 days remaining - should show renewal
            (15, True),   # 15 days remaining - should show renewal
            (1, True),    # 1 day remaining - should show renewal
        ]
        
        for days_remaining, should_show_renewal in test_cases:
            # Create active yearly subscription
            subscription = Subscription(
                user_id=test_user.openid,
                plan_id="yearly",
                status="active",
                start_date=current_time,
                expires_at=current_time + timedelta(days=days_remaining)
            )
            db_session.add(subscription)
            db_session.commit()
            
            response = client.get("/subscriptions/status", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            
            # Check renewal action availability
            renewal_action = next(
                (a for a in data["available_actions"] if a["action"] == "renewal"),
                None
            )
            
            if should_show_renewal:
                assert renewal_action is not None, f"Renewal should be available with {days_remaining} days remaining"
                assert renewal_action["plan_id"] == "yearly"
                assert renewal_action["payment"] == "99"
            else:
                assert renewal_action is None, f"Renewal should NOT be available with {days_remaining} days remaining"
            
            # Cleanup for next iteration
            db_session.query(Subscription).delete()
            db_session.commit()

    def test_generate_payment_monthly(self, client, test_user, auth_headers, db_session, monkeypatch):
        """Test generating payment info for monthly subscription"""
        monkeypatch.setenv("WEIXIN_APPID", "test_appid")
        monkeypatch.setenv("WEIXIN_MCH_ID", "test_mch_id")
        monkeypatch.setenv("WEIXIN_PAY_API_KEY", "test_api_key")
        monkeypatch.setenv("WEIXIN_PAY_API_V3_KEY", "test_api_v3_key")
        monkeypatch.setenv("WEIXIN_PAY_CERT_SERIAL_NO", "test_cert_serial")
        monkeypatch.setenv("WEIXIN_ENV_ID", "test_env_id")

        # we need to mock request.post
        weixin_response = requests.Response()
        weixin_response.status_code = 200
        weixin_response.json = lambda: {
            "errcode":0,
            "errmsg":"ok",
            "respdata":{
                "return_code":"SUCCESS",
                "return_msg":"OK",
                "appid":"test_appid",
                "mch_id":"test_mch_id",
                "sub_appid":"test_appid",
                "sub_mch_id":"test_mch_id",
                "nonce_str":"test_nonce_str",
                "sign":"test_sign",
                "result_code":"SUCCESS",
                "trade_type":"JSAPI",
                "prepay_id":"test_prepay_id",
                "payment":{
                    "appId":"test_appid",
                    "timeStamp":"1647841885",
                    "nonceStr":"test_nonce_str",
                    "package":"prepay_id=test_prepay_id",
                    "signType":"MD5",
                    "paySign":"test_pay_sign"
                }
            }
        }

        weixin_response.headers = {
            "Content-Type": "application/json"
        }

        # mock requests.post
        mock_post = MagicMock(return_value=weixin_response)
        monkeypatch.setattr("requests.post", mock_post)

        # Request payment info for monthly plan
        request_data = {
            "action": "upgrade",
            "plan_id": "monthly",
            "name": "包月30天",
            "price": "9.9",
            "duration": 30,
            "description": ["订阅后可使用30天"],
            "credit": "0",
            "payment": "9.9"
        }
        
        response = client.post("/subscriptions/payment", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Get the actual call arguments
        call_args = mock_post.call_args

        # Verify the URL
        assert call_args[0][0] == "http://api.weixin.qq.com/_/pay/unifiedorder"

        # Get the JSON payload
        json_payload = call_args[1]["json"]

        # Verify the out_trade_no format using regex
        out_trade_no_pattern = re.compile(r"^upgrade_monthly_\d{10,}$")
        assert out_trade_no_pattern.match(json_payload["out_trade_no"]), \
            f"out_trade_no '{json_payload['out_trade_no']}' doesn't match expected pattern"

        # Verify the rest of the payload
        expected_payload = {
            "body": request_data["name"],
            "openid": test_user.openid,
            "sub_mch_id": "test_mch_id",
            "spbill_create_ip": "127.0.0.1",
            "total_fee": 990,
            "env_id": "test_env_id",
            "callback_type": 2,
            "container": {
                "service": "gluco",
                "path": "/payments/notify"
            }
        }

        # Compare all fields except out_trade_no which we already validated
        for key, value in expected_payload.items():
            assert json_payload[key] == value, f"Mismatch in {key}"

        assert data == weixin_response.json()["respdata"]["payment"]

    def test_generate_payment_with_credit(self, client, test_user, auth_headers, db_session, monkeypatch):
        """Test generating payment info with remaining credit"""
        # Mock WeChat Pay credentials
        monkeypatch.setenv("WEIXIN_APPID", "test_appid")
        monkeypatch.setenv("WEIXIN_MCH_ID", "test_mch_id")
        monkeypatch.setenv("WEIXIN_PAY_API_KEY", "test_api_key")
        monkeypatch.setenv("WEIXIN_PAY_API_V3_KEY", "test_api_v3_key")
        monkeypatch.setenv("WEIXIN_PAY_CERT_SERIAL_NO", "test_cert_serial")
        monkeypatch.setenv("WEIXIN_ENV_ID", "test_env_id")

        # Create active monthly subscription with 15 days remaining
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        subscription = Subscription(
            user_id=test_user.openid,
            plan_id="monthly",
            status="active",
            start_date=current_time,
            expires_at=current_time + timedelta(days=15)  # Exactly 15 days
        )
        db_session.add(subscription)
        db_session.commit()

        # Mock WeChat API response
        weixin_response = requests.Response()
        weixin_response.status_code = 200
        weixin_response.json = lambda: {
            "errcode": 0,
            "errmsg": "ok",
            "respdata": {
                "return_code": "SUCCESS",
                "return_msg": "OK",
                "appid": "test_appid",
                "mch_id": "test_mch_id",
                "sub_appid": "test_appid",
                "sub_mch_id": "test_mch_id",
                "nonce_str": "test_nonce_str",
                "sign": "test_sign",
                "result_code": "SUCCESS",
                "trade_type": "JSAPI",
                "prepay_id": "test_prepay_id",
                "payment": {
                    "appId": "test_appid",
                    "timeStamp": "1647841885",
                    "nonceStr": "test_nonce_str",
                    "package": "prepay_id=test_prepay_id",
                    "signType": "MD5",
                    "paySign": "test_pay_sign"
                }
            }
        }
        weixin_response.headers = {"Content-Type": "application/json"}

        # Mock requests.post
        mock_post = MagicMock(return_value=weixin_response)
        monkeypatch.setattr("requests.post", mock_post)
        
        # Request payment info for yearly upgrade
        request_data = {
            "action": "upgrade",
            "plan_id": "yearly",
            "name": "包年365天",
            "price": "99",
            "duration": 365,
            "description": ["订阅后可使用365天"],
            "credit": "4.95",  # 9.90 * (15/30)
            "payment": "94.05"  # 99 - 4.95
        }
        
        response = client.post("/subscriptions/payment", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Get the actual call arguments
        call_args = mock_post.call_args

        # Verify the URL
        assert call_args[0][0] == "http://api.weixin.qq.com/_/pay/unifiedorder"

        # Get the JSON payload
        json_payload = call_args[1]["json"]

        # Verify the out_trade_no format using regex
        out_trade_no_pattern = re.compile(r"^upgrade_yearly_\d{10,}$")
        assert out_trade_no_pattern.match(json_payload["out_trade_no"]), \
            f"out_trade_no '{json_payload['out_trade_no']}' doesn't match expected pattern"

        # Verify the rest of the payload
        expected_payload = {
            "body": request_data["name"],
            "openid": test_user.openid,
            "sub_mch_id": "test_mch_id",
            "spbill_create_ip": "127.0.0.1",
            "total_fee": 9405,  # 94.05 in cents
            "env_id": "test_env_id",
            "callback_type": 2,
            "container": {
                "service": "gluco",
                "path": "/payments/notify"
            }
        }

        # Compare all fields except out_trade_no which we already validated
        for key, value in expected_payload.items():
            assert json_payload[key] == value, f"Mismatch in {key}"

        assert data == weixin_response.json()["respdata"]["payment"]

    def test_generate_payment_invalid_action(self, client, test_user, auth_headers, db_session, monkeypatch):
        """Test generating payment info with invalid action"""
        # Mock WeChat Pay credentials
        monkeypatch.setenv("WEIXIN_APPID", "test_appid")
        monkeypatch.setenv("WEIXIN_MCH_ID", "test_mch_id")
        monkeypatch.setenv("WEIXIN_PAY_API_KEY", "test_api_key")
        monkeypatch.setenv("WEIXIN_PAY_API_V3_KEY", "test_api_v3_key")
        monkeypatch.setenv("WEIXIN_PAY_CERT_SERIAL_NO", "test_cert_serial")
        monkeypatch.setenv("WEIXIN_ENV_ID", "test_env_id")

        # Mock WeChat API response
        weixin_response = requests.Response()
        weixin_response.status_code = 200
        weixin_response.json = lambda: {
            "errcode": 0,
            "errmsg": "ok",
            "respdata": {
                "return_code": "SUCCESS",
                "return_msg": "OK",
                "appid": "test_appid",
                "mch_id": "test_mch_id",
                "sub_appid": "test_appid",
                "sub_mch_id": "test_mch_id",
                "nonce_str": "test_nonce_str",
                "sign": "test_sign",
                "result_code": "SUCCESS",
                "trade_type": "JSAPI",
                "prepay_id": "test_prepay_id",
                "payment": {
                    "appId": "test_appid",
                    "timeStamp": "1647841885",
                    "nonceStr": "test_nonce_str",
                    "package": "prepay_id=test_prepay_id",
                    "signType": "MD5",
                    "paySign": "test_pay_sign"
                }
            }
        }
        weixin_response.headers = {"Content-Type": "application/json"}

        # Mock requests.post
        mock_post = MagicMock(return_value=weixin_response)
        monkeypatch.setattr("requests.post", mock_post)
        
        # Try to generate payment with invalid action
        request_data = {
            "action": "invalid",
            "plan_id": "monthly",
            "name": "包月30天",
            "price": "9.9",
            "duration": 30,
            "description": ["订阅后可使用30天"],
            "credit": "0",
            "payment": "9.9"
        }
        
        response = client.post("/subscriptions/payment", json=request_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Get the actual call arguments
        call_args = mock_post.call_args

        # Verify the URL
        assert call_args[0][0] == "http://api.weixin.qq.com/_/pay/unifiedorder"

        # Get the JSON payload
        json_payload = call_args[1]["json"]

        # Verify the out_trade_no format using regex
        out_trade_no_pattern = re.compile(r"^invalid_monthly_\d{10,}$")
        assert out_trade_no_pattern.match(json_payload["out_trade_no"]), \
            f"out_trade_no '{json_payload['out_trade_no']}' doesn't match expected pattern"

        # Verify the rest of the payload
        expected_payload = {
            "body": request_data["name"],
            "openid": test_user.openid,
            "sub_mch_id": "test_mch_id",
            "spbill_create_ip": "127.0.0.1",
            "total_fee": 990,  # 9.90 in cents
            "env_id": "test_env_id",
            "callback_type": 2,
            "container": {
                "service": "gluco",
                "path": "/payments/notify"
            }
        }

        # Compare all fields except out_trade_no which we already validated
        for key, value in expected_payload.items():
            assert json_payload[key] == value, f"Mismatch in {key}"

        assert data == weixin_response.json()["respdata"]["payment"]

    def test_existing_user_gets_trial_if_no_history(self, test_client, db_session, mock_weixin_auth):
        """Test that existing users without subscription history get a trial subscription during login"""
        # First create a user without subscription
        user = WeixinUser(openid="test_openid")
        db_session.add(user)
        db_session.commit()

        # Verify no subscription exists
        subscription = db_session.query(Subscription).filter(
            Subscription.user_id == "test_openid"
        ).first()
        assert subscription is None

        # Override get_db to use our test session
        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db

        try:
            # Login with the user
            response = test_client.post("/weixin/auth/login", json={"code": "test_code"})
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["user"]["openid"] == "test_openid"

            # Ensure changes are committed
            db_session.commit()

            # Verify trial subscription was created
            subscription = db_session.query(Subscription).filter(
                Subscription.user_id == "test_openid"
            ).first()
            assert subscription is not None
            assert subscription.status == "active"
            assert subscription.plan_id == "trial"
            assert subscription.expires_at is not None
        finally:
            app.dependency_overrides.clear()

    def test_existing_user_with_history_no_trial(self, test_client, db_session, mock_weixin_auth):
        """Test that existing users with subscription history don't get a trial subscription during login"""
        # First create a user with an expired subscription
        user = WeixinUser(openid="test_openid")
        db_session.add(user)
        
        # Add an expired subscription
        subscription = Subscription(
            user_id="test_openid",
            plan_id="monthly",
            status="expired",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        db_session.add(subscription)
        db_session.commit()

        # Login with the user
        response = test_client.post("/weixin/auth/login", json={"code": "test_code"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["openid"] == "test_openid"

        # Verify no new trial subscription was created
        subscriptions = db_session.query(Subscription).filter(
            Subscription.user_id == "test_openid"
        ).all()
        assert len(subscriptions) == 1  # Only the original expired subscription
        assert subscriptions[0].status == "expired"
        assert subscriptions[0].plan_id == "monthly"
