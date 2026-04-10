import pytest
from unittest.mock import MagicMock, patch
from app.services.tool_service import ToolService
from flask import Flask

@pytest.fixture
def app():
    app = Flask(__name__)
    return app

@pytest.fixture
def tool_service():
    return ToolService()

@patch('app.services.tool_service.mongodb')
def test_get_tool_statistics_happy_path(mock_mongodb, tool_service, app):
    # Mock return for aggregate
    mock_mongodb.aggregate.return_value = [{
        'base_counts': [
            {'total': 10, 'defect': 2}
        ],
        'lending_stats': [
            {'borrowed': 3, 'available': 5}
        ],
        'categories': [
            {'_id': 'Cat1', 'count': 4},
            {'_id': 'Cat2', 'count': 6}
        ],
        'locations': [
            {'_id': 'Loc1', 'count': 7},
            {'_id': 'Loc2', 'count': 3}
        ]
    }]

    with app.test_request_context():
        from flask import g
        g.current_department = 'Dept1'
        stats = tool_service.get_tool_statistics()

    assert stats['total_tools'] == 10
    assert stats['available_tools'] == 5
    assert stats['borrowed_tools'] == 3
    assert stats['defect_tools'] == 2
    assert stats['categories']['Cat1'] == 4
    assert stats['categories']['Cat2'] == 6
    assert stats['locations']['Loc1'] == 7
    assert stats['locations']['Loc2'] == 3

@patch('app.services.tool_service.mongodb')
def test_get_tool_statistics_empty_data(mock_mongodb, tool_service, app):
    # Mock return for aggregate on empty collection
    mock_mongodb.aggregate.return_value = [{
        'base_counts': [],
        'lending_stats': [],
        'categories': [],
        'locations': []
    }]

    with app.test_request_context():
        from flask import g
        g.current_department = 'Dept1'
        stats = tool_service.get_tool_statistics()

    assert stats['total_tools'] == 0
    assert stats['available_tools'] == 0
    assert stats['borrowed_tools'] == 0
    assert stats['defect_tools'] == 0
    assert stats['categories'] == {}
    assert stats['locations'] == {}
