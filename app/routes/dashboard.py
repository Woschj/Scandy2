from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBConsumable
from app.config import Config
from app.utils.decorators import login_required, not_teilnehmer_required
from flask_login import current_user

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    """Dashboard-Hauptseite"""
    # Für Teilnehmende: Weiterleitung zu Wochenberichten
    if current_user.role == 'teilnehmer':
        return redirect(url_for('workers.teilnehmer_timesheet_list'))
    
    # Verwende den zentralen Statistics Service
    from app.services.statistics_service import StatisticsService
    
    # Alle Statistiken auf einmal laden
    stats = StatisticsService.get_all_statistics()
    
    return render_template('dashboard/index.html',
                         stats=stats,
                         consumables_forecast=stats['consumables_forecast'],
                         duplicate_barcodes=stats['duplicate_barcodes'],
                         overdue_loans=stats['overdue_loans']) 