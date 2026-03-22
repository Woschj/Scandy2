"""
Unit tests for ID helper functions.
"""

import pytest
from unittest.mock import MagicMock, patch
from bson import ObjectId
from app.utils.id_helpers import (
    convert_id_for_query,
    normalize_id_for_database,
    find_document_by_id,
    find_user_by_id,
    normalize_all_ids_in_collection,
    resolve_user_group_names
)

class TestIDHelpers:
    """Test suite for ID helper functions."""

    def test_convert_id_for_query_valid_object_id(self):
        """Test conversion of valid 24-char hex string to ObjectId."""
        valid_id = "507f1f77bcf86cd799439011"
        result = convert_id_for_query(valid_id)
        assert isinstance(result, ObjectId)
        assert str(result) == valid_id

    def test_convert_id_for_query_invalid_object_id_str(self):
        """Test conversion of invalid 24-char string (non-hex)."""
        invalid_id = "g07f1f77bcf86cd799439011"  # 'g' is not hex
        result = convert_id_for_query(invalid_id)
        assert result == invalid_id
        assert isinstance(result, str)

    def test_convert_id_for_query_short_string(self):
        """Test conversion of string shorter than 24 chars."""
        short_id = "abc123"
        result = convert_id_for_query(short_id)
        assert result == short_id

    def test_convert_id_for_query_non_string(self):
        """Test conversion of non-string input."""
        non_str = 12345
        result = convert_id_for_query(non_str)
        assert result == non_str

    def test_normalize_id_for_database_object_id(self):
        """Test normalization of ObjectId to string."""
        oid = ObjectId("507f1f77bcf86cd799439011")
        result = normalize_id_for_database(oid)
        assert result == "507f1f77bcf86cd799439011"
        assert isinstance(result, str)

    def test_normalize_id_for_database_string(self):
        """Test normalization of string (should remain same)."""
        id_str = "some_id"
        result = normalize_id_for_database(id_str)
        assert result == id_str

    def test_normalize_id_for_database_other_type(self):
        """Test normalization of other types to string."""
        result = normalize_id_for_database(123)
        assert result == "123"

    @patch('app.models.mongodb_database.mongodb')
    def test_find_document_by_id_string(self, mock_mongo):
        """Test finding document by string ID."""
        mock_mongo.find_one.return_value = {"_id": "test_id", "name": "Test"}
        result = find_document_by_id("collection", "test_id")
        assert result["_id"] == "test_id"
        mock_mongo.find_one.assert_any_call("collection", {"_id": "test_id"})

    @patch('app.models.mongodb_database.mongodb')
    def test_find_document_by_id_object_id(self, mock_mongo):
        """Test finding document by ObjectId (fallback)."""
        oid_str = "507f1f77bcf86cd799439011"
        oid = ObjectId(oid_str)
        # First call (string ID) returns None, second (ObjectId) returns doc
        mock_mongo.find_one.side_effect = [None, {"_id": oid, "name": "Test"}]
        result = find_document_by_id("collection", oid_str)
        assert result["_id"] == oid
        assert mock_mongo.find_one.call_count == 2

    @patch('app.models.mongodb_database.mongodb')
    def test_find_document_by_id_not_found(self, mock_mongo):
        """Test when no document is found by any means."""
        mock_mongo.find_one.return_value = None
        result = find_document_by_id("collection", "not_exist")
        assert result is None
        # find_document_by_id tries:
        # 1. string id
        # 2. object id (if 24 chars, which "not_exist" is not)
        # 3. converted id (from convert_id_for_query)
        # "not_exist" is 9 chars, so it only does string id and converted id (which is the same)
        assert mock_mongo.find_one.call_count == 2

    @patch('app.models.mongodb_database.mongodb')
    def test_find_user_by_id_success(self, mock_mongo):
        """Test successful user lookup."""
        mock_mongo.find_one.return_value = {"_id": "user123", "username": "tester"}
        result = find_user_by_id("user123")
        assert result["username"] == "tester"
        mock_mongo.find_one.assert_called_with("users", {"_id": "user123"})

    @patch('app.models.mongodb_database.mongodb')
    def test_find_user_by_id_not_found(self, mock_mongo):
        """Test user lookup when user doesn't exist."""
        mock_mongo.find_one.return_value = None
        result = find_user_by_id("nonexistent")
        assert result is None

    @patch('app.models.mongodb_database.mongodb')
    def test_normalize_all_ids_in_collection(self, mock_mongo):
        """Test bulk normalization of IDs to strings."""
        oid = ObjectId("507f1f77bcf86cd799439011")
        mock_mongo.find.return_value = [
            {"_id": oid, "name": "Item 1"},
            {"_id": "string_id", "name": "Item 2"}
        ]

        result = normalize_all_ids_in_collection("items")
        assert result == 1  # Only Item 1 needed conversion

        mock_mongo.delete_one.assert_called_with("items", {"_id": oid})
        mock_mongo.insert_one.assert_called_once()
        inserted_doc = mock_mongo.insert_one.call_args[0][1]
        assert inserted_doc["_id"] == str(oid)

    @patch('app.models.mongodb_database.mongodb')
    def test_resolve_user_group_names_empty(self, mock_mongo):
        """Test resolving group names with empty input."""
        result = resolve_user_group_names([])
        assert result == ''

    @patch('app.models.mongodb_database.mongodb')
    def test_resolve_user_group_names_valid(self, mock_mongo):
        """Test resolving valid group IDs to names."""
        oid1_str = "507f1f77bcf86cd799439011"
        oid1 = ObjectId(oid1_str)
        mock_mongo.find_one.side_effect = [
            {"_id": oid1, "name": "Admins"},
            {"_id": "group2", "name": "Users"}
        ]

        result = resolve_user_group_names([oid1_str, "group2"])
        assert result == "Admins, Users"

    @patch('app.models.mongodb_database.mongodb')
    def test_resolve_user_group_names_partially_missing(self, mock_mongo):
        """Test resolving group names when some IDs don't exist in DB."""
        mock_mongo.find_one.return_value = None

        result = resolve_user_group_names(["missing1", "missing2"])
        assert result == "missing1, missing2"
