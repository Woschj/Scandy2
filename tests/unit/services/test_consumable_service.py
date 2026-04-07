
import pytest
from unittest.mock import patch, MagicMock
from app.services.consumable_service import ConsumableService

class TestConsumableService:
    """Test suite for the ConsumableService class"""

    @patch('app.services.consumable_service.mongodb.aggregate')
    @patch('app.services.consumable_service.g')
    def test_get_statistics_success(self, mock_g, mock_aggregate):
        """Test happy path for consumable statistics: correctly parses aggregation result"""
        mock_g.current_department = 'TestDept'

        # Mock aggregation result from MongoDB
        mock_aggregate.return_value = [
            {
                'total': [{'count': 10}],
                'categories': [
                    {'_id': 'Category A', 'count': 6},
                    {'_id': 'Category B', 'count': 4}
                ],
                'locations': [
                    {'_id': 'Location 1', 'count': 10}
                ],
                'stock_levels': [
                    {
                        'sufficient': 5,
                        'warning': 3,
                        'critical': 2
                    }
                ]
            }
        ]

        result = ConsumableService.get_statistics()

        assert result['total_consumables'] == 10
        assert result['categories']['Category A'] == 6
        assert result['categories']['Category B'] == 4
        assert result['locations']['Location 1'] == 10
        assert result['stock_levels']['sufficient'] == 5
        assert result['stock_levels']['warning'] == 3
        assert result['stock_levels']['critical'] == 2
        assert '_id' not in result['stock_levels']

    @patch('app.services.consumable_service.mongodb.aggregate')
    @patch('app.services.consumable_service.g')
    def test_get_statistics_empty(self, mock_g, mock_aggregate):
        """Test handling of empty collection or no results"""
        mock_g.current_department = 'TestDept'
        mock_aggregate.return_value = [
            {
                'total': [],
                'categories': [],
                'locations': [],
                'stock_levels': []
            }
        ]

        result = ConsumableService.get_statistics()

        assert result['total_consumables'] == 0
        assert result['categories'] == {}
        assert result['locations'] == {}
        assert result['stock_levels'] == {'sufficient': 0, 'warning': 0, 'critical': 0}

    @patch('app.services.consumable_service.mongodb.aggregate')
    @patch('app.services.consumable_service.g')
    def test_get_statistics_exception(self, mock_g, mock_aggregate):
        """Test behavior when an exception occurs during aggregation"""
        mock_g.current_department = 'TestDept'
        mock_aggregate.side_effect = Exception("DB Error")

        result = ConsumableService.get_statistics()

        # Should return fallback stats
        assert result['total_consumables'] == 0
        assert result['categories'] == {}
        assert result['stock_levels'] == {'sufficient': 0, 'warning': 0, 'critical': 0}
