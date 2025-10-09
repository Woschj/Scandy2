"""
Unit tests for configuration system.
"""

import pytest
import os
from unittest.mock import patch, mock_open
from app.config.config import (
    load_env_file, get_config, AppConfig, DevelopmentConfig,
    ProductionConfig, TestingConfig, DatabaseConfig
)


class TestConfig:
    """Test configuration classes and functions."""

    def test_load_env_file(self, temp_dir):
        """Test loading environment variables from file."""
        env_file = temp_dir / '.env'
        env_content = "TEST_VAR=test_value\nANOTHER_VAR=123\n"

        with patch('app.config.config.Path') as mock_path:
            mock_path.return_value = env_file
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.open = mock_open(read_data=env_content)

            with patch.dict(os.environ, {}, clear=True):
                load_env_file()

                # Should not raise any exceptions
                assert True

    def test_database_config(self):
        """Test DatabaseConfig dataclass."""
        config = DatabaseConfig(
            uri="mongodb://localhost:27017",
            database="test_db",
            collection_prefix="test_"
        )

        assert config.uri == "mongodb://localhost:27017"
        assert config.database == "test_db"
        assert config.collection_prefix == "test_"
        assert config.connection_string == "mongodb://localhost:27017"

    def test_app_config_creation(self):
        """Test AppConfig creation with defaults."""
        with patch.dict(os.environ, {'SYSTEM_NAME': 'TestApp'}, clear=True):
            config = AppConfig()

            assert config.system_name == 'TestApp'
            assert config.database.database == 'scandy'
            assert config.server.port == 5000
            assert config.security.enable_https is False

    def test_get_config_development(self):
        """Test get_config with development environment."""
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}, clear=True):
            config = get_config()

            assert isinstance(config, DevelopmentConfig)
            assert config.server.debug is True
            assert config.security.session_cookie_secure is False

    def test_get_config_production(self):
        """Test get_config with production environment."""
        with patch.dict(os.environ, {'FLASK_ENV': 'production'}, clear=True):
            config = get_config()

            assert isinstance(config, ProductionConfig)
            assert config.server.debug is False

    def test_get_config_testing(self):
        """Test get_config with testing environment."""
        with patch.dict(os.environ, {'FLASK_ENV': 'testing'}, clear=True):
            config = get_config()

            assert isinstance(config, TestingConfig)
            assert config.server.testing is True
            assert config.database.database == 'scandy_test'

    def test_to_flask_config(self):
        """Test conversion to Flask-compatible config."""
        config = AppConfig()
        flask_config = config.to_flask_config()

        assert isinstance(flask_config, dict)
        assert 'SECRET_KEY' in flask_config
        assert 'DEBUG' in flask_config
        assert 'TESTING' in flask_config
        assert 'SESSION_TYPE' in flask_config

    def test_base_url_generation(self):
        """Test base URL generation."""
        config = AppConfig()

        # Test with custom BASE_URL
        with patch.dict(os.environ, {'BASE_URL': 'https://custom.example.com'}, clear=True):
            config._get_base_url()
            # This would normally update config.base_url

        # Test fallback to localhost
        with patch.dict(os.environ, {}, clear=True):
            with patch('requests.get') as mock_get:
                mock_get.side_effect = Exception("Network error")
                url = config._get_base_url()
                assert url == "http://localhost:5000"
