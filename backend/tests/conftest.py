import pytest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path so we can import backend correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.main import app
from backend.app.config import settings
from backend.app.database import get_database, MockDatabase

@pytest.fixture(autouse=True)
def setup_test_directories():
    # Override settings for tests to use a temporary reporting/email directory
    settings.MAILBOX_DIR = str(Path(settings.MAILBOX_DIR).parent / "test_sent_emails")
    settings.REPORTS_DIR = str(Path(settings.REPORTS_DIR).parent / "test_reports")
    settings.EMAIL_TO = "operators@smartwindfarm.ai"
    
    os.makedirs(settings.MAILBOX_DIR, exist_ok=True)
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    yield
    # Clean up test directories
    import shutil
    if os.path.exists(settings.MAILBOX_DIR):
        shutil.rmtree(settings.MAILBOX_DIR, ignore_errors=True)
    if os.path.exists(settings.REPORTS_DIR):
        shutil.rmtree(settings.REPORTS_DIR, ignore_errors=True)

@pytest.fixture
def mock_db(monkeypatch):
    """Force use of MockDatabase during testing."""
    test_db = MockDatabase()
    
    def mock_get_database():
        return test_db
        
    monkeypatch.setattr("backend.app.database.get_database", mock_get_database)
    monkeypatch.setattr("backend.app.main.get_database", mock_get_database)
    return test_db

@pytest.fixture
def client(mock_db):
    """FastAPI test client fixture."""
    with TestClient(app) as c:
        yield c
