"""
Zentraler Validation Service für Scandy
Alle Formular-Validierungen an einem Ort
"""
from typing import Dict, List, Tuple, Any
from werkzeug.security import generate_password_hash
import re
import logging

logger = logging.getLogger(__name__)

class ValidationService:
    """Zentraler Service für alle Validierungen"""
    
    # Konfiguration
    MIN_PASSWORD_LENGTH = 8
    MAX_USERNAME_LENGTH = 50
    MIN_USERNAME_LENGTH = 3
    MAX_BARCODE_LENGTH = 50
    
    @staticmethod
    def validate_user_form(data: Dict[str, Any], is_edit: bool = False) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validiert Nutzende-Formulardaten
        
        Args:
            data: Formulardaten
            is_edit: True wenn es sich um eine Bearbeitung handelt
            
        Returns:
            (is_valid, errors, processed_data)
        """
        errors = []
        processed_data = {}
        
        # Basis-Felder validieren
        username = data.get('username', '').strip()
        firstname = data.get('firstname', '').strip()
        lastname = data.get('lastname', '').strip()
        role = data.get('role', '').strip()
        email = data.get('email', '').strip()
        
        # Pflichtfelder (nur Nutzendename und Rolle)
        if not username:
            errors.append('Nutzendename ist erforderlich')
        elif len(username) < ValidationService.MIN_USERNAME_LENGTH:
            errors.append(f'Nutzendename muss mindestens {ValidationService.MIN_USERNAME_LENGTH} Zeichen lang sein')
        elif len(username) > ValidationService.MAX_USERNAME_LENGTH:
            errors.append(f'Nutzendename darf maximal {ValidationService.MAX_USERNAME_LENGTH} Zeichen lang sein')
        
        if not role:
            errors.append('Rolle ist erforderlich')
        
        # Optionale Felder (Vorname und Nachname sind optional)
        if firstname and len(firstname) > 50:
            errors.append('Vorname darf maximal 50 Zeichen lang sein')
        
        if lastname and len(lastname) > 50:
            errors.append('Nachname darf maximal 50 Zeichen lang sein')
        
        # E-Mail-Validierung (optional)
        if email and not ValidationService._is_valid_email(email):
            errors.append('Ungültige E-Mail-Adresse')
        
        # Passwort-Validierung (nur wenn Passwort eingegeben wurde)
        password = data.get('password', '').strip()
        password_confirm = data.get('password_confirm', '').strip()
        
        # Nur validieren wenn Passwort eingegeben wurde
        if password:
            if password != password_confirm:
                errors.append('Passwörter stimmen nicht überein')
            elif len(password) < ValidationService.MIN_PASSWORD_LENGTH:
                errors.append(f'Passwort muss mindestens {ValidationService.MIN_PASSWORD_LENGTH} Zeichen lang sein')
        
        # Verarbeitete Daten zurückgeben
        processed_data = {
            'username': username,
            'firstname': firstname,
            'lastname': lastname,
            'role': role,
            'email': email,
            'password': password,
            'timesheet_enabled': data.get('timesheet_enabled') == 'on'
        }
        
        return len(errors) == 0, errors, processed_data
    
    @staticmethod
    def validate_barcode(barcode: str, existing_barcodes: List[str] = None) -> Tuple[bool, List[str]]:
        """
        Validiert Barcode
        
        Args:
            barcode: Zu validierender Barcode
            existing_barcodes: Liste existierender Barcodes für Duplikat-Prüfung
            
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        if not barcode:
            errors.append('Barcode ist erforderlich')
        elif len(barcode) > ValidationService.MAX_BARCODE_LENGTH:
            errors.append(f'Barcode darf maximal {ValidationService.MAX_BARCODE_LENGTH} Zeichen lang sein')
        
        if existing_barcodes and barcode in existing_barcodes:
            errors.append('Dieser Barcode existiert bereits')
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_consumable_form(data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validiert Verbrauchsmaterial-Formulardaten
        
        Args:
            data: Formulardaten
            
        Returns:
            (is_valid, errors, processed_data)
        """
        errors = []
        
        # Basis-Validierung
        name = data.get('name', '').strip()
        barcode = data.get('barcode', '').strip()
        quantity = data.get('quantity', '')
        min_quantity = data.get('min_quantity', '')
        
        if not name:
            errors.append('Name ist erforderlich')
        
        if not barcode:
            errors.append('Barcode ist erforderlich')
        
        # Mengen-Validierung
        try:
            quantity = int(quantity) if quantity else 0
            min_quantity = int(min_quantity) if min_quantity else 0
            
            if quantity < 0:
                errors.append('Menge darf nicht negativ sein')
            if min_quantity < 0:
                errors.append('Mindestmenge darf nicht negativ sein')
                
        except ValueError:
            errors.append('Mengen müssen Zahlen sein')
        
        processed_data = {
            'name': name,
            'barcode': barcode,
            'quantity': quantity,
            'min_quantity': min_quantity,
            'description': data.get('description', '').strip(),
            'category': data.get('category', '').strip(),
            'location': data.get('location', '').strip()
        }
        
        return len(errors) == 0, errors, processed_data
    
    @staticmethod
    def validate_tool_form(data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validiert Werkzeug-Formulardaten
        
        Args:
            data: Formulardaten
            
        Returns:
            (is_valid, errors, processed_data)
        """
        errors = []
        
        name = data.get('name', '').strip()
        barcode = data.get('barcode', '').strip()
        
        if not name:
            errors.append('Name ist erforderlich')
        
        if not barcode:
            errors.append('Barcode ist erforderlich')
        
        processed_data = {
            'name': name,
            'barcode': barcode,
            'description': data.get('description', '').strip(),
            'category': data.get('category', '').strip(),
            'location': data.get('location', '').strip(),
            'status': data.get('status', 'verfügbar')
        }
        
        return len(errors) == 0, errors, processed_data
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Prüft ob eine E-Mail-Adresse gültig ist"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def generate_secure_password() -> str:
        """Generiert ein sicheres Passwort"""
        import secrets
        import string
        
        # Mindestens 1 von jeder Kategorie sicherstellen
        password = (
            secrets.choice(string.ascii_uppercase) +  # 1 Großbuchstabe
            secrets.choice(string.ascii_lowercase) +  # 1 Kleinbuchstabe
            secrets.choice(string.digits) +           # 1 Ziffer
            secrets.choice("!@#$%^&*") +              # 1 Sonderzeichen
            ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for _ in range(8))  # 8 weitere zufällige Zeichen
        )
        
        # Passwort mischen
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        return ''.join(password_list) 