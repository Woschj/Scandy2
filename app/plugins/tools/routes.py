from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_login import current_user
from app.services.tool_service import ToolService
from app.utils.decorators import admin_required, login_required, mitarbeiter_required, not_teilnehmer_required
from app.utils.permissions import permission_required
from app.utils.database_helpers import get_categories_scoped, get_locations_scoped, get_categories_from_settings, get_locations_from_settings
from datetime import datetime
import logging
from app.models.mongodb_database import mongodb, is_feature_enabled

# Blueprint mit URL-Präfix definieren
bp = Blueprint('tools', __name__)
logger = logging.getLogger(__name__) # Logger für dieses Modul

def get_feature_settings_safe():
    """Lädt Feature-Einstellungen sicher mit Fallback"""
    try:
        from app.models.mongodb_database import get_feature_settings
        return get_feature_settings()
    except Exception as e:
        logger.warning(f"Fehler beim Laden der Feature-Einstellungen: {str(e)}")
        # Fallback zu Standard-Einstellungen
        return {
            'tool_field_serial_number': True,
            'tool_field_invoice_number': True,
            'tool_field_mac_address': True,
            'tool_field_mac_address_wlan': True,
            'tool_field_user_groups': True,
            'tool_field_software': True
        }

# ToolService wird bei Bedarf initialisiert
tool_service = None

def get_tool_service():
    """Lazy initialization des ToolService"""
    global tool_service
    if tool_service is None:
        tool_service = ToolService()
    return tool_service

def get_software_presets():
    """Holt die Software-Pakete aus der Datenbank"""
    from app.models.mongodb_database import mongodb
    try:
        software_list = list(mongodb.find('software', {}, sort=[('name', 1)]))
        return software_list
    except Exception as e:
        logger.warning(f"Fehler beim Laden der Software-Presets: {e}")
        return []

def get_user_groups():
    """Holt die Nutzergruppen aus der Datenbank"""
    from app.models.mongodb_database import mongodb
    try:
        groups_list = list(mongodb.find('user_groups', {}, sort=[('name', 1)]))
        return groups_list
    except Exception as e:
        logger.warning(f"Fehler beim Laden der Nutzergruppen: {e}")
        return []

@bp.route('/')
@login_required
@permission_required('tools', 'view')
def index():
    """Werkzeuge-Übersicht"""
    # Prüfe ob Werkzeuge-Feature aktiviert ist
    if not is_feature_enabled('tools'):
        flash('Werkzeuge-Verwaltung ist deaktiviert', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Hole alle Werkzeuge über den ToolService (filtert automatisch gelöschte und per Abteilung)
        tool_service = get_tool_service()
        tools = tool_service.get_all_tools()
        
        # Hole Kategorien und Standorte strikt abteilungsgetrennt
        categories = get_categories_scoped()
        locations = get_locations_scoped()
        
        # Hole Software und Nutzergruppen für Software-Management Feature
        software_presets = get_software_presets()
        user_groups = get_user_groups()
        feature_settings = get_feature_settings_safe()
        
        return render_template('tools/index.html',
                             tools=tools,
                             categories=categories,
                             locations=locations,
                             software_presets=software_presets,
                             user_groups=user_groups,
                             feature_settings=feature_settings)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeuge: {str(e)}")
        flash('Fehler beim Laden der Werkzeuge', 'error')
        return redirect(url_for('main.index'))

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('tools', 'create')
@not_teilnehmer_required
def add():
    """Neues Werkzeug hinzufügen"""
    # Prüfe ob Werkzeuge-Feature aktiviert ist
    if not is_feature_enabled('tools'):
        flash('Werkzeuge-Verwaltung ist deaktiviert', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            # Formulardaten sammeln
            tool_data = {
                'name': request.form.get('name', '').strip(),
                'barcode': request.form.get('barcode', '').strip(),
                'category': request.form.get('category', '').strip(),
                'location': request.form.get('location', '').strip(),
                'description': request.form.get('description', '').strip(),
                'status': request.form.get('status', 'verfügbar'),
                'serial_number': request.form.get('serial_number', ''),
                'invoice_number': request.form.get('invoice_number', ''),
                'mac_address': request.form.get('mac_address', ''),
                'mac_address_wlan': request.form.get('mac_address_wlan', '')
            }
            
            # Software-Management Daten nur hinzufügen, wenn Feature aktiviert ist
            feature_settings = get_feature_settings_safe()
            if feature_settings.get('software_management', False):
                user_groups_data = request.form.getlist('user_groups')
                additional_software_data = request.form.getlist('additional_software')
                tool_data['user_groups'] = user_groups_data
                tool_data['additional_software'] = additional_software_data
                print(f"DEBUG: Software-Management aktiviert")
                print(f"DEBUG: user_groups = {user_groups_data}")
                print(f"DEBUG: additional_software = {additional_software_data}")
            else:
                print(f"DEBUG: Software-Management deaktiviert")
                tool_data['user_groups'] = []
                tool_data['additional_software'] = []
            
            # Benutzerdefinierte Felder verarbeiten
            try:
                from app.services.custom_fields_service import CustomFieldsService
                success_custom, error_msg, custom_values = CustomFieldsService.process_custom_fields_from_form('tools', request.form)
                if success_custom:
                    tool_data['custom_fields'] = custom_values
                else:
                    flash(f'Fehler bei benutzerdefinierten Feldern: {error_msg}', 'error')
                    return render_template('tools/add.html', 
                                         form_data=tool_data,
                                         categories=get_categories_scoped(),
                                         locations=get_locations_scoped(),
                                         software_presets=get_software_presets(),
                                         user_groups=get_user_groups(),
                                         feature_settings=get_feature_settings_safe())
            except Exception as e:
                logger.error(f"Fehler beim Verarbeiten benutzerdefinierter Felder: {str(e)}")
                # Benutzerdefinierte Felder sind optional, daher kein Fehler-Return
                tool_data['custom_fields'] = {}
            
            # Validierung
            if not tool_data['name'] or not tool_data['barcode']:
                flash('Name und Barcode sind erforderlich', 'error')
                return render_template('tools/add.html', 
                                     form_data=tool_data,
                                     categories=get_categories_scoped(),
                                     locations=get_locations_scoped(),
                                     software_presets=get_software_presets(),
                                     user_groups=get_user_groups(),
                                     feature_settings=get_feature_settings_safe())
            
            # Werkzeug erstellen
            tool_service = get_tool_service()
            success, message, barcode = tool_service.create_tool(tool_data)
            
            if success:
                flash(message, 'success')
                return redirect(url_for('tools.index'))
            else:
                flash(message, 'error')
                return render_template('tools/add.html', 
                                     form_data=tool_data,
                                     categories=get_categories_scoped(),
                                     locations=get_locations_scoped(),
                                     software_presets=get_software_presets(),
                                     user_groups=get_user_groups(),
                                     feature_settings=get_feature_settings_safe())
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Werkzeugs: {str(e)}")
            flash('Fehler beim Erstellen des Werkzeugs', 'error')
            return render_template('tools/add.html', 
                                 form_data=tool_data,
                                 categories=get_categories_scoped(),
                                 locations=get_locations_scoped(),
                                 software_presets=get_software_presets(),
                                 user_groups=get_user_groups(),
                                 feature_settings=get_feature_settings_safe())
    
    # GET Request - Formular anzeigen
    try:
        categories = get_categories_scoped()
        locations = get_locations_scoped()
        software_presets = get_software_presets()
        user_groups = get_user_groups()
        
        return render_template('tools/add.html',
                             categories=categories,
                             locations=locations,
                             software_presets=software_presets,
                             user_groups=user_groups,
                             feature_settings=get_feature_settings_safe())
    except Exception as e:
        logger.error(f"Fehler beim Laden des Formulars: {str(e)}")
        flash('Fehler beim Laden des Formulars', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/<barcode>')
@login_required
@permission_required('tools', 'view')
def detail(barcode):
    """Zeigt die Details eines Werkzeugs"""
    try:
        # Hole detaillierte Werkzeug-Informationen über den Service
        tool_service = get_tool_service()
        tool = tool_service.get_tool_details(barcode)
        
        if not tool:
            flash('Werkzeug nicht gefunden', 'error')
            return redirect(url_for('tools.index'))
        
        # Hole Kategorien und Standorte
        categories = get_categories_scoped()
        locations = get_locations_scoped()
        software_presets = get_software_presets()
        user_groups = get_user_groups()
        
        # Feature-Einstellungen laden
        feature_settings = get_feature_settings_safe()
        
        return render_template('tools/detail.html',
                             tool=tool,
                             categories=categories,
                             locations=locations,
                             software_presets=software_presets,
                             user_groups=user_groups,
                             lending_history=tool.get('lending_history', []),
                             feature_settings=feature_settings,
                             now=datetime.now)
                             
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeug-Details: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Werkzeug-Details', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/<barcode>/edit', methods=['POST'])
@login_required
@permission_required('tools', 'edit')
def edit(barcode):
    """Bearbeitet ein Werkzeug über Modal"""
    try:
        # Formulardaten sammeln
        tool_data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'category': request.form.get('category'),
            'location': request.form.get('location'),
            'serial_number': request.form.get('serial_number', ''),
            'invoice_number': request.form.get('invoice_number', ''),
            'mac_address': request.form.get('mac_address', ''),
            'mac_address_wlan': request.form.get('mac_address_wlan', '')
        }
        
        # Software-Management Daten nur hinzufügen, wenn Feature aktiviert ist
        feature_settings = get_feature_settings_safe()
        if feature_settings.get('software_management', False):
            user_groups_data = request.form.getlist('user_groups')
            additional_software_data = request.form.getlist('additional_software')
            tool_data['user_groups'] = user_groups_data
            tool_data['additional_software'] = additional_software_data
            print(f"DEBUG EDIT: Software-Management aktiviert")
            print(f"DEBUG EDIT: user_groups = {user_groups_data}")
            print(f"DEBUG EDIT: additional_software = {additional_software_data}")
        else:
            print(f"DEBUG EDIT: Software-Management deaktiviert")
            tool_data['user_groups'] = []
            tool_data['additional_software'] = []
        
        # Benutzerdefinierte Felder verarbeiten
        try:
            from app.services.custom_fields_service import CustomFieldsService
            success_custom, error_msg, custom_values = CustomFieldsService.process_custom_fields_from_form('tools', request.form)
            if success_custom:
                tool_data['custom_fields'] = custom_values
            else:
                return jsonify({'success': False, 'message': f'Fehler bei benutzerdefinierten Feldern: {error_msg}'})
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten benutzerdefinierter Felder: {str(e)}")
            # Benutzerdefinierte Felder sind optional, daher kein Fehler-Return
            tool_data['custom_fields'] = {}
        
        # Status nur hinzufügen, wenn er explizit im Formular angegeben wurde
        form_status = request.form.get('status')
        if form_status and form_status.strip():
            tool_data['status'] = form_status
        
        # Barcode nur hinzufügen, wenn er explizit im Formular angegeben wurde
        form_barcode = request.form.get('barcode')
        if form_barcode and form_barcode.strip():
            tool_data['barcode'] = form_barcode
        
        # Werkzeug über Service aktualisieren
        tool_service = get_tool_service()
        success, message, new_barcode = tool_service.update_tool(barcode, tool_data)
        
        # Verwende den neuen Barcode oder den alten, falls new_barcode None ist
        redirect_barcode = new_barcode if new_barcode else barcode
        
        return jsonify({
            'success': success, 
            'message': message, 
            'redirect': url_for('tools.detail', barcode=redirect_barcode)
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Bearbeiten des Werkzeugs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': 'Fehler beim Bearbeiten des Werkzeugs'
        }), 500

@bp.route('/<string:barcode>/status', methods=['POST'])
@login_required
@permission_required('tools', 'edit')
def change_status(barcode):
    """Ändert den Status eines Werkzeugs"""
    try:
        new_status = request.form.get('status')
        
        # Status über Service ändern
        tool_service = get_tool_service()
        success, message = tool_service.change_tool_status(barcode, new_status)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        logger.error(f"Fehler beim Ändern des Status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler beim Ändern des Status'}), 500

@bp.route('/<string:barcode>/delete', methods=['POST'])
@login_required
@permission_required('tools', 'delete')
@admin_required
def delete(barcode):
    """Löscht ein Werkzeug"""
    try:
        permanent = request.form.get('permanent', 'false').lower() == 'true'
        
        # Werkzeug über Service löschen
        tool_service = get_tool_service()
        success, message = tool_service.delete_tool(barcode, permanent)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
            
        return redirect(url_for('tools.index'))
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Werkzeugs: {str(e)}", exc_info=True)
        flash('Fehler beim Löschen des Werkzeugs', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/search')
@login_required
def search():
    """Sucht nach Werkzeugen"""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return redirect(url_for('tools.index'))
        
        # Suche über Service
        tool_service = get_tool_service()
        tools = tool_service.search_tools(query)
        
        # Hole Kategorien und Standorte
        categories = get_categories_scoped()
        locations = get_locations_scoped()
        
        return render_template('tools/index.html',
                           tools=tools,
                           categories=categories,
                           locations=locations,
                           search_query=query,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler bei der Werkzeug-Suche: {str(e)}", exc_info=True)
        flash('Fehler bei der Suche', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/category/<category>')
@login_required
def by_category(category):
    """Zeigt Werkzeuge nach Kategorie"""
    try:
        # Werkzeuge nach Kategorie über Service
        tool_service = get_tool_service()
        tools = tool_service.get_tools_by_category(category)
        
        # Hole Kategorien und Standorte
        categories = get_categories_scoped()
        locations = get_locations_scoped()
        
        return render_template('tools/index.html',
                           tools=tools,
                           categories=categories,
                           locations=locations,
                           selected_category=category,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeuge nach Kategorie: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Werkzeuge', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/location/<location>')
@login_required
def by_location(location):
    """Zeigt Werkzeuge nach Standort"""
    try:
        # Werkzeuge nach Standort über Service
        tool_service = get_tool_service()
        tools = tool_service.get_tools_by_location(location)
        
        # Hole Kategorien und Standorte
        categories = get_categories_scoped()
        locations = get_locations_scoped()
        
        return render_template('tools/index.html',
                           tools=tools,
                           categories=categories,
                           locations=locations,
                           selected_location=location,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeuge nach Standort: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Werkzeuge', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/status/<status>')
@login_required
def by_status(status):
    """Zeigt Werkzeuge nach Status"""
    try:
        # Werkzeuge nach Status über Service
        tool_service = get_tool_service()
        tools = tool_service.get_tools_by_status(status)
        
        # Hole Kategorien und Standorte
        categories = get_categories_scoped()
        locations = get_locations_scoped()
        
        return render_template('tools/index.html',
                           tools=tools,
                           categories=categories,
                           locations=locations,
                           selected_status=status,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeuge nach Status: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Werkzeuge', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/statistics')
@login_required
@permission_required('tools', 'export')
@admin_required
def statistics():
    """Zeigt Werkzeug-Statistiken"""
    try:
        # Statistiken über Service
        tool_service = get_tool_service()
        stats = tool_service.get_tool_statistics()
        
        return render_template('tools/statistics.html',
                           stats=stats,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeug-Statistiken: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Statistiken', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/export')
@login_required
@permission_required('tools', 'export')
@admin_required
def export():
    """Exportiert Werkzeuge als CSV"""
    try:
        from flask import Response
        
        # CSV über Service exportieren
        tool_service = get_tool_service()
        csv_data = tool_service.export_tools()
        
        if not csv_data:
            flash('Fehler beim Export', 'error')
            return redirect(url_for('tools.index'))
        
        # CSV-Datei zum Download anbieten
        response = Response(csv_data, mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=werkzeuge_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Fehler beim Export der Werkzeuge: {str(e)}", exc_info=True)
        flash('Fehler beim Export', 'error')
        return redirect(url_for('tools.index'))