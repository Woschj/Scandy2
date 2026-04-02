
import pytest
from unittest.mock import patch, MagicMock
from app.services.consumable_service import ConsumableService

class TestConsumableServiceStats:

    @patch('app.services.consumable_service.mongodb.aggregate')
    def test_get_statistics_success(self, mock_aggregate, app):
        # Mock aggregation result
        mock_aggregate.return_value = [{
            'total': [{'count': 10}],
            'categories': [
                {'category': 'Cat1', 'count': 6},
                {'category': 'Cat2', 'count': 4}
            ],
            'locations': [
                {'location': 'Loc1', 'count': 10}
            ],
            'stock_levels': [{
                'sufficient': 5,
                'warning': 3,
                'critical': 2
            }]
        }]

        with app.test_request_context():
            from flask import g
            g.current_department = "TestDept"
            stats = ConsumableService.get_statistics()

        assert stats['total_consumables'] == 10
        assert stats['categories'] == {'Cat1': 6, 'Cat2': 4}
        assert stats['locations'] == {'Loc1': 10}
        assert stats['stock_levels'] == {'sufficient': 5, 'warning': 3, 'critical': 2}

        # Verify aggregation call
        args, kwargs = mock_aggregate.call_args
        assert args[0] == 'consumables'
        pipeline = args[1]
        assert pipeline[0]['$match']['department'] == "TestDept"

    @patch('app.services.consumable_service.mongodb.aggregate')
    def test_get_statistics_empty(self, mock_aggregate, app):
        mock_aggregate.return_value = []

        with app.test_request_context():
            from flask import g
            g.current_department = None
            stats = ConsumableService.get_statistics()

        assert stats['total_consumables'] == 0
        assert stats['categories'] == {}

    @patch('app.services.consumable_service.mongodb.aggregate')
    def test_get_statistics_exception(self, mock_aggregate, app):
        mock_aggregate.side_effect = Exception("DB Error")

        with app.test_request_context():
            from flask import g
            g.current_department = None
            stats = ConsumableService.get_statistics()

        assert stats['total_consumables'] == 0
