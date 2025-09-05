from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required

from app.utils.decorators import admin_required
from app.services.admin_email_templates_service import AdminEmailTemplatesService

bp = Blueprint('admin_email_templates', __name__, url_prefix='/admin/email-templates')


@bp.route('/')
@login_required
@admin_required
def index():
    # Übersicht entfernt – leite zur Admin-Dashboard-Seite um
    return redirect(url_for('admin_core.dashboard'))


# 'create' Route entfernt – Vorlagen werden systemseitig bereitgestellt


@bp.route('/<template_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(template_id: str):
    template = AdminEmailTemplatesService.get_template(template_id)
    if not template:
        flash('Vorlage nicht gefunden.', 'error')
        return redirect(url_for('admin_email_templates.index'))
    if request.method == 'POST':
        success, message = AdminEmailTemplatesService.update_template(template_id, {
            'name': request.form.get('name', ''),
            'key': request.form.get('key', ''),
            'subject': request.form.get('subject', ''),
            'html_content': request.form.get('html_content', ''),
            'text_content': request.form.get('text_content', ''),
        })
        if success:
            flash(message, 'success')
            return redirect(url_for('admin_email_templates.index'))
        flash(message, 'error')
    return render_template('admin/email_templates/form.html', template=template)


@bp.route('/<template_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(template_id: str):
    success, message = AdminEmailTemplatesService.delete_template(template_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('admin_email_templates.index'))


@bp.route('/<template_id>/send-test', methods=['POST'])
@login_required
@admin_required
def send_test(template_id: str):
    """Sendet eine Test-E-Mail für eine E-Mail-Vorlage"""
    try:
        recipient = request.form.get('recipient', '').strip()
        
        if not recipient:
            return jsonify({'success': False, 'message': 'Empfänger-E-Mail fehlt'})
        
        # Template-ID bereinigen
        template_id = template_id.strip()
        
        # Prüfe ob Template existiert
        template = AdminEmailTemplatesService.get_template(template_id)
        if not template:
            return jsonify({'success': False, 'message': 'E-Mail-Vorlage nicht gefunden'})
        
        # Sende Test-E-Mail
        success, message = AdminEmailTemplatesService.send_test_email(template_id, recipient)
        
        # Gib immer JSON-Antwort zurück
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})
        
    except Exception as e:
        error_message = f"Fehler beim Senden der Test-E-Mail: {str(e)}"
        return jsonify({'success': False, 'message': error_message})


@bp.route('/ensure-defaults', methods=['POST'])
@login_required
@admin_required
def ensure_defaults():
    res = AdminEmailTemplatesService.ensure_default_templates()
    flash(f"Standardvorlagen: {res['created']} erstellt, {res['skipped']} vorhanden.", 'success')
    next_url = request.form.get('next') or request.args.get('next')
    if next_url:
        return redirect(next_url)
    return redirect(url_for('admin_email_templates.index'))


@bp.route('/mappings', methods=['POST'])
@login_required
@admin_required
def save_mappings():
    # erwartete Actions
    actions = ['auftrag_confirmation', 'password_reset', 'user_welcome']
    mapping = {}
    for a in actions:
        mapping[a] = request.form.get(f'action_{a}', a)
    ok, msg = AdminEmailTemplatesService.save_template_mappings(mapping)
    flash(msg, 'success' if ok else 'error')
    next_url = request.form.get('next') or request.args.get('next')
    if next_url:
        return redirect(next_url)
    return redirect(url_for('admin_email_templates.index'))


