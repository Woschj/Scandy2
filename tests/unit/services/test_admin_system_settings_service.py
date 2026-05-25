import pytest
from unittest.mock import patch, MagicMock
from app.services.admin_system_settings_service import AdminSystemSettingsService

@pytest.fixture
def mock_mongodb():
    with patch('app.services.admin_system_settings_service.mongodb') as mock:
        yield mock

class TestAdminSystemSettingsService:
    # --- GETTERS ---

    def test_get_departments_from_settings_success(self, mock_mongodb):
        mock_mongodb.find_one.return_value = {'key': 'departments', 'value': ['IT', 'HR']}
        result = AdminSystemSettingsService.get_departments_from_settings()
        assert result == ['IT', 'HR']
        mock_mongodb.find_one.assert_called_with('settings', {'key': 'departments'})

    def test_get_departments_from_settings_empty_or_missing(self, mock_mongodb):
        mock_mongodb.find_one.return_value = None
        assert AdminSystemSettingsService.get_departments_from_settings() == []

        mock_mongodb.find_one.return_value = {'key': 'departments'}
        assert AdminSystemSettingsService.get_departments_from_settings() == []

    def test_get_categories_from_settings_success(self, mock_mongodb):
        mock_mongodb.find_one.return_value = {'key': 'categories', 'value': ['Laptop', 'Mouse']}
        result = AdminSystemSettingsService.get_categories_from_settings()
        assert result == ['Laptop', 'Mouse']

    def test_get_locations_from_settings_success(self, mock_mongodb):
        mock_mongodb.find_one.return_value = {'key': 'locations', 'value': ['Room 1', 'Room 2']}
        result = AdminSystemSettingsService.get_locations_from_settings()
        assert result == ['Room 1', 'Room 2']

    def test_get_ticket_categories_from_settings_success(self, mock_mongodb):
        mock_mongodb.find_one.return_value = {'key': 'ticket_categories', 'value': ['Hardware', 'Software']}
        result = AdminSystemSettingsService.get_ticket_categories_from_settings()
        assert result == ['Hardware', 'Software']

    # --- ADD ---

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    def test_add_department_success(self, mock_get_departments, mock_mongodb):
        mock_get_departments.return_value = ['HR']
        success, message = AdminSystemSettingsService.add_department('IT')

        assert success is True
        assert 'erfolgreich hinzugefügt' in message
        mock_mongodb.update_one.assert_called_once()
        args, kwargs = mock_mongodb.update_one.call_args
        assert args[0] == 'settings'
        assert args[1] == {'key': 'departments'}
        assert kwargs['upsert'] is True
        assert args[2]['$set']['value'] == ['HR', 'IT'] # sorted alphabetically

    def test_add_department_empty(self, mock_mongodb):
        success, message = AdminSystemSettingsService.add_department('   ')
        assert success is False
        assert "darf nicht leer sein" in message
        mock_mongodb.update_one.assert_not_called()

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    def test_add_department_already_exists(self, mock_get_departments, mock_mongodb):
        mock_get_departments.return_value = ['IT']
        success, message = AdminSystemSettingsService.add_department('IT')
        assert success is False
        assert "existiert bereits" in message
        mock_mongodb.update_one.assert_not_called()

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_categories_from_settings')
    def test_add_category_success(self, mock_get_categories, mock_mongodb):
        mock_get_categories.return_value = ['Monitor']
        success, message = AdminSystemSettingsService.add_category('Laptop')

        assert success is True
        assert 'erfolgreich hinzugefügt' in message
        mock_mongodb.update_one.assert_called_once()
        args, kwargs = mock_mongodb.update_one.call_args
        assert args[2]['$set']['value'] == ['Laptop', 'Monitor']

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_locations_from_settings')
    def test_add_location_success(self, mock_get_locations, mock_mongodb):
        mock_get_locations.return_value = ['B']
        success, message = AdminSystemSettingsService.add_location('A')

        assert success is True
        mock_mongodb.update_one.assert_called_once()
        args, kwargs = mock_mongodb.update_one.call_args
        assert args[2]['$set']['value'] == ['A', 'B']

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_ticket_categories_from_settings')
    def test_add_ticket_category_success(self, mock_get_ticket_categories, mock_mongodb):
        mock_get_ticket_categories.return_value = ['Software']
        success, message = AdminSystemSettingsService.add_ticket_category('Hardware')

        assert success is True
        mock_mongodb.update_one.assert_called_once()
        args, kwargs = mock_mongodb.update_one.call_args
        assert args[2]['$set']['value'] == ['Hardware', 'Software']

    # --- DELETE ---

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    def test_delete_department_success(self, mock_get_departments, mock_mongodb):
        mock_get_departments.return_value = ['IT', 'HR']

        mock_mongodb.db.tickets.find.return_value = [{'_id': 'ticket1'}]
        mock_mongodb.db.tools.delete_many.return_value = MagicMock(deleted_count=1)
        mock_mongodb.db.messages.delete_many.return_value = MagicMock(deleted_count=2)

        success, message = AdminSystemSettingsService.delete_department('IT')

        assert success is True
        assert "gelöscht" in message
        # Verify settings list update
        mock_mongodb.update_one.assert_called_once()
        args, kwargs = mock_mongodb.update_one.call_args
        assert args[2]['$set']['value'] == ['HR']

    def test_delete_department_empty(self, mock_mongodb):
        success, message = AdminSystemSettingsService.delete_department('')
        assert success is False
        assert "darf nicht leer sein" in message

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    def test_delete_department_not_found(self, mock_get_departments, mock_mongodb):
        mock_get_departments.return_value = ['HR']
        success, message = AdminSystemSettingsService.delete_department('IT')
        assert success is False
        assert "nicht gefunden" in message

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_categories_from_settings')
    def test_delete_category_success(self, mock_get_categories, mock_mongodb):
        mock_get_categories.return_value = ['Laptop', 'Mouse']
        mock_mongodb.count_documents.return_value = 0 # No tools using it

        success, message = AdminSystemSettingsService.delete_category('Laptop')

        assert success is True
        mock_mongodb.update_one.assert_called_once()
        args, kwargs = mock_mongodb.update_one.call_args
        assert args[2]['$set']['value'] == ['Mouse']

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_categories_from_settings')
    def test_delete_category_in_use(self, mock_get_categories, mock_mongodb):
        mock_get_categories.return_value = ['Laptop']
        mock_mongodb.count_documents.return_value = 5 # 5 tools using it

        success, message = AdminSystemSettingsService.delete_category('Laptop')

        assert success is False
        assert "wird noch von 5 Werkzeugen verwendet" in message
        mock_mongodb.update_one.assert_not_called()

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_locations_from_settings')
    def test_delete_location_in_use(self, mock_get_locations, mock_mongodb):
        mock_get_locations.return_value = ['Room 1']
        mock_mongodb.count_documents.return_value = 2

        success, message = AdminSystemSettingsService.delete_location('Room 1')
        assert success is False
        assert "wird noch von 2 Werkzeugen verwendet" in message

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_ticket_categories_from_settings')
    def test_delete_ticket_category_in_use(self, mock_get_ticket_categories, mock_mongodb):
        mock_get_ticket_categories.return_value = ['Hardware']
        mock_mongodb.count_documents.return_value = 1

        success, message = AdminSystemSettingsService.delete_ticket_category('Hardware')
        assert success is False
        assert "wird noch von 1 Tickets verwendet" in message

    # --- RENAME ---

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    def test_rename_department_success(self, mock_get_departments, mock_mongodb):
        mock_get_departments.return_value = ['IT', 'HR']
        mock_mongodb.db.tickets.find.return_value = [{'_id': 't1'}]

        success, message = AdminSystemSettingsService.rename_department('IT', 'IT-Dev')

        assert success is True
        assert "umbenannt" in message

        # Verify it updated the global list
        mock_mongodb.update_one.assert_called_once()
        args, kwargs = mock_mongodb.update_one.call_args
        assert args[2]['$set']['value'] == ['IT-Dev', 'HR']

        # Verify it updated direct collections
        # mock_mongodb.db is accessed via getitem in the code: mongodb.db[coll].update_many
        # So we assert on any call to db.__getitem__().update_many
        assert mock_mongodb.db.__getitem__.called

    def test_rename_department_missing_params(self, mock_mongodb):
        success, message = AdminSystemSettingsService.rename_department('', 'IT-Dev')
        assert success is False
        assert "sind erforderlich" in message

    def test_rename_department_identical(self, mock_mongodb):
        success, message = AdminSystemSettingsService.rename_department('IT', 'IT')
        assert success is False
        assert "identisch" in message

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    def test_rename_department_not_found(self, mock_get_departments, mock_mongodb):
        mock_get_departments.return_value = ['HR']
        success, message = AdminSystemSettingsService.rename_department('IT', 'IT-Dev')
        assert success is False
        assert "nicht gefunden" in message

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    def test_rename_department_new_exists(self, mock_get_departments, mock_mongodb):
        mock_get_departments.return_value = ['IT', 'HR']
        success, message = AdminSystemSettingsService.rename_department('IT', 'HR')
        assert success is False
        assert "existiert bereits" in message

    # --- STATISTICS ---

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_categories_from_settings')
    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_locations_from_settings')
    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_ticket_categories_from_settings')
    def test_get_system_settings_statistics(self, mock_ticket_cat, mock_loc, mock_cat, mock_dept, mock_mongodb):
        mock_dept.return_value = ['IT']
        mock_cat.return_value = ['Laptop']
        mock_loc.return_value = ['Room 1']
        mock_ticket_cat.return_value = ['Hardware']

        mock_mongodb.count_documents.side_effect = [
            5, # workers
            10, # tools cat
            15, # tools loc
            20  # tickets
        ]

        stats = AdminSystemSettingsService.get_system_settings_statistics()

        assert stats['departments']['count'] == 1
        assert stats['departments']['used_by_workers'] == 5
        assert stats['categories']['count'] == 1
        assert stats['categories']['used_by_tools'] == 10
        assert stats['locations']['count'] == 1
        assert stats['locations']['used_by_tools'] == 15
        assert stats['ticket_categories']['count'] == 1
        assert stats['ticket_categories']['used_by_tickets'] == 20

    # --- VALIDATION ---

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_categories_from_settings')
    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_locations_from_settings')
    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_ticket_categories_from_settings')
    def test_validate_system_settings_valid(self, mock_ticket_cat, mock_loc, mock_cat, mock_dept, mock_mongodb):
        mock_dept.return_value = ['IT']
        mock_cat.return_value = ['Laptop']
        mock_loc.return_value = ['Room 1']
        mock_ticket_cat.return_value = ['Hardware']

        results = AdminSystemSettingsService.validate_system_settings()
        assert results['overall_valid'] is True
        assert results['departments']['valid'] is True

    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_departments_from_settings')
    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_categories_from_settings')
    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_locations_from_settings')
    @patch('app.services.admin_system_settings_service.AdminSystemSettingsService.get_ticket_categories_from_settings')
    def test_validate_system_settings_invalid(self, mock_ticket_cat, mock_loc, mock_cat, mock_dept, mock_mongodb):
        mock_dept.return_value = ['IT', '  '] # Invalid empty dept
        mock_cat.return_value = ['Laptop']
        mock_loc.return_value = ['Room 1']
        mock_ticket_cat.return_value = ['Hardware']

        results = AdminSystemSettingsService.validate_system_settings()
        assert results['overall_valid'] is False
        assert results['departments']['valid'] is False
        assert "Leere Abteilung gefunden" in results['departments']['issues'][0]
