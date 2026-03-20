import pytest
from unittest.mock import MagicMock
from app.utils.performance_optimizer import QueryOptimizer

class TestPerformanceOptimizer:
    """Tests for the QueryOptimizer class"""

    def test_get_dashboard_statistics_optimized_structure(self, monkeypatch):
        """Test the structure of the returned statistics from optimized method"""
        # Mock mongodb object
        mock_mongodb = MagicMock()

        # Mock aggregate returns
        mock_mongodb.aggregate.side_effect = [
            # Tool result
            [{'total': 10, 'available': 5, 'lent': 3, 'defect': 2}],
            # Consumable result
            [{'total': 20, 'sufficient': 10, 'warning': 5, 'critical': 5}]
        ]

        # Mock count_documents returns
        mock_mongodb.count_documents.side_effect = [
            # Workers total
            15,
            # Lendings active
            8
        ]

        monkeypatch.setattr('app.utils.performance_optimizer.mongodb', mock_mongodb)

        stats = QueryOptimizer.get_dashboard_statistics_optimized()

        # Verify calls
        assert mock_mongodb.aggregate.call_count == 2
        assert mock_mongodb.count_documents.call_count == 2

        # Verify tool stats call params
        args, kwargs = mock_mongodb.aggregate.call_args_list[0]
        assert args[0] == 'tools'

        # Verify consumable stats call params
        args, kwargs = mock_mongodb.aggregate.call_args_list[1]
        assert args[0] == 'consumables'

        # Verify structure
        assert 'tool_stats' in stats
        assert 'consumable_stats' in stats
        assert 'worker_stats' in stats
        assert 'lending_stats' in stats

        assert stats['tool_stats']['total'] == 10
        assert stats['consumable_stats']['total'] == 20
        assert stats['worker_stats']['total'] == 15
        assert stats['lending_stats']['active'] == 8

    def test_get_dashboard_statistics_optimized_empty(self, monkeypatch):
        """Test handling of empty collections"""
        mock_mongodb = MagicMock()
        mock_mongodb.aggregate.return_value = []
        mock_mongodb.count_documents.return_value = 0

        monkeypatch.setattr('app.utils.performance_optimizer.mongodb', mock_mongodb)

        stats = QueryOptimizer.get_dashboard_statistics_optimized()

        assert stats['tool_stats']['total'] == 0
        assert stats['consumable_stats']['total'] == 0
        assert stats['worker_stats']['total'] == 0
        assert stats['lending_stats']['active'] == 0

    def test_get_dashboard_statistics_optimized_fallback(self, monkeypatch):
        """Test fallback on exception"""
        mock_mongodb = MagicMock()
        mock_mongodb.aggregate.side_effect = Exception("DB Error")

        # Mock the fallback method too to avoid DB calls
        mock_fallback = MagicMock(return_value={'fallback': True})

        monkeypatch.setattr('app.utils.performance_optimizer.mongodb', mock_mongodb)
        monkeypatch.setattr('app.utils.performance_optimizer.QueryOptimizer._get_dashboard_statistics_fallback', mock_fallback)

        stats = QueryOptimizer.get_dashboard_statistics_optimized()

        assert stats == {'fallback': True}
        mock_fallback.assert_called_once()
