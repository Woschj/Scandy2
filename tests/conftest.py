"""
Pytest configuration and shared fixtures for Scandy tests.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import mongomock
from flask import Flask

# Set test environment
os.environ['FLASK_ENV'] = 'testing'
os.environ['MONGODB_DB'] = 'scandy_test'


@pytest.fixture(scope='session')
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_mongo():
    """Mock MongoDB client for testing."""
    with patch('app.models.mongodb_database.MongoClient') as mock_client:
        mock_db = Mock()
        mock_client.return_value.db = mock_db
        yield mock_db


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    from app.config import get_config

    config = get_config('testing')
    flask_config = config.to_flask_config()

    app = Flask(__name__)
    app.config.update(flask_config)

    # Initialize minimal app components for testing
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()


@pytest.fixture
def sample_user():
    """Sample user data for tests."""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'role': 'user',
        'active': True
    }


@pytest.fixture
def sample_ticket():
    """Sample ticket data for tests."""
    return {
        'title': 'Test Ticket',
        'description': 'This is a test ticket',
        'status': 'offen',
        'priority': 'normal',
        'created_by': 'testuser',
        'category': 'support'
    }


@pytest.fixture
def sample_tool():
    """Sample tool data for tests."""
    return {
        'name': 'Test Tool',
        'barcode': 'ABC123456',
        'category': 'hand_tools',
        'status': 'available',
        'location': 'warehouse_a'
    }


@pytest.fixture(autouse=True)
def clean_mongo_collections(mock_mongo):
    """Clean all MongoDB collections before each test."""
    if hasattr(mock_mongo, 'reset_mock'):
        mock_mongo.reset_mock()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "security: Security-related tests")
    config.addinivalue_line("markers", "database: Database-related tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on path."""
    for item in items:
        # Add markers based on file path
        if 'unit' in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif 'integration' in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add database marker for database-related tests
        if 'database' in item.name.lower() or 'mongo' in item.name.lower():
            item.add_marker(pytest.mark.database)


def assert_response_status(response, expected_status=200):
    """Helper to assert response status with detailed error message."""
    assert response.status_code == expected_status, \
        f"Expected status {expected_status}, got {response.status_code}. Response: {response.data.decode()}"


def assert_json_response(response, expected_keys=None):
    """Helper to assert JSON response structure."""
    assert response.content_type == 'application/json', \
        f"Expected JSON response, got {response.content_type}"

    data = response.get_json()
    assert data is not None, "Response is not valid JSON"

    if expected_keys:
        for key in expected_keys:
            assert key in data, f"Expected key '{key}' not found in response"

    return data
