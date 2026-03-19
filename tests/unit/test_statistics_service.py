import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.services.statistics_service import StatisticsService

class TestStatisticsService:
    """Test suite for the StatisticsService class"""

    @patch('app.services.statistics_service.mongodb.aggregate')
    def test_get_overdue_loans_success(self, mock_aggregate):
        """Test happy path for overdue loans calculation: correctly identifies and sorts overdue loans"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        tomorrow = today + timedelta(days=1)

        # Mock the aggregated results from MongoDB
        # Note: In production, the aggregation pipeline would filter out 'tomorrow'.
        # Since we are mocking the aggregate result, we should only provide overdue items.
        mock_aggregate.return_value = [
            {
                'tool_barcode': 'T1',
                'worker_barcode': 'W1',
                'expected_return_date': yesterday,
                'tool_info': {'name': 'Hammer'},
                'worker_info': {
                    'firstname': 'Max', 'lastname': 'Mustermann', 'deleted': False
                },
                'lent_at': today - timedelta(days=5)
            },
            {
                'tool_barcode': 'T3',
                'worker_barcode': 'W3',
                'expected_return_date': two_days_ago,  # 2 days overdue
                'tool_info': {'name': 'Säge'},
                'worker_info': {
                    'firstname': 'Lars', 'lastname': 'Müller', 'deleted': False
                },
                'lent_at': today - timedelta(days=5)
            }
        ]

        result = StatisticsService._get_overdue_loans()

        # Verify only overdue loans are returned
        assert len(result) == 2

        # Verify sorting (most overdue first)
        assert result[0]['tool_barcode'] == 'T3'
        assert result[0]['days_overdue'] == 2

        assert result[1]['tool_barcode'] == 'T1'
        assert result[1]['days_overdue'] == 1

        # Verify formatting and mapping of info
        assert result[0]['tool_name'] == 'Säge'
        assert result[0]['worker_name'] == 'Lars Müller'

    @patch('app.services.statistics_service.mongodb.aggregate')
    def test_get_overdue_loans_string_date(self, mock_aggregate):
        """Test processing of string-formatted expected return date and missing tool/worker info"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')

        # Mock string date and missing tool/worker info (e.g., if deleted from DB but lending exists)
        mock_aggregate.return_value = [
            {
                'tool_barcode': 'T1',
                'expected_return_date': yesterday_str,
                'tool_info': None,
                'worker_info': None
            }
        ]

        result = StatisticsService._get_overdue_loans()

        # Verify date string was parsed correctly and is identified as overdue
        assert len(result) == 1
        assert result[0]['days_overdue'] == 1

        # Verify fallback names for missing info
        assert result[0]['tool_name'] == 'Unbekanntes Werkzeug'
        assert result[0]['worker_name'] == 'Unbekannt'

    @patch('app.services.statistics_service.mongodb.aggregate')
    def test_get_overdue_loans_invalid_string_date(self, mock_aggregate):
        """Test skipping of records with invalid date string formats"""
        mock_aggregate.return_value = [
            {
                'tool_barcode': 'T1',
                'expected_return_date': 'invalid-date-format',
                'tool_info': None,
                'worker_info': None
            }
        ]

        result = StatisticsService._get_overdue_loans()

        # Verify record is skipped due to ValueError
        assert len(result) == 0

    @patch('app.services.statistics_service.mongodb.aggregate')
    def test_get_overdue_loans_deleted_worker(self, mock_aggregate):
        """Test handling of soft-deleted workers"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        mock_aggregate.return_value = [
            {
                'tool_barcode': 'T1',
                'worker_barcode': 'W1',
                'expected_return_date': yesterday,
                'tool_info': {'name': 'Hammer'},
                'worker_info': {'firstname': 'Max', 'lastname': 'Mustermann', 'deleted': True}
            }
        ]

        result = StatisticsService._get_overdue_loans()

        assert len(result) == 1
        # Worker is marked as deleted, should use the fallback name 'Unbekannt'
        assert result[0]['worker_name'] == 'Unbekannt'

    @patch('app.services.statistics_service.mongodb.aggregate')
    def test_get_overdue_loans_exception(self, mock_aggregate):
        """Test behavior when an exception occurs during execution (e.g. DB error)"""
        mock_aggregate.side_effect = Exception("DB Connection Error")

        # The function has a top-level try-except block, should return empty list
        result = StatisticsService._get_overdue_loans()

        assert result == []

    @patch('app.services.statistics_service.mongodb.aggregate')
    def test_get_overdue_loans_missing_expected_date(self, mock_aggregate):
        """Test handling of documents missing the expected_return_date field or having it as None"""
        mock_aggregate.return_value = [
            {
                'tool_barcode': 'T1',
                'worker_barcode': 'W1',
                # No expected_return_date
                'tool_info': {'name': 'Hammer'},
                'worker_info': {'firstname': 'Max', 'lastname': 'Mustermann', 'deleted': False}
            },
            {
                'tool_barcode': 'T2',
                'worker_barcode': 'W2',
                'expected_return_date': None,
                'tool_info': {'name': 'Zange'},
                'worker_info': {'firstname': 'Max', 'lastname': 'Mustermann', 'deleted': False}
            }
        ]

        result = StatisticsService._get_overdue_loans()

        # Verify both records are correctly skipped
        assert len(result) == 0
