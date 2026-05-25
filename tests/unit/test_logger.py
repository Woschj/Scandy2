import pytest
import logging
from unittest.mock import patch, MagicMock, call
import os
from pathlib import Path

from app.utils.logger import (
    setup_logger,
    init_app_logger,
    create_specialized_loggers,
    log_security_event,
    log_user_action,
    log_database_operation,
    log_api_request,
    log_performance_metric,
    loggers
)

def test_setup_logger():
    with patch('os.makedirs') as mock_makedirs, patch('app.utils.logger.RotatingFileHandler') as mock_handler:
        logger = setup_logger('test.logger', 'logs/test.log')
        mock_makedirs.assert_called_once_with('logs', exist_ok=True)
        assert logger.name == 'test.logger'
        assert logger.level == logging.INFO

def test_init_app_logger():
    app = MagicMock()
    app.root_path = '/mock/path'
    app.logger.handlers = []

    with patch('pathlib.Path.mkdir') as mock_mkdir, patch('app.utils.logger.RotatingFileHandler') as mock_handler:
        init_app_logger(app)
        mock_mkdir.assert_called_once_with(exist_ok=True)
        assert len(app.logger.handlers) == 0 # we replaced it with addHandler on app.logger
        assert app.logger.setLevel.called
        assert app.logger.propagate is False

def test_create_specialized_loggers():
    with patch('app.utils.logger.setup_logger') as mock_setup:
        mock_setup.return_value = MagicMock()
        specialized = create_specialized_loggers()
        assert 'security' in specialized
        assert 'user_actions' in specialized
        assert 'database' in specialized
        assert 'api' in specialized
        assert 'errors' in specialized
        assert 'performance' in specialized
        assert mock_setup.call_count == 6

def test_log_security_event():
    with patch.dict(loggers, {'security': MagicMock(), 'errors': MagicMock()}):
        log_security_event('login_success', 'user1', '127.0.0.1', 'Details here')
        loggers['security'].warning.assert_called_once()
        assert 'SECURITY_EVENT' in loggers['security'].warning.call_args[0][0]
        assert 'login_success' in loggers['security'].warning.call_args[0][0]
        loggers['errors'].error.assert_not_called()

def test_log_security_event_critical():
    with patch.dict(loggers, {'security': MagicMock(), 'errors': MagicMock()}):
        log_security_event('login_failed', 'user1', '127.0.0.1', 'Details here')
        loggers['security'].warning.assert_called_once()
        loggers['errors'].error.assert_called_once()
        assert 'KRITISCHES SICHERHEITSEREIGNIS: login_failed' in loggers['errors'].error.call_args[0][0]

def test_log_user_action():
    with patch.dict(loggers, {'user_actions': MagicMock()}):
        log_user_action('create_ticket', 'user1', 'Ticket 123')
        loggers['user_actions'].info.assert_called_once()
        assert 'USER_ACTION: create_ticket' in loggers['user_actions'].info.call_args[0][0]

def test_log_database_operation_success_with_duration():
    with patch.dict(loggers, {'database': MagicMock()}):
        log_database_operation('find', 'tickets', duration=0.123, success=True)
        loggers['database'].info.assert_called_once()
        msg = loggers['database'].info.call_args[0][0]
        assert 'DB_OPERATION: find' in msg
        assert 'Collection: tickets' in msg
        assert 'Status: SUCCESS' in msg
        assert '(0.123s)' in msg

def test_log_database_operation_failed_no_duration():
    with patch.dict(loggers, {'database': MagicMock()}):
        log_database_operation('insert', 'users', success=False)
        loggers['database'].info.assert_called_once()
        msg = loggers['database'].info.call_args[0][0]
        assert 'DB_OPERATION: insert' in msg
        assert 'Collection: users' in msg
        assert 'Status: FAILED' in msg
        assert '(' not in msg

def test_log_api_request_full():
    with patch.dict(loggers, {'api': MagicMock()}):
        log_api_request('GET', '/api/tickets', 'user1', 200, 0.045)
        loggers['api'].info.assert_called_once()
        msg = loggers['api'].info.call_args[0][0]
        assert 'API_REQUEST: GET /api/tickets' in msg
        assert 'User: user1' in msg
        assert 'Status: 200' in msg
        assert '(0.045s)' in msg

def test_log_api_request_minimal():
    with patch.dict(loggers, {'api': MagicMock()}):
        log_api_request('POST', '/api/login')
        loggers['api'].info.assert_called_once()
        msg = loggers['api'].info.call_args[0][0]
        assert 'API_REQUEST: POST /api/login' in msg
        assert 'User:' not in msg
        assert 'Status:' not in msg
        assert 's)' not in msg

def test_log_performance_metric_with_unit():
    with patch.dict(loggers, {'performance': MagicMock()}):
        log_performance_metric('page_load', 1.2, 'seconds')
        loggers['performance'].info.assert_called_once()
        msg = loggers['performance'].info.call_args[0][0]
        assert 'PERFORMANCE: page_load: 1.2 seconds' in msg

def test_log_performance_metric_no_unit():
    with patch.dict(loggers, {'performance': MagicMock()}):
        log_performance_metric('active_users', 42)
        loggers['performance'].info.assert_called_once()
        msg = loggers['performance'].info.call_args[0][0]
        assert 'PERFORMANCE: active_users: 42' in msg
        assert ' seconds' not in msg
