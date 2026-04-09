import pytest
from unittest.mock import patch, MagicMock
from app.services.admin_notification_service import AdminNotificationService

@pytest.fixture
def mock_mongodb():
    with patch('app.services.admin_notification_service.mongodb') as mock:
        yield mock

def test_get_notification_count_optimized(mock_mongodb):
    # Mock return value for the aggregate pipeline
    mock_mongodb.aggregate.return_value = [
        {
            'total': [{'count': 10}],
            'unread': [{'count': 3}]
        }
    ]

    stats = AdminNotificationService.get_notification_count()

    assert stats['total'] == 10
    assert stats['unread'] == 3
    assert stats['read'] == 7
    mock_mongodb.aggregate.assert_called_once()

    # Verify pipeline structure
    args, _ = mock_mongodb.aggregate.call_args
    pipeline = args[1]
    assert '$facet' in pipeline[0]
    assert 'total' in pipeline[0]['$facet']
    assert 'unread' in pipeline[0]['$facet']

def test_get_notification_statistics_optimized(mock_mongodb):
    # Mock return value for the aggregate pipeline
    mock_mongodb.aggregate.return_value = [
        {
            'total': [{'count': 20}],
            'types': [
                {'_id': 'info', 'count': 10},
                {'_id': 'warning', 'count': 5}
            ],
            'priorities': [
                {'_id': 'high', 'count': 8},
                {'_id': 'normal', 'count': 12}
            ],
            'read_status': [
                {'_id': True, 'count': 15},
                {'_id': False, 'count': 5}
            ]
        }
    ]

    stats = AdminNotificationService.get_notification_statistics()

    assert stats['total_count'] == 20
    assert stats['type_stats']['info'] == 10
    assert stats['type_stats']['warning'] == 5
    assert stats['type_stats']['error'] == 0
    assert stats['priority_stats']['high'] == 8
    assert stats['priority_stats']['normal'] == 12
    assert stats['unread_count'] == 5
    assert stats['read_count'] == 15
    mock_mongodb.aggregate.assert_called_once()

def test_get_notifications_no_id_loop(mock_mongodb):
    # Mock return value for find
    mock_mongodb.find.return_value = [
        {'_id': '123', 'title': 'Test'}
    ]

    notifications = AdminNotificationService.get_notifications()

    assert len(notifications) == 1
    assert notifications[0]['_id'] == '123'
    # Since we removed the loop, the _id should still be '123' because find handles it
    mock_mongodb.find.assert_called_once()
