"""
Unit tests for database helper functions in app.utils.database_helpers.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from bson import ObjectId
from flask import Flask, g

from app.utils.database_helpers import (
    _extract_by_department,
    get_setting_value,
    get_ticket_categories_from_settings,
    get_setting_map,
    get_ticket_categories_map,
    get_categories_from_settings,
    get_locations_from_settings,
    get_categories_scoped,
    get_locations_scoped,
    get_departments_from_settings,
    ensure_default_settings,
    validate_reference_data,
    migrate_old_data_to_settings,
    get_next_ticket_number,
    normalize_id_for_database,
    ensure_consistent_ids
)

class TestExtractByDepartment:
    """Test suite for _extract_by_department helper function."""

    def test_extract_by_department_dict_valid_dept(self):
        """Test extraction from dict with valid department key."""
        data = {'dept1': ['A', 'B'], 'dept2': ['C']}
        result = _extract_by_department(data, 'dept1')
        assert result == ['A', 'B']

    def test_extract_by_department_dict_invalid_dept_fallback_global(self):
        """Test extraction falling back to GLOBAL key."""
        data = {'dept1': ['A', 'B'], 'GLOBAL': ['C']}
        result = _extract_by_department(data, 'invalid_dept')
        assert result == ['C']

    def test_extract_by_department_dict_invalid_dept_fallback_asterisk(self):
        """Test extraction falling back to '*' key."""
        data = {'dept1': ['A'], '*': ['B']}
        result = _extract_by_department(data, 'invalid_dept')
        assert result == ['B']

    def test_extract_by_department_dict_invalid_dept_fallback_default(self):
        """Test extraction falling back to 'default' key."""
        data = {'dept1': ['A'], 'default': ['D']}
        result = _extract_by_department(data, 'invalid_dept')
        assert result == ['D']

    def test_extract_by_department_dict_merge_all(self):
        """Test extraction merging all lists when no fallback is found."""
        data = {'dept1': ['A', 'B'], 'dept2': ['C']}
        result = _extract_by_department(data, 'invalid_dept')
        assert sorted(result) == ['A', 'B', 'C']

    def test_extract_by_department_list(self):
        """Test extraction from a list directly."""
        data = ['A', 'B']
        result = _extract_by_department(data, 'dept1')
        assert result == ['A', 'B']

    def test_extract_by_department_other_type(self):
        """Test extraction with unhandled type."""
        data = "string_value"
        result = _extract_by_department(data, 'dept1')
        assert result == []

class TestGetSettingValue:
    """Test suite for get_setting_value function."""

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_value_string_legacy(self, mock_mongodb):
        """Test loading string legacy value from settings collection."""
        mock_mongodb.find_one.return_value = {'key': 'my_setting', 'value': 'A, B, C '}
        result = get_setting_value('my_setting')
        assert result == ['A', 'B', 'C']
        mock_mongodb.find_one.assert_called_once_with('settings', {'key': 'my_setting'})

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_value_dict_department_sensitiv(self, mock_mongodb):
        """Test loading dict value with department scoping."""
        mock_mongodb.find_one.return_value = {'key': 'my_setting', 'value': {'dept1': ['A', 'B']}}
        app = Flask(__name__)
        with app.app_context():
            g.current_department = 'dept1'
            result = get_setting_value('my_setting')
            assert result == ['A', 'B']

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_value_fallback_collection(self, mock_mongodb):
        """Test fallback collection when settings not found."""
        mock_mongodb.find_one.return_value = None
        mock_mongodb.find.return_value = [{'name': 'A'}, {'name': 'B'}, {'other': 'C'}]

        result = get_setting_value('my_setting', fallback_collection='my_fallback', fallback_field='name')

        assert result == ['A', 'B']
        mock_mongodb.find_one.assert_called_once_with('settings', {'key': 'my_setting'})
        mock_mongodb.find.assert_called_once_with('my_fallback', {'deleted': {'$ne': True}})

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_value_no_fallback_collection(self, mock_mongodb):
        """Test missing setting with no fallback collection."""
        mock_mongodb.find_one.return_value = None
        result = get_setting_value('my_setting')
        assert result == []

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_value_exception(self, mock_mongodb):
        """Test handling of exceptions during loading."""
        mock_mongodb.find_one.side_effect = Exception("DB Error")
        result = get_setting_value('my_setting')
        assert result == []

class TestGetSettingMap:
    """Test suite for get_setting_map function."""

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_map_missing(self, mock_mongodb):
        mock_mongodb.find_one.return_value = None
        assert get_setting_map('test_key') == {}

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_map_list(self, mock_mongodb):
        mock_mongodb.find_one.return_value = {'key': 'test_key', 'value': ['A', 'B']}
        assert get_setting_map('test_key') == {'GLOBAL': ['A', 'B']}

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_map_dict(self, mock_mongodb):
        mock_mongodb.find_one.return_value = {'key': 'test_key', 'value': {'dept1': ['A']}}
        assert get_setting_map('test_key') == {'dept1': ['A']}

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_map_other(self, mock_mongodb):
        mock_mongodb.find_one.return_value = {'key': 'test_key', 'value': "string"}
        assert get_setting_map('test_key') == {}

    @patch('app.utils.database_helpers.mongodb')
    def test_get_setting_map_exception(self, mock_mongodb):
        mock_mongodb.find_one.side_effect = Exception("DB Error")
        assert get_setting_map('test_key') == {}


class TestScopedFunctions:
    """Test suite for scoped getter functions."""

    @patch('app.utils.database_helpers.mongodb')
    def test_get_categories_scoped_valid(self, mock_mongodb):
        app = Flask(__name__)
        with app.app_context():
            g.current_department = 'dept1'
            mock_mongodb.find.return_value = [
                {'name': 'B'}, {'name': ' a '}, {'name': 'A'}, {'name': None}, {}
            ]
            result = get_categories_scoped()
            assert result == ['a', 'B'] # Casefold sorted, deduplicated, stripped
            mock_mongodb.find.assert_called_once_with('categories', {'deleted': {'$ne': True}, 'department': 'dept1'})

    @patch('app.utils.database_helpers.mongodb')
    def test_get_categories_scoped_no_dept(self, mock_mongodb):
        app = Flask(__name__)
        with app.app_context():
            # g.current_department missing
            assert get_categories_scoped() == []

    @patch('app.utils.database_helpers.mongodb')
    def test_get_locations_scoped_valid(self, mock_mongodb):
        app = Flask(__name__)
        with app.app_context():
            g.current_department = 'dept1'
            mock_mongodb.find.return_value = [{'name': 'Loc1'}]
            assert get_locations_scoped() == ['Loc1']

class TestUtilityAliases:
    """Test suite for utility aliases."""

    @patch('app.utils.database_helpers.get_setting_value')
    def test_aliases(self, mock_get_setting_value):
        mock_get_setting_value.return_value = ['A']

        assert get_ticket_categories_from_settings() == ['A']
        mock_get_setting_value.assert_called_with('ticket_categories')

        assert get_categories_from_settings() == ['A']
        mock_get_setting_value.assert_called_with('categories', 'categories', 'name')

        assert get_locations_from_settings() == ['A']
        mock_get_setting_value.assert_called_with('locations', 'locations', 'name')

        assert get_departments_from_settings() == ['A']
        mock_get_setting_value.assert_called_with('departments', 'departments', 'name')

    @patch('app.utils.database_helpers.get_setting_map')
    def test_get_ticket_categories_map(self, mock_get_setting_map):
        mock_get_setting_map.return_value = {'GLOBAL': ['A']}
        assert get_ticket_categories_map() == {'GLOBAL': ['A']}
        mock_get_setting_map.assert_called_with('ticket_categories')

class TestSettingsOperations:
    """Test suite for settings and migration operations."""

    @patch('app.utils.database_helpers.mongodb')
    def test_ensure_default_settings_not_exist(self, mock_mongodb):
        mock_mongodb.find_one.return_value = None
        ensure_default_settings()
        assert mock_mongodb.insert_one.call_count == 2
        mock_mongodb.insert_one.assert_any_call('settings', {'key': 'departments', 'value': []})
        mock_mongodb.insert_one.assert_any_call('settings', {'key': 'ticket_categories', 'value': []})

    @patch('app.utils.database_helpers.mongodb')
    def test_ensure_default_settings_exists(self, mock_mongodb):
        mock_mongodb.find_one.return_value = True
        ensure_default_settings()
        mock_mongodb.insert_one.assert_not_called()

    @patch('app.utils.database_helpers.mongodb')
    def test_ensure_default_settings_exception(self, mock_mongodb):
        mock_mongodb.find_one.side_effect = Exception("DB Error")
        with pytest.raises(Exception):
            ensure_default_settings()

    @patch('app.utils.database_helpers.get_categories_from_settings')
    @patch('app.utils.database_helpers.get_locations_from_settings')
    @patch('app.utils.database_helpers.get_departments_from_settings')
    def test_validate_reference_data(self, mock_dept, mock_loc, mock_cat):
        mock_cat.return_value = ['Cat1']
        mock_loc.return_value = ['Loc1']
        mock_dept.return_value = ['Dept1']

        res = validate_reference_data()
        assert res == {'categories': ['Cat1'], 'locations': ['Loc1'], 'departments': ['Dept1']}

    @patch('app.utils.database_helpers.get_categories_from_settings')
    def test_validate_reference_data_exception(self, mock_cat):
        mock_cat.side_effect = Exception("DB Error")
        res = validate_reference_data()
        assert res == {'categories': [], 'locations': [], 'departments': []}

    @patch('app.utils.database_helpers.mongodb')
    def test_migrate_old_data_to_settings(self, mock_mongodb):
        def find_side_effect(collection, query):
            if collection == 'categories': return [{'name': 'Cat1'}]
            if collection == 'locations': return [{'name': 'Loc1'}]
            if collection == 'departments': return [{'name': 'Dept1'}]
            if collection == 'ticket_categories': return [{'name': 'TCat1'}]
            return []

        mock_mongodb.find.side_effect = find_side_effect
        migrate_old_data_to_settings()

        assert mock_mongodb.update_one.call_count == 4
        mock_mongodb.update_one.assert_any_call('settings', {'key': 'categories'}, {'$set': {'value': ['Cat1']}}, upsert=True)
        mock_mongodb.update_one.assert_any_call('settings', {'key': 'locations'}, {'$set': {'value': ['Loc1']}}, upsert=True)
        mock_mongodb.update_one.assert_any_call('settings', {'key': 'departments'}, {'$set': {'value': ['Dept1']}}, upsert=True)
        mock_mongodb.update_one.assert_any_call('settings', {'key': 'ticket_categories'}, {'$set': {'value': ['TCat1']}}, upsert=True)

    @patch('app.utils.database_helpers.mongodb')
    def test_migrate_old_data_to_settings_empty(self, mock_mongodb):
        mock_mongodb.find.return_value = []
        migrate_old_data_to_settings()
        mock_mongodb.update_one.assert_not_called()

    @patch('app.utils.database_helpers.mongodb')
    def test_migrate_old_data_to_settings_exception(self, mock_mongodb):
        mock_mongodb.find.side_effect = Exception("DB Error")
        with pytest.raises(Exception):
            migrate_old_data_to_settings()

class TestUtilityFunctions:
    """Test suite for general utility functions."""

    @patch('app.utils.database_helpers.mongodb')
    @patch('app.utils.database_helpers.datetime')
    def test_get_next_ticket_number_empty(self, mock_datetime, mock_mongodb):
        mock_date = datetime(2025, 6, 1)
        mock_datetime.now.return_value = mock_date
        mock_mongodb.find.return_value = []

        assert get_next_ticket_number() == "2506-001"

    @patch('app.utils.database_helpers.mongodb')
    @patch('app.utils.database_helpers.datetime')
    def test_get_next_ticket_number_existing(self, mock_datetime, mock_mongodb):
        mock_date = datetime(2025, 6, 1)
        mock_datetime.now.return_value = mock_date
        mock_mongodb.find.return_value = [{'ticket_number': '2506-005'}, {'ticket_number': '2506-012'}]

        assert get_next_ticket_number() == "2506-013"

    @patch('app.utils.database_helpers.mongodb')
    @patch('app.utils.database_helpers.datetime')
    def test_get_next_ticket_number_invalid_existing(self, mock_datetime, mock_mongodb):
        mock_date = datetime(2025, 6, 1)
        mock_datetime.now.return_value = mock_date
        # Tests resilience against badly formatted numbers
        mock_mongodb.find.return_value = [{'ticket_number': '2506-abc'}, {'ticket_number': '2506-002'}, {}]

        assert get_next_ticket_number() == "2506-003"

    def test_normalize_id_for_database(self):
        oid = ObjectId('507f1f77bcf86cd799439011')
        assert normalize_id_for_database(oid) == '507f1f77bcf86cd799439011'
        assert normalize_id_for_database('string_id') == 'string_id'
        assert normalize_id_for_database(123) == '123'

    @patch('app.utils.database_helpers.mongodb')
    def test_ensure_consistent_ids(self, mock_mongodb):
        oid = ObjectId('507f1f77bcf86cd799439011')

        def find_side_effect(collection, query):
            if collection == 'tickets': return [{'_id': oid, 'data': 'test'}, {'_id': 'string_id'}]
            return []

        mock_mongodb.find.side_effect = find_side_effect

        updated_count = ensure_consistent_ids()

        assert updated_count == 1
        mock_mongodb.delete_one.assert_called_once_with('tickets', {'_id': oid})
        mock_mongodb.insert_one.assert_called_once_with('tickets', {'_id': '507f1f77bcf86cd799439011', 'data': 'test'})

    @patch('app.utils.database_helpers.mongodb')
    def test_ensure_consistent_ids_exception(self, mock_mongodb):
        mock_mongodb.find.side_effect = Exception("DB Error")
        updated_count = ensure_consistent_ids()
        assert updated_count == 0
