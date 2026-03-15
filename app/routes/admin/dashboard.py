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
        # Umfassende automatische Reparatur beim Dashboard-Aufruf
        try:
            from app.services.admin_debug_service import AdminDebugService
            from app.services.admin_backup_service import AdminBackupService

            # 1. Standard Dashboard-Reparatur
            AdminDebugService.fix_missing_created_at_fields()
            logger.info("Standard Dashboard-Reparatur durchgeführt")

            # 2. Umfassende Datentyp-Reparatur
            dashboard_fixes = AdminBackupService.fix_dashboard_after_backup()
            if dashboard_fixes.get('total', 0) > 0:
                logger.info(f"Umfassende Dashboard-Reparatur durchgeführt: {dashboard_fixes}")

            # 3. Zusätzliche Dashboard-spezifische Reparatur
            try:
                from app.models.mongodb_database import mongodb

                # Repariere spezifische Dashboard-Probleme
                dashboard_fixes_count = 0

                # Stelle sicher, dass alle Tools gültige Felder haben
                all_tools = mongodb.find('tools', {})
                for tool in all_tools:
                    try:
                        updates = {}

                        # Stelle sicher, dass name Feld existiert
                        if 'name' not in tool or not tool['name']:
                            updates['name'] = tool.get('description', 'Unbekanntes Tool')

                        # Stelle sicher, dass barcode Feld existiert
                        if 'barcode' not in tool:
                            updates['barcode'] = str(tool.get('_id', ''))

                        # Stelle sicher, dass status Feld existiert
                        if 'status' not in tool:
                            updates['status'] = 'verfügbar'

                        # Stelle sicher, dass location Feld existiert
                        if 'location' not in tool:
                            updates['location'] = 'Unbekannt'

                        if updates:
                            mongodb.update_one('tools', {'_id': tool['_id']}, {'$set': updates})
                            dashboard_fixes_count += 1

                    except Exception as e:
                        logger.warning(f"Fehler bei Tool-Reparatur: [Interner Fehler]")
                        continue

                # Stelle sicher, dass alle Workers gültige Felder haben
                all_workers = mongodb.find('workers', {})
                for worker in all_workers:
                    try:
                        updates = {}

                        # Stelle sicher, dass name Feld existiert
                        if 'name' not in worker or not worker['name']:
                            firstname = worker.get('firstname', '')
                            lastname = worker.get('lastname', '')
                            if firstname or lastname:
                                updates['name'] = f"{firstname} {lastname}".strip()
                            else:
                                updates['name'] = 'Unbekannter Worker'

                        # Stelle sicher, dass barcode Feld existiert
                        if 'barcode' not in worker:
                            updates['barcode'] = str(worker.get('_id', ''))

                        if updates:
                            mongodb.update_one('workers', {'_id': worker['_id']}, {'$set': updates})
                            dashboard_fixes_count += 1

                    except Exception as e:
                        logger.warning(f"Fehler bei Worker-Reparatur: [Interner Fehler]")
                        continue

                if dashboard_fixes_count > 0:
                    logger.info(f"Dashboard-spezifische Reparatur: {dashboard_fixes_count} Korrekturen")

            except Exception as e:
                logger.warning(f"Dashboard-spezifische Reparatur fehlgeschlagen: [Interner Fehler]")

        except Exception as e:
            logger.warning(f"Automatische Dashboard-Reparatur fehlgeschlagen: [Interner Fehler]")

        # Verwende den AdminDashboardService für alle Dashboard-Daten
        recent_activity = AdminDashboardService.get_recent_activity()
        material_usage = AdminDashboardService.get_material_usage()
        warnings = AdminDashboardService.get_warnings()
        consumables_forecast = AdminDashboardService.get_consumables_forecast()
        consumable_trend = AdminDashboardService.get_consumable_trend()

        # Starseiten-Hinweise (aktuelle Abteilung)
        try:
            from flask import g
            from app.services.admin_notification_service import AdminNotificationService
            current_department = getattr(g, 'current_department', None)
            raw_notices = AdminNotificationService.get_all_notices(current_department)
            # Nur aktive, nach Priorität/Datum sortiert
            notices = [n for n in raw_notices if n.get('is_active', False)]
            from datetime import datetime as _dt
            notices.sort(key=lambda x: (int(x.get('priority', 0)), x.get('created_at') or _dt.min), reverse=True)
        except Exception as _nerr:
            logger.warning(f"Dashboard: Hinweise konnten nicht geladen werden: {_nerr}")
            notices = []

        # Hole zusätzliche Statistiken
        try:
            total_tools = mongodb.count_documents('tools', {'deleted': {'$ne': True}})
            total_consumables = mongodb.count_documents('consumables', {'deleted': {'$ne': True}})
            total_workers = mongodb.count_documents('workers', {'deleted': {'$ne': True}})
            total_tickets = mongodb.count_documents('tickets', {})

            # Tool-Statistiken - Berücksichtige tatsächliche Ausleihen
            all_tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
            current_lendings = list(mongodb.find('lendings', {'returned_at': {'$exists': False}}))

            # Debug: Zeige Ausleihen an
            logger.info(f"Dashboard Debug: {len(current_lendings)} aktuelle Ausleihen gefunden")
            for lending in current_lendings:
                logger.info(f"  Ausleihe: Tool={lending.get('tool_barcode')}, Worker={lending.get('worker_barcode')}, ID={lending.get('_id')}")

            # Erstelle Set der ausgeliehenen Tool-Barcodes (entferne Duplikate)
            # Bolt ⚡: Collect worker barcodes as well for bulk fetching
            lent_barcodes = set()
            worker_barcodes = set()
            for lending in current_lendings:
                tb = lending.get('tool_barcode')
                wb = lending.get('worker_barcode')
                if tb: lent_barcodes.add(tb)
                if wb: worker_barcodes.add(wb)

            # Bolt ⚡: Optimization - Bulk fetch tools and workers involved in active lendings to avoid N+1 queries
            tools_cache = {t.get('barcode'): t for t in mongodb.find('tools', {'barcode': {'$in': list(lent_barcodes)}})}
            workers_cache = {w.get('barcode'): w for w in mongodb.find('workers', {'barcode': {'$in': list(worker_barcodes)}})}

            logger.info(f"Dashboard Debug: {len(lent_barcodes)} eindeutige ausgeliehene Tools")

            available_count = 0
            lent_count = 0
            defect_count = 0

            for tool in all_tools:
                tool_barcode = tool.get('barcode')
                status = tool.get('status', 'verfügbar').lower()

                # Prüfe ob Tool tatsächlich ausgeliehen ist
                is_lent = tool_barcode in lent_barcodes

                if 'defekt' in status or 'defect' in status or 'broken' in status:
                    defect_count += 1
                elif is_lent:
                    lent_count += 1
                elif 'verfügbar' in status or 'available' in status:
                    available_count += 1
                else:
                    # Unbekannter Status - als verfügbar zählen
                    available_count += 1

            tool_stats = {
                'total': total_tools,
                'available': available_count,
                'lent': lent_count,
                'defect': defect_count
            }

            # Consumable-Statistiken - Verbesserte Logik
            consumables = list(mongodb.find('consumables', {'deleted': {'$ne': True}}))
            sufficient = 0
            warning = 0
            critical = 0

            for consumable in consumables:
                # Verwende verschiedene mögliche Feldnamen für den Bestand
                stock = consumable.get('stock', consumable.get('quantity', 0))
                warning_threshold = consumable.get('warning_threshold', 10)
                critical_threshold = consumable.get('critical_threshold', 5)

                # Konvertiere zu int falls nötig
                try:
                    stock = int(stock) if stock is not None else 0
                    warning_threshold = int(warning_threshold) if warning_threshold is not None else 10
                    critical_threshold = int(critical_threshold) if critical_threshold is not None else 5
                except (ValueError, TypeError):
                    stock = 0
                    warning_threshold = 10
                    critical_threshold = 5

                if stock >= warning_threshold:
                    sufficient += 1
                elif stock >= critical_threshold:
                    warning += 1
                else:
                    critical += 1

            consumable_stats = {
                'total': total_consumables,
                'sufficient': sufficient,
                'warning': warning,
                'critical': critical
            }

            # Worker-Statistiken
            workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}))
            worker_stats = {
                'total': total_workers,
                'by_department': []
            }

            # Gruppiere nach Abteilung
            dept_counts = {}
            for worker in workers:
                dept = worker.get('department', 'Ohne Abteilung')
                dept_counts[dept] = dept_counts.get(dept, 0) + 1

            for dept, count in dept_counts.items():
                worker_stats['by_department'].append({
                    'name': dept,
                    'count': count
                })

            # Tool-Warnungen - Erweiterte Logik
            tool_warnings = []

            # Defekte Tools
            defect_tools = list(mongodb.find('tools', {'status': 'defekt', 'deleted': {'$ne': True}}))
            for tool in defect_tools:
                tool_warnings.append({
                    'name': tool.get('name', 'Unbekanntes Tool'),
                    'status': 'Defekt',
                    'severity': 'error'
                })

            # Warnung bei doppelten Ausleihen
            lending_counts = {}
            for lending in current_lendings:
                tool_barcode = lending.get('tool_barcode')
                if tool_barcode:
                    lending_counts[tool_barcode] = lending_counts.get(tool_barcode, 0) + 1

            duplicate_lendings = {barcode: count for barcode, count in lending_counts.items() if count > 1}
            if duplicate_lendings:
                logger.warning(f"Dashboard Debug: Doppelte Ausleihen gefunden: {duplicate_lendings}")
                # Bolt ⚡: Optimization - Use bulk-fetched tools_cache instead of mongodb.find_one
                for barcode, count in duplicate_lendings.items():
                    tool = tools_cache.get(barcode)
                    if tool:
                        tool_warnings.append({
                            'name': f"{tool.get('name', 'Unbekanntes Tool')} (Barcode: {barcode})",
                            'status': f'Doppelte Ausleihen: {count}x',
                            'severity': 'warning'
                        })

            # Bolt ⚡: Removed redundant overdue lending and consumable stock check loops here
            # as these are already computed and provided via AdminDashboardService.get_warnings()
            # which is assigned to the 'warnings' variable used in the template.

            # Aktuelle Ausleihen
            # Bolt ⚡: Reuse current_lendings fetched earlier to avoid redundant DB call
            # current_lendings = list(mongodb.find('lendings', {'returned_at': {'$exists': False}}))

            # Verarbeite Ausleihen für Anzeige
            processed_lendings = []

            # Batch-Fetch für Tools und Worker zur Vermeidung von N+1 Queries
            t_codes = list({
                l.get('tool_barcode') for l in current_lendings
                if l.get('tool_barcode')
            })
            w_codes = list({
                l.get('worker_barcode') for l in current_lendings
                if l.get('worker_barcode')
            })

            tools_cache = {}
            if t_codes:
                tools = mongodb.find('tools', {'barcode': {'$in': t_codes}})
                tools_cache = {t.get('barcode'): t for t in tools}

            workers_cache = {}
            if w_codes:
                workers = mongodb.find('workers', {'barcode': {'$in': w_codes}})
                workers_cache = {w.get('barcode'): w for w in workers}

            for lending in current_lendings:
                try:
                    tool = tools_cache.get(lending.get('tool_barcode', ''))
                    worker = workers_cache.get(lending.get('worker_barcode', ''))

                    if tool and worker:
                        # Sichere Datumsbehandlung
                        lent_at = lending.get('lent_at')
                        if isinstance(lent_at, str):
                            try:
                                lent_at = datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S.%f')
                            except ValueError:
                                try:
                                    lent_at = datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    lent_at = datetime.now()
                        elif not isinstance(lent_at, datetime):
                            lent_at = datetime.now()

                        processed_lendings.append({
                            'tool_name': tool.get('name', 'Unbekanntes Tool'),
                            'worker_name': worker.get('name', 'Unbekannter Worker'),
                            'lent_at': lent_at,
                            'days_lent': (datetime.now() - lent_at).days
                        })
                except Exception as e:
                    logger.warning(f"Fehler bei Verarbeitung einer Ausleihe: [Interner Fehler]")
                    continue

            # Sortiere nach Ausleihdatum (älteste zuerst)
            processed_lendings.sort(key=lambda x: x.get('lent_at', datetime.now()))

        except Exception as e:
            logger.error(f"Fehler beim Laden der Dashboard-Statistiken: [Interner Fehler]")
            # Fallback-Werte
            tool_stats = {'total': 0, 'available': 0, 'lent': 0, 'defect': 0}
            consumable_stats = {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0}
            worker_stats = {'total': 0, 'by_department': []}
            tool_warnings = []
            consumable_warnings = []
            processed_lendings = []
            total_tools = 0
            total_consumables = 0
            total_workers = 0
            total_tickets = 0

        # Bolt ⚡: Merge manual tool_warnings into the main warnings object
        if tool_warnings:
            if 'defect_tools' not in warnings: warnings['defect_tools'] = []
            warnings['defect_tools'].extend([tw for tw in tool_warnings if tw.get('status') == 'Defekt'])
            # Add duplicate lendings to warnings
            warnings['duplicate_lendings'] = [tw for tw in tool_warnings if 'Doppelte Ausleihen' in tw.get('status', '')]

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
