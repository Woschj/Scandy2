#!/usr/bin/env python3
"""
Ticket-History API-Routen für Scandy
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.services.ticket_history_service import ticket_history_service

bp = Blueprint('ticket_history', __name__, url_prefix='/api/tickets')


@bp.route('/<ticket_id>/history')
@login_required
def get_ticket_history(ticket_id):
    """
    Holt die Historie eines Tickets
    
    Args:
        ticket_id: ID des Tickets
        
    Returns:
        JSON: Liste der History-Einträge
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        history = ticket_history_service.get_ticket_history(ticket_id, limit)
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Fehler beim Laden der Historie: {str(e)}'
        }), 500


@bp.route('/user/<username>/activity')
@login_required  
def get_user_activity(username):
    """
    Holt die Aktivitäten eines Nutzendes
    
    Args:
        username: Nutzendename
        
    Returns:
        JSON: Liste der Nutzende-Aktivitäten
    """
    try:
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        activity = ticket_history_service.get_user_activity(username, days, limit)
        
        return jsonify({
            'success': True,
            'activity': activity,
            'count': len(activity)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Fehler beim Laden der Nutzende-Aktivitäten: {str(e)}'
        }), 500 