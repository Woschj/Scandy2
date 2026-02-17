from .blueprint import bp
from .shared import *
from app.services.plugin_installer_service import PluginInstallerService
from werkzeug.utils import secure_filename
import tempfile

plugin_installer = PluginInstallerService()

@bp.route('/plugins')
@admin_required
def list_plugins():
    """Lists all installed plugins"""
    plugins = plugin_installer.list_plugins()
    return render_template('admin/plugins.html', plugins=plugins)

@bp.route('/plugins/upload', methods=['POST'])
@admin_required
def upload_plugin():
    """Handles plugin ZIP upload and installation"""
    if 'plugin_file' not in request.files:
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('admin.list_plugins'))

    file = request.files['plugin_file']
    if file.filename == '':
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('admin.list_plugins'))

    if not file.filename.endswith('.zip'):
        flash('Nur ZIP-Dateien sind erlaubt', 'error')
        return redirect(url_for('admin.list_plugins'))

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        success, message = plugin_installer.install_plugin(tmp_path)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return redirect(url_for('admin.list_plugins'))

@bp.route('/plugins/delete/<plugin_name>', methods=['POST'])
@admin_required
def delete_plugin(plugin_name):
    """Uninstalls a plugin"""
    success, message = plugin_installer.uninstall_plugin(plugin_name)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('admin.list_plugins'))
