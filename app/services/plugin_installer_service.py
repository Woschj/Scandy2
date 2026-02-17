import os
import zipfile
import shutil
import logging
from datetime import datetime
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)

class PluginInstallerService:
    def __init__(self, plugins_dir=None):
        if plugins_dir:
            self.plugins_dir = Path(plugins_dir).resolve()
        else:
            # Assume we are in app/services/ and want to target app/plugins/
            self.plugins_dir = Path(__file__).resolve().parents[1] / 'plugins'

        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def _is_safe_path(self, path):
        """Checks if the path is within the plugins directory to prevent Zip Slip."""
        return os.path.commonpath([str(self.plugins_dir), os.path.abspath(path)]) == str(self.plugins_dir)

    def install_plugin(self, zip_file_path):
        """Installs a plugin from a ZIP file."""
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Security check for Zip Slip
                for member in zip_ref.namelist():
                    member_path = os.path.abspath(os.path.join(self.plugins_dir, member))
                    if not self._is_safe_path(member_path):
                        return False, f"Sicherheitswarnung: ZIP enthält ungültige Pfade ({member})"

                # Basic validation: check if it has an __init__.py
                top_level_names = {parts[0] for parts in (Path(name).parts for name in zip_ref.namelist())}

                is_flat = False
                if len(top_level_names) != 1:
                    if '__init__.py' in zip_ref.namelist():
                        is_flat = True
                        plugin_name = Path(zip_file_path).stem
                        target_path = self.plugins_dir / plugin_name
                    else:
                        return False, "ZIP must contain a single plugin directory or a flat plugin with __init__.py"
                else:
                    plugin_name = list(top_level_names)[0]
                    target_path = self.plugins_dir / plugin_name

                if target_path.exists():
                    shutil.rmtree(target_path)

                if is_flat:
                    target_path.mkdir(parents=True, exist_ok=True)
                    zip_ref.extractall(target_path)
                else:
                    zip_ref.extractall(self.plugins_dir)

                # Check if the extracted content actually has an __init__.py
                if not (target_path / '__init__.py').exists():
                    shutil.rmtree(target_path)
                    return False, "Extracted plugin is missing __init__.py"

                logger.info(f"Plugin {plugin_name} installed successfully to {target_path}")
                return True, f"Plugin '{plugin_name}' erfolgreich installiert. Bitte starten Sie die Anwendung neu, um es zu aktivieren."
        except Exception as e:
            logger.error(f"Error installing plugin: {e}")
            return False, f"Fehler bei der Plugin-Installation: {str(e)}"

    def list_plugins(self):
        """Lists all installed plugins."""
        plugins = []
        if self.plugins_dir.exists():
            for item in self.plugins_dir.iterdir():
                if item.is_dir() and not item.name.startswith('__'):
                    if (item / '__init__.py').exists():
                        plugins.append({
                            'name': item.name,
                            'path': str(item),
                            'installed_at': datetime.fromtimestamp(item.stat().st_mtime).isoformat() if hasattr(os, 'stat') else 'Unknown'
                        })
        return plugins

    def uninstall_plugin(self, plugin_name):
        """Uninstalls a plugin by removing its directory."""
        try:
            target_path = self.plugins_dir / plugin_name
            if target_path.exists() and target_path.is_dir():
                shutil.rmtree(target_path)
                logger.info(f"Plugin {plugin_name} uninstalled.")
                return True, f"Plugin '{plugin_name}' wurde deinstalliert."
            return False, "Plugin nicht gefunden."
        except Exception as e:
            logger.error(f"Error uninstalling plugin: {e}")
            return False, f"Fehler bei der Deinstallation: {str(e)}"
