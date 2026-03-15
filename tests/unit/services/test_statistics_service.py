import pytest
from unittest.mock import patch
from app.services.statistics_service import StatisticsService

def test_get_notices_error_handling(app):
    """Test that get_notices returns an empty list and logs an error when a database exception occurs."""
    with app.app_context():
        # Mock the find call to raise an Exception
        with patch('app.services.statistics_service.mongodb.find') as mock_find:
            mock_find.side_effect = Exception("Mocked database error")

            with patch('app.services.statistics_service.logger.error') as mock_logger:
                notices = StatisticsService.get_notices()

                # Should return an empty list on error
                assert notices == []

                # Should log the error
                mock_logger.assert_called_once_with("Fehler beim Laden der Hinweise: [Interner Fehler]")
