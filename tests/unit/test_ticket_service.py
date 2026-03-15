import pytest
from unittest.mock import patch
from app.services.ticket_service import TicketService
from flask import g


@pytest.fixture
def ticket_service():
    """Fixture to provide a TicketService instance."""
    return TicketService()


@pytest.fixture
def sample_ticket_data():
    """Fixture providing valid sample ticket data."""
    return {
        'title': 'Test Ticket',
        'description': 'A test description',
        'priority': 'hoch',
        'category': 'Support'
    }


def test_create_ticket_mongodb_error(app, ticket_service, sample_ticket_data):
    """
    Test that an internal error during MongoDB insertion is properly handled
    and returns the correct error tuple.
    """
    with app.app_context():
        g.current_department = 'IT'

        mock_mongo_path = 'app.services.ticket_service.mongodb'
        mock_cat_path = 'app.services.ticket_service.ticket_category_service'

        with patch(mock_mongo_path) as mock_mongodb, \
             patch(mock_cat_path) as mock_category_service:

            # Setup mock to pass category validation
            mock_cat_service_method = \
                mock_category_service.get_ticket_categories_for_department
            mock_cat_service_method.return_value = ['Support']

            # Setup mock to simulate a missing required fields setting
            mock_mongodb.find_one.return_value = None

            # Setup mock to raise an exception on insert
            mock_mongodb.insert_one.side_effect = Exception("DB failure")

            success, message, ticket_id = ticket_service.create_ticket(
                ticket_data=sample_ticket_data,
                created_by='test_user'
            )

            assert success is False
            err_msg = 'Fehler beim Erstellen des Tickets: [Interner Fehler]'
            assert message == err_msg
            assert ticket_id is None


def test_create_ticket_success(app, ticket_service, sample_ticket_data):
    """
    Test that creating a ticket successfully returns the expected tuple.
    """
    with app.app_context():
        g.current_department = 'IT'

        mock_mongo_path = 'app.services.ticket_service.mongodb'
        mock_cat_path = 'app.services.ticket_service.ticket_category_service'
        mock_num_path = 'app.services.ticket_service.get_next_ticket_number'

        with patch(mock_mongo_path) as mock_mongodb, \
             patch(mock_cat_path) as mock_category_service, \
             patch(mock_num_path) as mock_get_number:

            # Setup mocks for validation and setup
            mock_cat_service_method = \
                mock_category_service.get_ticket_categories_for_department
            mock_cat_service_method.return_value = ['Support']

            mock_mongodb.find_one.return_value = None
            mock_get_number.return_value = "T-1234"

            # Setup mock for successful insertion
            mock_mongodb.insert_one.return_value = "mock_ticket_id_5678"

            success, message, ticket_id = ticket_service.create_ticket(
                ticket_data=sample_ticket_data,
                created_by='test_user'
            )

            assert success is True
            assert message == 'Ticket wurde erfolgreich erstellt'
            assert ticket_id == 'mock_ticket_id_5678'

            # Verify insert was called
            mock_mongodb.insert_one.assert_called_once()
