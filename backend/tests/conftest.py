"""Test configuration and fixtures."""
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.dependencies import get_db
from app.main import app
import os


# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def set_test_database(monkeypatch):
    """Set test database environment variable before any imports occur."""
    # Set the test database URL to be used during tests.
    test_db_url = "mysql+pymysql://root@localhost:3306/gluco_test"
    monkeypatch.setenv("DATABASE_URL", test_db_url)


@pytest.fixture(scope="function")
def test_db() -> Session:
    """Create a fresh test database for each test."""
    # Create test database engine
    test_db_url = os.getenv("DATABASE_URL")
    assert "gluco_test" in test_db_url, f"Wrong database! Using {test_db_url} instead of test database"
    
    engine = create_engine(test_db_url)

    try:
        from app.database.database import Base

        # Create all tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        # Create a new session
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )
        db = TestingSessionLocal()

        # Override the get_db dependency
        def override_get_db():
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    """Create a test client."""
    from fastapi.testclient import TestClient

    return TestClient(app)


# Add a fixture to set dummy environment variables required by the OpenAI client
@pytest.fixture(autouse=True)
def set_dummy_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_api_key")
    monkeypatch.setenv("OPENAI_BASE_URL", "dummy_base_url")
    monkeypatch.setenv("OPENAI_VISION_API_KEY", "dummy_vision_api_key")
    monkeypatch.setenv("OPENAI_VISION_BASE_URL", "dummy_vision_base_url")
    monkeypatch.setenv("OPENAI_MODEL", "dummy_model")
    monkeypatch.setenv("OPENAI_VISION_MODEL", "dummy_vision_model")
    monkeypatch.setenv("OPENAI_MAX_TOKENS", "1000")
    monkeypatch.setenv("OPENAI_VISION_MAX_TOKENS", "1000")


@pytest.fixture(autouse=True)
def patch_openai_init(monkeypatch):
    monkeypatch.setattr(
        "app.utils.gpt_client.OpenAI.__init__", lambda *args, **kwargs: None
    )