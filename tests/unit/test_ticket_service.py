
import pytest
from bson import ObjectId
from datetime import datetime
from unittest.mock import MagicMock
from app.services.ticket_service import TicketService

@pytest.fixture
def mock_mongodb(monkeypatch):
    # Use a real mongomock client
    import mongomock
    client = mongomock.MongoClient()
    db = client.scandy

    # Mock the mongodb object from app.models.mongodb_database
    mock_db = MagicMock()
    mock_db.db = db

    def mock_find(collection, query, **kwargs):
        return db[collection].find(query)

    def mock_aggregate(collection, pipeline, **kwargs):
        return db[collection].aggregate(pipeline)

    def mock_find_one(collection, query, **kwargs):
        return db[collection].find_one(query)

    mock_db.find.side_effect = mock_find
    mock_db.aggregate.side_effect = mock_aggregate
    mock_db.find_one.side_effect = mock_find_one

    monkeypatch.setattr('app.services.ticket_service.mongodb', mock_db)
    return db

def test_get_tickets_by_user_message_count_optimization(mock_mongodb, monkeypatch):
    """Verify that message counts are correctly retrieved in batch (Bolt ⚡ optimization)"""
    # Setup data
    ticket_id = ObjectId()
    mock_mongodb.tickets.insert_one({
        '_id': ticket_id,
        'title': 'Test Ticket',
        'status': 'offen',
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'deleted': False
    })

    # Add messages with different ID types (both should be counted)
    mock_mongodb.ticket_messages.insert_one({
        'ticket_id': ticket_id,
        'message': 'Message 1'
    })
    mock_mongodb.ticket_messages.insert_one({
        'ticket_id': str(ticket_id),
        'message': 'Message 2'
    })

    # Mock Flask g
    mock_g = MagicMock()
    mock_g.current_department = None
    monkeypatch.setattr('app.services.ticket_service.g', mock_g)

    # Mock ticket_category_service
    monkeypatch.setattr('app.services.ticket_service.ticket_category_service', MagicMock())

    service = TicketService()

    # Call the method (Admin role sees 'all_tickets')
    result = service.get_tickets_by_user('testuser', 'admin')

    # Verify message count is correct (2 messages total)
    all_tickets = result['all_tickets']
    assert len(all_tickets) == 1
    assert all_tickets[0]['message_count'] == 2
    assert all_tickets[0]['id'] == str(ticket_id)

def test_get_tickets_by_user_deduplication_and_counts(mock_mongodb, monkeypatch):
    """Verify deduplication and message counts for multiple tickets"""
    tid1 = ObjectId()
    tid2 = ObjectId()
    mock_mongodb.tickets.insert_many([
        {'_id': tid1, 'title': 'T1', 'status': 'offen', 'updated_at': datetime.now(), 'deleted': False},
        {'_id': tid2, 'title': 'T2', 'status': 'offen', 'updated_at': datetime.now(), 'deleted': False}
    ])

    # Messages for both tickets
    mock_mongodb.ticket_messages.insert_many([
        {'ticket_id': tid1, 'message': 'M1'},
        {'ticket_id': tid1, 'message': 'M2'},
        {'ticket_id': str(tid2), 'message': 'M3'}
    ])

    mock_g = MagicMock()
    mock_g.current_department = None
    monkeypatch.setattr('app.services.ticket_service.g', mock_g)

    service = TicketService()
    monkeypatch.setattr('app.services.ticket_service.ticket_category_service', MagicMock())

    result = service.get_tickets_by_user('testuser', 'admin')

    # Map results by title for easy assertion
    tickets = {t['title']: t for t in result['all_tickets']}
    assert tickets['T1']['message_count'] == 2
    assert tickets['T2']['message_count'] == 1
