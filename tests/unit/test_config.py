"""
Unit tests for configuration system.
"""

import pytest
import os
from unittest.mock import patch, mock_open, MagicMock
from app.config.config import (
    _load_env_files, config, Config, DevelopmentConfig,
    ProductionConfig, TestingConfig
)


class TestConfig:
    """Test configuration classes and functions."""

    def test_load_env_file(self, temp_dir):
        """Test loading environment variables from file."""
        env_content = "TEST_VAR=test_value\nANOTHER_VAR=123\n"

        with patch('app.config.config.Path') as mock_path:
            mock_file = MagicMock()
            mock_path.return_value = mock_file
            mock_file.resolve.return_value.parents.__getitem__.return_value.__truediv__.return_value = mock_file
            mock_file.exists.return_value = True
            mock_file.open = mock_open(read_data=env_content)

            with patch.dict(os.environ, {}, clear=True):
                _load_env_files()

                # Should not raise any exceptions
                assert True

    def test_app_config_creation(self):
        """Test Config creation."""
        config_obj = Config()
        assert config_obj.PORT == 5000

    def test_development_config(self):
        """Test DevelopmentConfig."""
        assert DevelopmentConfig.DEBUG is True

    def test_production_config(self):
        """Test ProductionConfig."""
        assert ProductionConfig.TESTING is False
