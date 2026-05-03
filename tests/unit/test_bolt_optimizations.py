
import pytest
from unittest.mock import patch, MagicMock
from app.utils.performance_optimizer import QueryOptimizer, IndexOptimizer

class TestQueryOptimizer:
    @patch('app.utils.performance_optimizer.mongodb')
    def test_get_dashboard_statistics_optimized_success(self, mock_mongodb):
        # Mock responses for the 4 calls
        mock_mongodb.aggregate.side_effect = [
            # Tools
            [{'total': 10, 'available': 5, 'lent': 3, 'defect': 2}],
            # Consumables
            [{'total': 20, 'sufficient': 10, 'warning': 5, 'critical': 5}],
            # Workers
            [{
                'total': [{'count': 15}],
                'by_dept': [{'_id': 'IT', 'count': 10}, {'_id': None, 'count': 5}]
            }]
        ]
        mock_mongodb.count_documents.return_value = 8 # active lendings

        stats = QueryOptimizer.get_dashboard_statistics_optimized()

        assert stats['tool_stats']['total'] == 10
        assert stats['tool_stats']['available'] == 5
        assert stats['consumable_stats']['total'] == 20
        assert stats['worker_stats']['total'] == 15
        assert stats['worker_stats']['by_department'][0]['name'] == 'IT'
        assert stats['worker_stats']['by_department'][1]['name'] == 'Ohne Abteilung'
        assert stats['lending_stats']['active'] == 8

    @patch('app.utils.performance_optimizer.mongodb')
    @patch('app.utils.performance_optimizer.QueryOptimizer._get_dashboard_statistics_fallback', create=True)
    def test_get_dashboard_statistics_optimized_exception(self, mock_fallback, mock_mongodb):
        mock_mongodb.aggregate.side_effect = Exception("DB Error")
        mock_fallback.return_value = {"fallback": "data"}

        # We need to mock IndexOptimizer._get_dashboard_statistics_fallback if it is called
        with patch('app.utils.performance_optimizer.IndexOptimizer._get_dashboard_statistics_fallback', return_value={"fallback": "data"}, create=True):
            stats = QueryOptimizer.get_dashboard_statistics_optimized()

        assert stats == {"fallback": "data"}
