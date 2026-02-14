from .blueprint import bp
from .shared import *
@bp.route('/custom_fields', methods=['GET', 'POST'])
@admin_required
def custom_fields():
    """
    Zentrale Feld-Verwaltung für Standard- und benutzerdefinierte Felder

    GET: Zeigt die Feldverwaltung-Seite mit Standard-Feldern und benutzerdefinierten Feldern
    POST: Verarbeitet Updates für Standard-Felder (action=update_default_fields)

    Integriert:
    - Standard-Werkzeugfelder (Seriennummer, MAC-Adressen, etc.)
    - Benutzerdefinierte Felder für Werkzeuge und Verbrauchsgüter
    """
    try:
        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'update_default_fields':
                # Standard-Felder aktualisieren
                field_mappings = {
                    'tool_field_serial_number': 'tool_field_serial_number',
                    'tool_field_invoice_number': 'tool_field_invoice_number',
                    'tool_field_mac_address': 'tool_field_mac_address',
                    'tool_field_mac_address_wlan': 'tool_field_mac_address_wlan',
                    'tool_field_user_groups': 'tool_field_user_groups',
                    'tool_field_software': 'tool_field_software'
                }

                for form_field, setting_key in field_mappings.items():
                    set_feature_setting(setting_key, form_field in request.form)

                flash('Standard-Felder erfolgreich aktualisiert', 'success')
                return redirect(url_for('admin.custom_fields'))

        # Alle benutzerdefinierten Felder laden
        custom_fields = CustomFieldsService.get_all_custom_fields()

        # Feature-Einstellungen laden
        feature_settings = get_feature_settings()

        return render_template('admin/custom_fields.html',
                             custom_fields=custom_fields,
                             field_types=CustomFieldsService.FIELD_TYPES,
                             target_types=CustomFieldsService.TARGET_TYPES,
                             feature_settings=feature_settings)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Feld-Verwaltung: {str(e)}")
        flash('Fehler beim Laden der Feld-Verwaltung', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/custom_fields/add', methods=['POST'])
@admin_required
def add_custom_field():
    """Neues benutzerdefiniertes Feld hinzufügen"""
    try:

        # Daten aus dem Formular extrahieren
        field_data = {
            'name': request.form.get('name', ''),
            'field_type': request.form.get('field_type', ''),
            'target_type': request.form.get('target_type', ''),
            'description': request.form.get('description', ''),
            'required': request.form.get('required') == 'on',
            'default_value': request.form.get('default_value', ''),
            'sort_order': int(request.form.get('sort_order', 999)),
            'select_options': request.form.get('select_options', '')
        }

        success, message = CustomFieldsService.create_custom_field(field_data)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('admin.custom_fields'))

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des benutzerdefinierten Feldes: {str(e)}")
        flash('Fehler beim Erstellen des Feldes', 'error')
        return redirect(url_for('admin.custom_fields'))

@bp.route('/custom_fields/<field_id>/edit', methods=['POST'])
@admin_required
def edit_custom_field(field_id):
    """Benutzerdefiniertes Feld bearbeiten"""
    try:
        # Daten aus dem Formular extrahieren
        field_data = {
            'name': request.form.get('name', ''),
            'field_type': request.form.get('field_type', ''),
            'target_type': request.form.get('target_type', ''),
            'description': request.form.get('description', ''),
            'required': request.form.get('required') == 'on',
            'default_value': request.form.get('default_value', ''),
            'sort_order': int(request.form.get('sort_order', 999)),
            'select_options': request.form.get('select_options', '')
        }

        success, message = CustomFieldsService.update_custom_field(field_id, field_data)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('admin.custom_fields'))

    except Exception as e:
        logger.error(f"Fehler beim Bearbeiten des benutzerdefinierten Feldes: {str(e)}")
        flash('Fehler beim Bearbeiten des Feldes', 'error')
        return redirect(url_for('admin.custom_fields'))

@bp.route('/custom_fields/<field_id>/delete', methods=['POST'])
@admin_required
def delete_custom_field(field_id):
    """Benutzerdefiniertes Feld löschen"""
    try:
        success, message = CustomFieldsService.delete_custom_field(field_id)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('admin.custom_fields'))

    except Exception as e:
        logger.error(f"Fehler beim Löschen des benutzerdefinierten Feldes: {str(e)}")
        flash('Fehler beim Löschen des Feldes', 'error')
        return redirect(url_for('admin.custom_fields'))
