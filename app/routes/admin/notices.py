from .blueprint import bp
from .shared import *
@bp.route('/notices')
@admin_required
def notices():
    """Notizen-Übersicht"""
    from flask import g
    current_department = getattr(g, 'current_department', None)
    notices = AdminNotificationService.get_all_notices(current_department)
    # Konvertiere Felder für Template-Kompatibilität
    for n in notices:
        if '_id' in n and 'id' not in n:
            n['id'] = n['_id']
        if 'message' in n and 'content' not in n:
            n['content'] = n['message']
    return render_template('admin/notices.html', notices=notices)

@bp.route('/create_notice', methods=['GET', 'POST'])
@admin_required
def create_notice():
    """Neue Notiz erstellen"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        notice_type = request.form.get('type', 'info')
        from flask import g
        current_department = getattr(g, 'current_department', None)
        priority = request.form.get('priority')
        is_active = True if request.form.get('is_active') in ('on', 'true', '1') else False

        success, message = AdminNotificationService.create_notice(title, content, notice_type, department=current_department, priority=priority, is_active=is_active)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('admin.notices'))

    return render_template('admin/notice_form.html')

@bp.route('/edit_notice/<id>', methods=['GET', 'POST'])
@admin_required
def edit_notice(id):
    """Notiz bearbeiten"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        notice_type = request.form.get('type', 'info')
        from flask import g
        current_department = getattr(g, 'current_department', None)
        priority = request.form.get('priority')
        is_active = True if request.form.get('is_active') in ('on', 'true', '1') else False

        success, message = AdminNotificationService.update_notice(id, title, content, notice_type, department=current_department, priority=priority, is_active=is_active)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('admin.notices'))

    notice = AdminNotificationService.get_notice_by_id(id)
    if notice:
        # Mapping für Template
        notice['id'] = notice.get('_id') or id
        if 'message' in notice:
            notice['content'] = notice['message']
    if not notice:
        flash('Notiz nicht gefunden', 'error')
        return redirect(url_for('admin.notices'))

    return render_template('admin/notice_form.html', notice=notice)

@bp.route('/delete_notice/<id>', methods=['POST'])
@admin_required
def delete_notice(id):
    """Löscht einen Hinweis"""
    try:
        success, message = AdminNotificationService.delete_notice(id)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('admin.notices'))

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Hinweises: {str(e)}")
        flash('Fehler beim Löschen des Hinweises', 'error')
        return redirect(url_for('admin.notices'))
