import pytest
from unittest.mock import patch, MagicMock
from app.services.location_service import LocationService

@pytest.fixture
def location_service():
    return LocationService()

def test_get_current_department_success(location_service):
    class MockAppG:
        pass

    mock_g = MockAppG()
    mock_g.current_department = 'IT'

    with patch('app.services.location_service.g', mock_g):
        assert location_service.get_current_department() == 'IT'

def test_get_current_department_exception(location_service):
    class MockAppG:
        @property
        def current_department(self):
            raise Exception("Test Exception")

    mock_g = MockAppG()
    with patch('app.services.location_service.g', mock_g):
        assert location_service.get_current_department() is None

@patch('app.services.location_service.LocationService.get_current_department')
@patch('app.services.location_service.mongodb')
def test_get_locations_for_department_success(mock_mongodb, mock_get_current_department, location_service):
    mock_mongodb.find.return_value = [
        {'name': 'Berlin '},
        {'name': 'Munich'},
        {'name': ''}, # should be ignored
        {} # no name, should be ignored
    ]

    locations = location_service.get_locations_for_department('IT')

    assert locations == ['Berlin', 'Munich']
    mock_mongodb.find.assert_called_once_with('locations', {
        'department': 'IT',
        'deleted': {'$ne': True}
    })

@patch('app.services.location_service.LocationService.get_current_department')
def test_get_locations_for_department_no_department(mock_get_current_department, location_service):
    mock_get_current_department.return_value = None
    locations = location_service.get_locations_for_department()
    assert locations == []

@patch('app.services.location_service.mongodb')
def test_get_locations_for_department_db_error(mock_mongodb, location_service):
    mock_mongodb.find.side_effect = Exception("DB Error")
    locations = location_service.get_locations_for_department('IT')
    assert locations == []

@patch('app.services.location_service.LocationService.get_locations_for_department')
@patch('app.services.location_service.mongodb')
def test_get_all_department_locations_success(mock_mongodb, mock_get_locations, location_service):
    mock_mongodb.find_one.return_value = {
        'value': ['IT', 'HR', '', ' ']
    }

    def side_effect(dept):
        if dept == 'IT':
            return ['Berlin']
        elif dept == 'HR':
            return ['Munich']
        return []

    mock_get_locations.side_effect = side_effect

    result = location_service.get_all_department_locations()

    assert result == {'IT': ['Berlin'], 'HR': ['Munich']}
    mock_mongodb.find_one.assert_called_once_with('settings', {'key': 'departments'})

@patch('app.services.location_service.mongodb')
def test_get_all_department_locations_no_setting(mock_mongodb, location_service):
    mock_mongodb.find_one.return_value = None
    result = location_service.get_all_department_locations()
    assert result == {}

@patch('app.services.location_service.mongodb')
def test_get_all_department_locations_db_error(mock_mongodb, location_service):
    mock_mongodb.find_one.side_effect = Exception("DB Error")
    result = location_service.get_all_department_locations()
    assert result == {}

@patch('app.services.location_service.mongodb')
def test_create_location_success(mock_mongodb, location_service):
    mock_mongodb.find_one.return_value = None

    result = location_service.create_location('Berlin', 'IT')

    assert result is True
    mock_mongodb.insert_one.assert_called_once()
    args, kwargs = mock_mongodb.insert_one.call_args
    assert args[0] == 'locations'
    assert args[1]['name'] == 'Berlin'
    assert args[1]['department'] == 'IT'
    assert 'created_at' in args[1]
    assert 'updated_at' in args[1]
    assert args[1]['deleted'] is False

@patch('app.services.location_service.LocationService.get_current_department')
def test_create_location_no_department(mock_get_current_department, location_service):
    mock_get_current_department.return_value = None
    assert location_service.create_location('Berlin') is False

def test_create_location_empty_name(location_service):
    assert location_service.create_location('', 'IT') is False
    assert location_service.create_location('   ', 'IT') is False

@patch('app.services.location_service.mongodb')
def test_create_location_existing(mock_mongodb, location_service):
    mock_mongodb.find_one.return_value = {'_id': '123', 'name': 'Berlin'}
    assert location_service.create_location('Berlin', 'IT') is False

@patch('app.services.location_service.mongodb')
def test_create_location_db_error(mock_mongodb, location_service):
    mock_mongodb.find_one.side_effect = Exception("DB Error")
    assert location_service.create_location('Berlin', 'IT') is False

@patch('app.services.location_service.mongodb')
def test_update_location_success(mock_mongodb, location_service):
    mock_mongodb.update_one.return_value = True

    result = location_service.update_location('Berlin', 'Berlin 2', 'IT')

    assert result is True
    mock_mongodb.update_one.assert_called_once()
    args, kwargs = mock_mongodb.update_one.call_args
    assert args[0] == 'locations'
    assert args[1] == {'name': 'Berlin', 'department': 'IT', 'deleted': {'$ne': True}}
    assert args[2]['$set']['name'] == 'Berlin 2'
    assert 'updated_at' in args[2]['$set']

@patch('app.services.location_service.LocationService.get_current_department')
def test_update_location_no_department(mock_get_current_department, location_service):
    mock_get_current_department.return_value = None
    assert location_service.update_location('Berlin', 'Berlin 2') is False

@patch('app.services.location_service.mongodb')
def test_update_location_not_found(mock_mongodb, location_service):
    mock_mongodb.update_one.return_value = False
    assert location_service.update_location('Berlin', 'Berlin 2', 'IT') is False

@patch('app.services.location_service.mongodb')
def test_update_location_db_error(mock_mongodb, location_service):
    mock_mongodb.update_one.side_effect = Exception("DB Error")
    assert location_service.update_location('Berlin', 'Berlin 2', 'IT') is False

@patch('app.services.location_service.mongodb')
def test_delete_location_success(mock_mongodb, location_service):
    mock_mongodb.update_one.return_value = True

    result = location_service.delete_location('Berlin', 'IT')

    assert result is True
    mock_mongodb.update_one.assert_called_once()
    args, kwargs = mock_mongodb.update_one.call_args
    assert args[0] == 'locations'
    assert args[1] == {'name': 'Berlin', 'department': 'IT', 'deleted': {'$ne': True}}
    assert args[2]['$set']['deleted'] is True
    assert 'deleted_at' in args[2]['$set']
    assert 'updated_at' in args[2]['$set']

@patch('app.services.location_service.LocationService.get_current_department')
def test_delete_location_no_department(mock_get_current_department, location_service):
    mock_get_current_department.return_value = None
    assert location_service.delete_location('Berlin') is False

@patch('app.services.location_service.mongodb')
def test_delete_location_not_found(mock_mongodb, location_service):
    mock_mongodb.update_one.return_value = False
    assert location_service.delete_location('Berlin', 'IT') is False

@patch('app.services.location_service.mongodb')
def test_delete_location_db_error(mock_mongodb, location_service):
    mock_mongodb.update_one.side_effect = Exception("DB Error")
    assert location_service.delete_location('Berlin', 'IT') is False
