"""
Versionschecker für Scandy
Prüft ob die lokale Installation mit der aktuellen GitHub-Version übereinstimmt
"""

import requests
import re
import logging
from pathlib import Path
from app.config.version import VERSION

logger = logging.getLogger(__name__)

class VersionChecker:
    """Versionschecker für Scandy"""
    
    def __init__(self):
        self.github_api_url = "https://api.github.com/repos/woschj/Scandy2/releases/latest"
        self.github_raw_url = "https://raw.githubusercontent.com/woschj/Scandy2/main/app/config/version.py"
        self.local_version = VERSION
        
    def get_github_version(self):
        """Holt die neueste Version von GitHub"""
        try:
            # Versuche zuerst die GitHub API (für Release-Tags)
            response = requests.get(self.github_api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                tag_name = data.get('tag_name', '')
                if tag_name:
                    # Entferne 'v' Prefix falls vorhanden
                    return tag_name.lstrip('v')
            
            # Fallback: Direkt aus der version.py Datei lesen
            response = requests.get(self.github_raw_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                # Suche nach VERSION = "..." Pattern
                match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
                    
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der GitHub-Version: [Interner Fehler]")
            
        return None
    
    def get_local_version(self):
        """Gibt die lokale Version zurück"""
        return self.local_version
    
    def is_up_to_date(self):
        """Prüft ob die lokale Version aktuell ist"""
        github_version = self.get_github_version()
        if not github_version:
            return None  # Unbekannt
        
        return self.local_version == github_version
    
    def get_version_info(self):
        """Gibt detaillierte Versionsinformationen zurück"""
        github_version = self.get_github_version()
        
        info = {
            'local_version': self.local_version,
            'github_version': github_version,
            'is_up_to_date': None,
            'update_available': False,
            'error': None
        }
        
        if github_version:
            info['is_up_to_date'] = self.local_version == github_version
            info['update_available'] = self.local_version != github_version
        else:
            info['error'] = "GitHub-Version konnte nicht abgerufen werden"
            
        return info
    
    def get_update_url(self):
        """Gibt die URL für das Update zurück"""
        return "https://github.com/woschj/Scandy2/releases/latest"
    
    def check_for_updates(self):
        """Prüft auf Updates und gibt Status zurück"""
        try:
            info = self.get_version_info()
            
            if info['error']:
                return {
                    'status': 'error',
                    'message': info['error'],
                    'local_version': info['local_version']
                }
            
            if info['is_up_to_date']:
                return {
                    'status': 'up_to_date',
                    'message': 'Installation ist aktuell',
                    'local_version': info['local_version'],
                    'github_version': info['github_version']
                }
            else:
                return {
                    'status': 'update_available',
                    'message': 'Update verfügbar',
                    'local_version': info['local_version'],
                    'github_version': info['github_version'],
                    'update_url': self.get_update_url()
                }
                
        except Exception as e:
            logger.error(f"Fehler beim Versionscheck: [Interner Fehler]")
            return {
                'status': 'error',
                'message': 'Fehler beim Versionscheck.',
                'local_version': info['local_version']
            }

# Globale Instanz
version_checker = VersionChecker()

def check_version():
    """Einfache Funktion für Versionscheck"""
    return version_checker.check_for_updates()

def get_version_info():
    """Gibt Versionsinformationen zurück"""
    return version_checker.get_version_info() 