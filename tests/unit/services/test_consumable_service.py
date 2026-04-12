import pytest
from unittest.mock import patch, MagicMock
from app.services.consumable_service import ConsumableService

class TestConsumableService:
    """Test suite for the ConsumableService class"""

    @patch('app.services.consumable_service.mongodb')
    def test_get_statistics_success(self, mock_mongodb):
        """Test that get_statistics correctly calculates counts and groupings"""

        # Mock aggregation result
        mock_mongodb.aggregate.return_value = [
            {
                'total': [{'count': 5}],
                'categories': [
                    {'_id': 'Cat1', 'count': 2},
                    {'_id': 'Cat2', 'count': 2},
                    {'_id': 'Keine Kategorie', 'count': 1}
                ],
                'locations': [
                    {'_id': 'Loc1', 'count': 2},
                    {'_id': 'Loc2', 'count': 1},
                    {'_id': 'Loc3', 'count': 1},
                    {'_id': 'Kein Standort', 'count': 1}
                ],
                'stock_levels': [
                    {
                        'sufficient': 3,
                        'warning': 1,
                        'critical': 1
                    }
                ]
            }
        ]

        # Check if the service uses g
        with patch('app.services.consumable_service.g', MagicMock(current_department='TestDept')):
            stats = ConsumableService.get_statistics()

        assert stats['total_consumables'] == 5
        assert stats['categories']['Cat1'] == 2
        assert stats['categories']['Keine Kategorie'] == 1
        assert stats['locations']['Loc1'] == 2
        assert stats['stock_levels']['sufficient'] == 3
        assert stats['stock_levels']['warning'] == 1
        assert stats['stock_levels']['critical'] == 1
        assert '_id' not in stats['stock_levels']

    @patch('app.services.consumable_service.mongodb')
    def test_get_statistics_empty(self, mock_mongodb):
        """Test get_statistics with no consumables"""
        mock_mongodb.aggregate.return_value = [
            {
                'total': [],
                'categories': [],
                'locations': [],
                'stock_levels': []
            }
        ]

        with patch('app.services.consumable_service.g', MagicMock(current_department='TestDept')):
            stats = ConsumableService.get_statistics()

        assert stats['total_consumables'] == 0
        assert stats['categories'] == {}
        assert stats['locations'] == {}
        assert stats['stock_levels'] == {'sufficient': 0, 'warning': 0, 'critical': 0}

    @patch('app.services.consumable_service.mongodb')
    def test_get_statistics_exception(self, mock_mongodb):
        """Test get_statistics with database error"""
        mock_mongodb.aggregate.side_effect = Exception("DB Error")

        with patch('app.services.consumable_service.g', MagicMock(current_department='TestDept')):
            stats = ConsumableService.get_statistics()

        assert stats['total_consumables'] == 0
        assert stats['stock_levels'] == {'sufficient': 0, 'warning': 0, 'critical': 0}
