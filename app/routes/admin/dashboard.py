from .blueprint import bp
from .shared import *
@bp.route('/')
@mitarbeiter_required
def index():
    """Admin-Startseite"""
    return redirect(url_for('admin.dashboard'))

@bp.route('/dashboard')
@mitarbeiter_required
def dashboard():
    """Admin-Dashboard"""
    try:
        # Verwende den AdminDashboardService für alle Dashboard-Daten
        recent_activity = AdminDashboardService.get_recent_activity()
        material_usage = AdminDashboardService.get_material_usage()
        warnings = AdminDashboardService.get_warnings()
        consumables_forecast = AdminDashboardService.get_consumables_forecast()
        consumable_trend = AdminDashboardService.get_consumable_trend()

        # Starseiten-Hinweise (aktuelle Abteilung) (Bolt ⚡ Optimiert)
        try:
            from flask import g
            from app.services.admin_notification_service import AdminNotificationService
            current_department = getattr(g, 'current_department', None)
            # Nutze die optimierte Methode für aktive Hinweise (filtert & sortiert in der DB)
            notices = AdminNotificationService.get_active_notices(current_department)
        except Exception as _nerr:
            logger.warning(f"Dashboard: Hinweise konnten nicht geladen werden: {_nerr}")
            notices = []

        # Hole Statistiken und Ausleihen über optimierte Services (Bolt ⚡)
        try:
            from app.services.statistics_service import StatisticsService
            from app.services.lending_service import LendingService

            stats = StatisticsService.get_all_statistics()
            tool_stats = stats.get('tool_stats', {})
            consumable_stats = stats.get('consumable_stats', {})
            worker_stats = stats.get('worker_stats', {})
            ticket_stats = stats.get('ticket_stats', {})

            total_tools = tool_stats.get('total', 0)
            total_consumables = consumable_stats.get('total', 0)
            total_workers = worker_stats.get('total', 0)
            total_tickets = ticket_stats.get('total', 0)

            # Hole aktive Ausleihen (bereits optimiert via Aggregation)
            current_lendings_raw = LendingService.get_active_lendings()

            # Verarbeite für die Anzeige im Dashboard
            processed_lendings = []
            for lending in current_lendings_raw:
                lent_at = lending.get('lent_at')
                if isinstance(lent_at, str):
                    try:
                        lent_at = datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        lent_at = datetime.now()
                elif not isinstance(lent_at, datetime):
                    lent_at = datetime.now()

                processed_lendings.append({
                    'tool_name': lending.get('tool_name', 'Unbekanntes Tool'),
                    'worker_name': lending.get('worker_name', 'Unbekannter Worker'),
                    'lent_at': lent_at,
                    'days_lent': (datetime.now() - lent_at).days if lent_at else 0
                })

            # Sortiere nach Ausleihdatum (älteste zuerst)
            processed_lendings.sort(key=lambda x: x.get('lent_at', datetime.now()))

        except Exception as e:
            logger.error(f"Fehler beim Laden der Dashboard-Statistiken: [Interner Fehler]")
            tool_stats = {'total': 0, 'available': 0, 'lent': 0, 'defect': 0}
            consumable_stats = {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0}
            worker_stats = {'total': 0, 'by_department': []}
            processed_lendings = []
            total_tools = 0
            total_consumables = 0
            total_workers = 0
            total_tickets = 0

        return render_template('admin/dashboard.html',
                             recent_activity=recent_activity,
                             material_usage=material_usage,
                             warnings=warnings,
                             consumables_forecast=consumables_forecast,
                             consumable_trend=consumable_trend,
                             total_tools=total_tools,
                             total_consumables=total_consumables,
                             total_workers=total_workers,
                             total_tickets=total_tickets,
                             current_lendings=processed_lendings,
                             tool_stats=tool_stats,
                             consumable_stats=consumable_stats,
                             worker_stats=worker_stats,
                             notices=notices)

    except Exception as e:
        logger.error(f"Fehler beim Laden des Dashboards: [Interner Fehler]")
        flash('Fehler beim Laden des Dashboards', 'error')
        return render_template('admin/dashboard.html',
                             recent_activity=[],
                             material_usage={'usage_data': [], 'period_days': 30},
                             warnings={'defect_tools': [], 'overdue_lendings': [], 'low_stock_consumables': [], 'duplicate_lendings': []},
                             consumables_forecast=[],
                             consumable_trend={},
                             total_tools=0,
                             total_consumables=0,
                             total_workers=0,
                             total_tickets=0,
                             current_lendings=[],
                             tool_stats={'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
                             consumable_stats={'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
                             worker_stats={'total': 0, 'by_department': []},
                             notices=[])

@bp.route('/tickets/<id>/export')
@login_required
@admin_required
def export_ticket(id):
    """Exportiert das Ticket als ausgefülltes Word-Dokument."""
    try:
        # Verwende den AdminTicketService
        success, message, file_path = AdminTicketService.export_ticket_as_word(id)

        if success and file_path:
            # Sende das Dokument
            ticket = find_document_by_id('tickets', id)
            ticket_number = ticket.get('ticket_number', id) if ticket else id

            # Pfad-Validierung für Sicherheit
            from flask import send_from_directory

            directory = os.path.join(current_app.root_path, 'static', 'uploads')
            filename = os.path.basename(file_path)

            return send_from_directory(directory, filename, as_attachment=True, download_name=f'ticket_{ticket_number}_export.docx')
        else:
            flash('Fehler beim Exportieren des Tickets.', 'error')
            return redirect(url_for('admin.ticket_detail', ticket_id=id))

    except Exception as e:
        logging.error(f"Fehler beim Generieren des Word-Dokuments: [Interner Fehler]", exc_info=True)
        flash('Fehler beim Generieren des Dokuments.', 'error')
        return redirect(url_for('admin.ticket_detail', ticket_id=id))

@bp.route('/export_all_data')
@admin_required
def export_all_data():
    """Exportiert alle Daten als Excel-Datei"""
    try:
        # Hole alle Daten aus der Datenbank
        tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
        workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}))
        consumables = list(mongodb.find('consumables', {'deleted': {'$ne': True}}))
        lendings = list(mongodb.find('lendings', {}))
        settings = list(mongodb.find('settings', {}))

        # Erstelle Excel-Datei mit mehreren Arbeitsblättern
        data_dict = {
            'Werkzeuge': tools,
            'Mitarbeiter': workers,
            'Verbrauchsmaterial': consumables,
            'Ausleihverlauf': lendings,
            'Settings': settings
        }

        # Erstelle Excel-Datei
        excel_file = create_multi_sheet_excel(data_dict)

        # Sende Datei als Download
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=f'scandy_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        logger.error(f"Fehler beim Exportieren der Daten: [Interner Fehler]")
        flash('Fehler beim Exportieren der Daten', 'error')
        return redirect(url_for('admin.system'))

@bp.route('/export_excel_detailed')
@admin_required
def export_excel_detailed():
    """Exportiert alle Scandy-Daten in eine detaillierte Excel-Datei"""
    try:
        logger.info(f"Detaillierter Excel-Export gestartet von Benutzer: {current_user.username}")

        # Erstelle Excel-Export
        export_service = ExcelExportService()
        excel_file = export_service.generate_complete_export()

        # Generiere Dateinamen mit Zeitstempel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'scandy_detailliert_{timestamp}.xlsx'

        logger.info(f"Detaillierter Excel-Export erfolgreich erstellt: {filename}")

        return send_file(
            excel_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        logger.error(f"Fehler beim detaillierten Excel-Export: [Interner Fehler]", exc_info=True)
        flash('Fehler beim Generieren des detaillierten Excel-Exports', 'error')
        return redirect(url_for('admin.dashboard'))
