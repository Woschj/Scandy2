from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import current_user
from app.models.mongodb_database import mongodb, is_feature_enabled
from app.utils.decorators import admin_required, login_required, mitarbeiter_required, not_teilnehmer_required
from app.utils.permissions import permission_required
from app.utils.database_helpers import get_categories_scoped, get_locations_scoped, get_categories_from_settings, get_locations_from_settings
from datetime import datetime, timedelta
import logging
from app.services.consumable_service import ConsumableService

# Blueprint mit URL-Präfix definieren
bp = Blueprint('consumables', __name__)
logger = logging.getLogger(__name__)

@bp.route('/')
@login_required
@permission_required('consumables', 'view')
@not_teilnehmer_required
def index():
    """Zeigt alle Verbrauchsmaterialien an"""
    # Prüfe ob Verbrauchsmaterial-Feature aktiviert ist
    if not is_feature_enabled('consumables'):
        flash('Verbrauchsmaterial-Verwaltung ist deaktiviert', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Hole alle Verbrauchsmaterialien der aktuellen Abteilung
        from flask import g
        filter_query = {}
        if getattr(g, 'current_department', None):
            filter_query['department'] = g.current_department
        consumables = list(mongodb.find('consumables', filter_query, sort=[('name', 1)]))
        
        # Hole Kategorien und Standorte strikt abteilungsgetrennt
        categories = get_categories_scoped()
        locations = get_locations_scoped()
        
        return render_template('consumables/index.html',
                             consumables=consumables,
                             categories=categories,
                             locations=locations)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Verbrauchsmaterialien: {str(e)}")
        flash('Fehler beim Laden der Verbrauchsmaterialien', 'error')
        return redirect(url_for('main.index'))

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('consumables', 'create')
def add():
    """Fügt ein neues Verbrauchsmaterial hinzu"""
    if request.method == 'POST':
        try:
            from flask import g
            if not getattr(g, 'current_department', None):
                flash('Bitte Abteilung wählen, bevor Sie ein Verbrauchsmaterial anlegen', 'error')
                categories = get_categories_scoped()
                locations = get_locations_scoped()
                return render_template('consumables/add.html', 
                                     categories=categories, 
                                     locations=locations,
                                     form_data=request.form)
            data = {
                'name': request.form.get('name'),
                'barcode': request.form.get('barcode'),
                'category': request.form.get('category'),
                'location': request.form.get('location'),
                'quantity': request.form.get('quantity', 0),
                'min_quantity': request.form.get('min_quantity', 0),
                'description': request.form.get('description', '')
            }
            
            # Benutzerdefinierte Felder verarbeiten
            try:
                from app.services.custom_fields_service import CustomFieldsService
                success_custom, error_msg, custom_values = CustomFieldsService.process_custom_fields_from_form('consumables', request.form)
                if success_custom:
                    data['custom_fields'] = custom_values
                else:
                    flash(f'Fehler bei benutzerdefinierten Feldern: {error_msg}', 'error')
                    categories = get_categories_scoped()
                    locations = get_locations_scoped()
                    return render_template('consumables/add.html', 
                                         categories=categories, 
                                         locations=locations,
                                         form_data=data)
            except Exception as e:
                logger.error(f"Fehler beim Verarbeiten benutzerdefinierter Felder: {str(e)}")
                # Benutzerdefinierte Felder sind optional, daher kein Fehler-Return
                data['custom_fields'] = {}
            success, message = ConsumableService.add_consumable(data)
            if success:
                flash(message, 'success')
                return redirect(url_for('consumables.index'))
            else:
                flash(message, 'error')
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Verbrauchsmaterials: {str(e)}", exc_info=True)
            flash('Fehler beim Hinzufügen des Verbrauchsmaterials', 'error')
    
    # GET-Anfrage: Formular anzeigen
    categories = get_categories_scoped()
    locations = get_locations_scoped()
    return render_template('consumables/add.html', 
                       categories=categories, 
                       locations=locations)

@bp.route('/<string:barcode>', methods=['GET', 'POST'])
@login_required
@permission_required('consumables', 'edit')
def detail(barcode):
    """Zeigt die Details eines Verbrauchsmaterials und verarbeitet Updates"""
    if request.method == 'POST':
        try:
            # Form-Daten in Dictionary konvertieren für bessere Handhabung
            data = dict(request.form)
            
            # Benutzerdefinierte Felder verarbeiten
            try:
                from app.services.custom_fields_service import CustomFieldsService
                success_custom, error_msg, custom_values = CustomFieldsService.process_custom_fields_from_form('consumables', request.form)
                if success_custom:
                    data['custom_fields'] = custom_values
                else:
                    return jsonify({'success': False, 'message': f'Fehler bei benutzerdefinierten Feldern: {error_msg}'}), 400
            except Exception as e:
                logger.error(f"Fehler beim Verarbeiten benutzerdefinierter Felder: {str(e)}")
                # Benutzerdefinierte Felder sind optional, daher kein Fehler-Return
                data['custom_fields'] = {}
            
            success, message, new_barcode = ConsumableService.update_consumable(barcode, data)
            if success:
                return jsonify({'success': True, 'redirect': url_for('consumables.detail', barcode=new_barcode)})
            else:
                return jsonify({'success': False, 'message': message}), 400
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Verbrauchsmaterials: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET-Methode: Details anzeigen
    consumable = ConsumableService.get_consumable_detail(barcode)
    if not consumable:
        flash('Verbrauchsmaterial nicht gefunden', 'error')
        return redirect(url_for('consumables.index'))
    
    categories = get_categories_scoped()
    locations = get_locations_scoped()
    usages = ConsumableService.get_consumable_usages(barcode)
    
    # Erstelle Verlaufsliste
    history = []
    for usage in usages:
        worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})
        worker_name = f"{worker['firstname']} {worker['lastname']}" if worker else "Admin"
        
        action = "Entnommen" if usage['quantity'] < 0 else "Hinzugefügt"
        quantity = abs(usage['quantity'])
        
        action_date = usage['used_at']
        if isinstance(action_date, str):
            try:
                action_date = datetime.strptime(action_date, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                action_date = datetime.now()
        
        history.append({
            'action': action,
            'quantity': quantity,
            'worker_name': worker_name,
            'date': action_date
        })
    
    return render_template('consumables/details.html',
                         consumable=consumable,
                       history=history,
                         categories=categories,
                       locations=locations)

@bp.route('/<barcode>/adjust-stock', methods=['POST'])
@login_required
@permission_required('consumables', 'edit')
def adjust_stock(barcode):
    """Passt den Bestand eines Verbrauchsmaterials an"""
    try:
        data = request.get_json()
        quantity = int(data.get('quantity', 0))
        reason = data.get('reason', '')
        
        success, message = ConsumableService.adjust_stock(barcode, quantity, reason)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        logger.error(f"Fehler beim Anpassen des Bestands: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<barcode>/delete', methods=['DELETE'])
@login_required
@permission_required('consumables', 'delete')
def delete(barcode):
    """Löscht ein Verbrauchsmaterial"""
    try:
        success, message = ConsumableService.delete_consumable(barcode)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Verbrauchsmaterials: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<barcode>/forecast')
@login_required
@permission_required('consumables', 'view')
def forecast(barcode):
    """Zeigt eine Vorhersage für ein Verbrauchsmaterial an"""
    try:
        forecast_data = ConsumableService.get_consumable_forecast(barcode)
        if forecast_data:
            return jsonify({'success': True, 'forecast': forecast_data})
        else:
            return jsonify({'success': False, 'message': 'Keine ausreichenden Daten für Vorhersage'}), 400
    except Exception as e:
        logger.error(f"Fehler bei der Vorhersage: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/export')
@login_required
@permission_required('consumables', 'export')
def export():
    """Exportiert alle Verbrauchsmaterialien als CSV"""
    try:
        csv_data = ConsumableService.export_consumables()
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=verbrauchsmaterialien.csv'}
        )
    except Exception as e:
        logger.error(f"Fehler beim Export: {str(e)}", exc_info=True)
        flash('Fehler beim Export', 'error')
        return redirect(url_for('consumables.index'))

@bp.route('/search')
@login_required
def search():
    """Sucht nach Verbrauchsmaterialien"""
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('consumables.index'))
    
    try:
        consumables = ConsumableService.search_consumables(query)
        return render_template('consumables/index.html', 
                           consumables=consumables, 
                           search_query=query)
    except Exception as e:
        logger.error(f"Fehler bei der Suche: {str(e)}", exc_info=True)
        flash('Fehler bei der Suche', 'error')
        return redirect(url_for('consumables.index'))

@bp.route('/bulk-actions', methods=['POST'])
@login_required
def bulk_actions():
    """Führt Massenaktionen auf Verbrauchsmaterialien aus"""
    try:
        data = request.get_json()
        action = data.get('action')
        barcodes = data.get('barcodes', [])
        
        if not barcodes:
            return jsonify({'success': False, 'message': 'Keine Verbrauchsmaterialien ausgewählt'}), 400
        
        success, message = ConsumableService.bulk_action(action, barcodes)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        logger.error(f"Fehler bei Massenaktion: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/statistics')
@login_required
def statistics():
    """Zeigt Statistiken für Verbrauchsmaterialien an"""
    try:
        stats = ConsumableService.get_statistics()
        # Verwende das index Template mit Statistiken
        return render_template('consumables/index.html', stats=stats)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Statistiken: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Statistiken', 'error')
        return redirect(url_for('consumables.index'))

@bp.route('/low-stock')
@login_required
def low_stock():
    """Zeigt Verbrauchsmaterialien mit niedrigem Bestand an"""
    try:
        low_stock_items = ConsumableService.get_low_stock_items()
        # Verwende das index Template mit Niedrigbestand-Filter
        return render_template('consumables/index.html', consumables=low_stock_items, show_low_stock=True)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Niedrigbestand-Liste: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Niedrigbestand-Liste', 'error')
        return redirect(url_for('consumables.index'))

@bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_consumables():
    """Importiert Verbrauchsmaterialien aus einer CSV-Datei"""
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                flash('Keine Datei ausgewählt', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('Keine Datei ausgewählt', 'error')
                return redirect(request.url)
            
            if file and file.filename.endswith('.csv'):
                success, message = ConsumableService.import_consumables(file)
                if success:
                    flash(message, 'success')
                else:
                    flash(message, 'error')
            else:
                flash('Nur CSV-Dateien sind erlaubt', 'error')
            
            return redirect(url_for('consumables.index'))
        except Exception as e:
            logger.error(f"Fehler beim Import: {str(e)}", exc_info=True)
            flash('Fehler beim Import', 'error')
            return redirect(url_for('consumables.index'))
    
    # Verwende das add Template für Import-Funktionalität
    return render_template('consumables/add.html', show_import=True)

@bp.route('/scan/<barcode>')
@login_required
def barcode_scan(barcode):
    """Verarbeitet einen Barcode-Scan für Verbrauchsmaterialien"""
    try:
        result = ConsumableService.process_barcode_scan(barcode)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"Fehler beim Barcode-Scan: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/quick-scan', methods=['GET', 'POST'])
@login_required
def quick_scan():
    """Schneller Scan für Verbrauchsmaterialien"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            barcode = data.get('barcode')
            action = data.get('action', 'consume')  # 'consume' oder 'add'
            quantity = int(data.get('quantity', 1))
            
            result = ConsumableService.quick_scan_action(barcode, action, quantity)
            return jsonify(result)
        except Exception as e:
            logger.error(f"Fehler beim Quick-Scan: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # Verwende das index Template für Quick-Scan
    return render_template('consumables/index.html', show_quick_scan=True)

@bp.route('/restock-alert/<barcode>', methods=['POST'])
@login_required
def restock_alert(barcode):
    """Sendet eine Nachbestellungs-Benachrichtigung für ein Verbrauchsmaterial"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        success, result = ConsumableService.send_restock_alert(barcode, message)
        if success:
            return jsonify({'success': True, 'message': result})
        else:
            return jsonify({'success': False, 'message': result}), 400
    except Exception as e:
        logger.error(f"Fehler beim Senden der Nachbestellungs-Benachrichtigung: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/usage-history/<barcode>')
@login_required
def usage_history(barcode):
    """Zeigt die Nutzungshistorie eines Verbrauchsmaterials an"""
    try:
        history_data = ConsumableService.get_usage_history(barcode)
        if history_data:
            return jsonify({'success': True, 'history': history_data})
        else:
            return jsonify({'success': False, 'message': 'Keine Historie gefunden'}), 404
    except Exception as e:
        logger.error(f"Fehler beim Laden der Nutzungshistorie: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/categories', methods=['GET', 'POST'])
@login_required
def category_management():
    """Verwaltet Kategorien für Verbrauchsmaterialien"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            action = data.get('action')
            
            if action == 'add':
                name = data.get('name')
                success, message = ConsumableService.add_category(name)
            elif action == 'delete':
                name = data.get('name')
                success, message = ConsumableService.delete_category(name)
            else:
                return jsonify({'success': False, 'message': 'Ungültige Aktion'}), 400
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'message': message}), 400
        except Exception as e:
            logger.error(f"Fehler bei der Kategorieverwaltung: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET-Methode: Kategorien anzeigen
    try:
        categories = ConsumableService.get_categories()
        # Verwende das index Template für Kategorieverwaltung
        return render_template('consumables/index.html', categories=categories, show_categories=True)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Kategorien: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Kategorien', 'error')
        return redirect(url_for('consumables.index'))

@bp.route('/locations', methods=['GET', 'POST'])
@login_required
def location_management():
    """Verwaltet Standorte für Verbrauchsmaterialien"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            action = data.get('action')
            
            if action == 'add':
                name = data.get('name')
                success, message = ConsumableService.add_location(name)
            elif action == 'delete':
                name = data.get('name')
                success, message = ConsumableService.delete_location(name)
            else:
                return jsonify({'success': False, 'message': 'Ungültige Aktion'}), 400
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'message': message}), 400
        except Exception as e:
            logger.error(f"Fehler bei der Standortverwaltung: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET-Methode: Standorte anzeigen
    try:
        locations = ConsumableService.get_locations()
        # Verwende das index Template für Standortverwaltung
        return render_template('consumables/index.html', locations=locations, show_locations=True)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Standorte: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Standorte', 'error')
        return redirect(url_for('consumables.index'))

@bp.route('/report')
@login_required
def report():
    """Generiert einen Bericht über Verbrauchsmaterialien"""
    try:
        report_type = request.args.get('type', 'overview')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        report_data = ConsumableService.generate_report(report_type, date_from, date_to)
        # Verwende das index Template für Berichte
        return render_template('consumables/index.html', 
                           report_data=report_data,
                           report_type=report_type,
                           show_report=True)
    except Exception as e:
        logger.error(f"Fehler beim Generieren des Berichts: {str(e)}", exc_info=True)
        flash('Fehler beim Generieren des Berichts', 'error')
        return redirect(url_for('consumables.index'))

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Verwaltet Einstellungen für Verbrauchsmaterialien"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            success, message = ConsumableService.update_settings(data)
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'message': message}), 400
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Einstellungen: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET-Methode: Einstellungen anzeigen
    try:
        settings_data = ConsumableService.get_settings()
        # Verwende das index Template für Einstellungen
        return render_template('consumables/index.html', settings=settings_data, show_settings=True)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Einstellungen: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Einstellungen', 'error')
        return redirect(url_for('consumables.index'))
