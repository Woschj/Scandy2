"""
E-Mail-Debug-Funktionen für Scandy
Hilft bei der Diagnose von E-Mail-Problemen
"""
import logging
from app.utils.email_utils import get_email_config

logger = logging.getLogger(__name__)

def debug_email_status():
    """Debug-Funktion um den E-Mail-Status zu prüfen"""
    try:
        config = get_email_config()
        if not config:
            return {
                'status': 'error',
                'message': 'Keine E-Mail-Konfiguration gefunden',
                'details': 'Bitte konfigurieren Sie das E-Mail-System im Admin-Bereich'
            }
        
        # Prüfe ob alle erforderlichen Felder vorhanden sind
        required_fields = ['mail_server', 'mail_port', 'mail_username', 'mail_password']
        missing_fields = [field for field in required_fields if not config.get(field)]
        
        if missing_fields:
            return {
                'status': 'error',
                'message': f'Unvollständige E-Mail-Konfiguration',
                'details': f'Fehlende Felder: {", ".join(missing_fields)}',
                'config': {k: v if k != 'mail_password' else '***' for k, v in config.items()}
            }
        
        return {
            'status': 'ok',
            'message': 'E-Mail-Konfiguration vollständig',
            'details': f'SMTP: {config["mail_server"]}:{config["mail_port"]}, TLS: {config["mail_use_tls"]}',
            'config': {k: v if k != 'mail_password' else '***' for k, v in config.items()}
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Fehler beim Prüfen des E-Mail-Status: [Interner Fehler]',
            'details': 'Überprüfen Sie die Logs für weitere Details'
        }

def test_simple_email():
    """Sendet eine einfache Test-E-Mail"""
    try:
        from app.utils.email_utils import send_password_reset_mail
        
        # Test-E-Mail senden
        test_email = "test@example.com"
        test_password = "test123"
        
        result = send_password_reset_mail(test_email, password=test_password)
        
        if result:
            return {
                'status': 'success',
                'message': 'Test-E-Mail erfolgreich gesendet',
                'details': f'An {test_email} gesendet'
            }
        else:
            return {
                'status': 'error',
                'message': 'Test-E-Mail konnte nicht gesendet werden',
                'details': 'Überprüfen Sie die E-Mail-Konfiguration'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Fehler beim Testen der E-Mail: [Interner Fehler]',
            'details': 'Überprüfen Sie die Logs für weitere Details'
        }
