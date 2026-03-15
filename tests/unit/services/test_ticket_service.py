import pytest
from unittest.mock import patch, MagicMock
from app.services.ticket_service import TicketService

class TestTicketService:
    @pytest.fixture
    def ticket_service(self):
        # TicketService __init__ initializes NotificationService and UtilityService
        # If they require DB or something, we might need to patch them.
        # But looking at __init__, it just instantiates them.
        with patch('app.services.ticket_service.NotificationService'), \
             patch('app.services.ticket_service.UtilityService'):
            return TicketService()

    def test_update_ticket_status_not_found(self, ticket_service):
        with patch.object(ticket_service, 'get_ticket_by_id', return_value=None):
            success, message = ticket_service.update_ticket_status('123', 'in_bearbeitung', 'user1')
            assert success is False
            assert message == 'Ticket nicht gefunden'

    def test_update_ticket_status_invalid_status(self, ticket_service):
        with patch.object(ticket_service, 'get_ticket_by_id', return_value={'_id': '123', 'status': 'offen'}):
            success, message = ticket_service.update_ticket_status('123', 'invalid_status', 'user1')
            assert success is False
            assert message == 'Ungültiger Status'

    def test_update_ticket_status_invalid_transition(self, ticket_service):
        # offen -> wartet_auf_antwort is not allowed directly
        with patch.object(ticket_service, 'get_ticket_by_id', return_value={'_id': '123', 'status': 'offen'}):
            success, message = ticket_service.update_ticket_status('123', 'wartet_auf_antwort', 'user1')
            assert success is False
            assert message == 'Statuswechsel nicht erlaubt: offen → wartet_auf_antwort'

    @patch('app.services.ticket_service.mongodb')
    def test_update_ticket_status_success(self, mock_mongodb, ticket_service):
        # offen -> in_bearbeitung is allowed
        with patch.object(ticket_service, 'get_ticket_by_id', return_value={'_id': '123', 'status': 'offen'}):
            with patch('app.services.ticket_history_service.ticket_history_service.log_status_change') as mock_log_status:
                success, message = ticket_service.update_ticket_status('123', 'in_bearbeitung', 'user1')
                assert success is True
                assert 'Status erfolgreich auf "in_bearbeitung" geändert' in message

                mock_mongodb.update_one.assert_called_once()
                args, kwargs = mock_mongodb.update_one.call_args
                assert args[0] == 'tickets'
                assert args[1] == {'_id': '123'}
                assert '$set' in args[2]
                assert args[2]['$set']['status'] == 'in_bearbeitung'
                assert args[2]['$set']['updated_by'] == 'user1'

                mock_log_status.assert_called_once_with(
                    ticket_id='123',
                    old_status='offen',
                    new_status='in_bearbeitung',
                    changed_by='user1'
                )

    def test_update_ticket_status_internal_error(self, ticket_service):
        with patch.object(ticket_service, 'get_ticket_by_id', side_effect=Exception('DB Error')):
            success, message = ticket_service.update_ticket_status('123', 'in_bearbeitung', 'user1')
            assert success is False
            assert message == 'Fehler beim Aktualisieren: [Interner Fehler]'
