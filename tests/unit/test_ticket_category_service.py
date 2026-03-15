import pytest
from unittest.mock import patch
from flask import Flask, g
from app.services.ticket_category_service import TicketCategoryService


@pytest.fixture
def app_context():
    app = Flask(__name__)
    with app.app_context():
        yield app


def test_get_ticket_categories_for_department_none_no_g(app_context):
    """Test returning empty list when department is None and no g.current_department"""
    with patch.object(TicketCategoryService, "get_current_department", return_value=None):
        categories = TicketCategoryService.get_ticket_categories_for_department()
        assert categories == []


def test_get_ticket_categories_for_department_empty_string(app_context):
    """Test returning empty list when department is empty string"""
    categories = TicketCategoryService.get_ticket_categories_for_department("")
    assert categories == []


def test_get_ticket_categories_for_department_valid(app_context):
    """Test returning valid sorted categories for a department"""
    mock_db_results = [{"name": "Zebra"}, {"name": "  Alpha  "}, {"name": "Beta"}]
    with patch(
        "app.services.ticket_category_service.mongodb.find", return_value=mock_db_results
    ) as mock_find:
        categories = TicketCategoryService.get_ticket_categories_for_department("IT")

        mock_find.assert_called_once_with(
            "ticket_categories", {"department": "IT", "deleted": {"$ne": True}}
        )
        assert categories == ["Alpha", "Beta", "Zebra"]


def test_get_ticket_categories_for_department_with_empty_names(app_context):
    """Test filtering out empty or whitespace-only names"""
    mock_db_results = [{"name": "Valid"}, {"name": ""}, {"name": "   "}, {}]  # missing name key
    with patch("app.services.ticket_category_service.mongodb.find", return_value=mock_db_results):
        categories = TicketCategoryService.get_ticket_categories_for_department("HR")
        assert categories == ["Valid"]


def test_get_ticket_categories_for_department_db_exception(app_context):
    """Test returning empty list when database throws an exception"""
    with patch(
        "app.services.ticket_category_service.mongodb.find", side_effect=Exception("DB Error")
    ):
        categories = TicketCategoryService.get_ticket_categories_for_department("Finance")
        assert categories == []


def test_get_ticket_categories_for_department_from_g(app_context):
    """Test getting department from g.current_department when department is None"""
    g.current_department = "Marketing"

    mock_db_results = [{"name": "Campaigns"}]
    with patch(
        "app.services.ticket_category_service.mongodb.find", return_value=mock_db_results
    ) as mock_find:
        categories = TicketCategoryService.get_ticket_categories_for_department(None)

        mock_find.assert_called_once_with(
            "ticket_categories", {"department": "Marketing", "deleted": {"$ne": True}}
        )
        assert categories == ["Campaigns"]


def test_get_current_department_exception():
    """Test get_current_department handling exception when outside app context"""
    assert TicketCategoryService.get_current_department() is None
