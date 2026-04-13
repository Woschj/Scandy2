
import pytest
from unittest.mock import patch, MagicMock
from app.services.consumable_service import ConsumableService

class TestConsumableServiceStats:
    """Test suite for the optimized ConsumableService.get_statistics"""

    @patch('app.services.consumable_service.mongodb.aggregate')
    def test_get_statistics_success(self, mock_aggregate):
        """Test happy path for statistics calculation using aggregation"""
        # Mock the aggregated results from MongoDB
        mock_aggregate.return_value = [{
            'base_counts': [{
                'total': 10,
                'sufficient': 7,
                'warning': 2,
                'critical': 1
            }],
            'categories': [
                {'_id': 'Werkzeug', 'count': 5},
                {'_id': 'Elektronik', 'count': 5}
            ],
            'locations': [
                {'_id': 'Lager A', 'count': 10}
            ]
        }]

        # Set department in g mock if necessary, though current implementation handles it
        with patch('app.services.consumable_service.g') as mock_g:
            mock_g.current_department = 'IT'
            result = ConsumableService.get_statistics()

        # Verify results
        assert result['total_consumables'] == 10
        assert result['stock_levels']['sufficient'] == 7
        assert result['stock_levels']['warning'] == 2
        assert result['stock_levels']['critical'] == 1
        assert result['categories']['Werkzeug'] == 5
        assert result['locations']['Lager A'] == 10

        # Verify aggregation was called correctly
        assert mock_aggregate.called
        args, kwargs = mock_aggregate.call_args
        assert args[0] == 'consumables'
        pipeline = args[1]
        assert pipeline[0]['$match']['department'] == 'IT'

    @patch('app.services.consumable_service.mongodb.aggregate')
    def test_get_statistics_empty(self, mock_aggregate):
        """Test behavior when no consumables are found"""
        mock_aggregate.return_value = [{'base_counts': [], 'categories': [], 'locations': []}]

        result = ConsumableService.get_statistics()

        assert result['total_consumables'] == 0
        assert result['categories'] == {}
        assert result['stock_levels']['sufficient'] == 0

    @patch('app.services.consumable_service.mongodb.aggregate')
    def test_get_statistics_exception(self, mock_aggregate):
        """Test behavior when an exception occurs"""
        mock_aggregate.side_effect = Exception("DB Error")

        result = ConsumableService.get_statistics()

        assert result['total_consumables'] == 0
        assert result['categories'] == {}
