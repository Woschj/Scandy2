#!/usr/bin/env python3
"""
Test-Skript für Passwort-Reset-E-Mails
Testet die E-Mail-Funktionalität für Passwort-Resets
"""

import sys
import os
sys.path.append('/opt/scandy')

def test_password_reset_email():
    """Testet die Passwort-Reset-E-Mail-Funktionalität"""
    
    try:
        from app.utils.email_utils import send_password_reset_mail, get_email_config
        
        print("🔧 Teste Passwort-Reset-E-Mail-Funktionalität...")
        print("=" * 50)
        
        # 1. E-Mail-Konfiguration prüfen
        print("\n1️⃣ Prüfe E-Mail-Konfiguration...")
        config = get_email_config()
        if not config:
            print("❌ Keine E-Mail-Konfiguration gefunden!")
            return False
        
        print("✅ E-Mail-Konfiguration gefunden:")
        for key, value in config.items():
            if key != 'mail_password':
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {'***' if value else 'Nicht gesetzt'}")
        
        # 2. Test-E-Mail mit neuem Passwort senden
        print("\n2️⃣ Sende Test-Passwort-Reset-E-Mail...")
        test_email = config.get('test_email') or config.get('mail_username')
        test_password = "TestPasswort123!"
        
        if not test_email:
            print("❌ Keine Test-E-Mail-Adresse gefunden!")
            return False
        
        print(f"📧 Sende Test-E-Mail an: {test_email}")
        print(f"🔑 Test-Passwort: {test_password}")
        
        success = send_password_reset_mail(
            recipient=test_email,
            password=test_password
        )
        
        if success:
            print("✅ Passwort-Reset-E-Mail erfolgreich gesendet!")
            print(f"📧 Prüfen Sie den Posteingang von: {test_email}")
            return True
        else:
            print("❌ Passwort-Reset-E-Mail fehlgeschlagen!")
            return False
            
    except Exception as e:
        print(f"❌ Fehler beim Testen: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_email_template():
    """Testet die E-Mail-Vorlage für Passwort-Reset"""
    
    try:
        from app.services.admin_email_templates_service import AdminEmailTemplatesService
        
        print("\n3️⃣ Teste E-Mail-Vorlage...")
        
        # Prüfe ob Vorlage existiert
        template = AdminEmailTemplatesService.get_template_by_key('password_reset')
        if not template:
            print("❌ E-Mail-Vorlage 'password_reset' nicht gefunden!")
            return False
        
        print("✅ E-Mail-Vorlage gefunden:")
        print(f"  Name: {template.get('name')}")
        print(f"  Betreff: {template.get('subject')}")
        print(f"  HTML-Inhalt: {len(template.get('html_content', ''))} Zeichen")
        print(f"  Text-Inhalt: {len(template.get('text_content', ''))} Zeichen")
        
        # Teste Template-Rendering
        rendered = AdminEmailTemplatesService.render_template_by_key('password_reset', {
            'password': 'TestPasswort123!',
            'reset_link': 'https://example.com/reset/test'
        })
        
        if rendered:
            print("✅ Template-Rendering erfolgreich:")
            print(f"  Betreff: {rendered.get('subject')}")
            print(f"  HTML: {len(rendered.get('html_content', ''))} Zeichen")
            print(f"  Text: {len(rendered.get('text_content', ''))} Zeichen")
            return True
        else:
            print("❌ Template-Rendering fehlgeschlagen!")
            return False
            
    except Exception as e:
        print(f"❌ Fehler beim Testen der Vorlage: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Passwort-Reset-E-Mail Test")
    print("=" * 50)
    
    # Führe Tests aus
    email_test = test_password_reset_email()
    template_test = test_email_template()
    
    print("\n" + "=" * 50)
    print("📋 Testergebnisse:")
    print(f"  E-Mail-Versand: {'✅ Erfolgreich' if email_test else '❌ Fehlgeschlagen'}")
    print(f"  E-Mail-Vorlage: {'✅ Erfolgreich' if template_test else '❌ Fehlgeschlagen'}")
    
    if email_test and template_test:
        print("\n🎉 Alle Tests erfolgreich!")
        print("Passwort-Reset-E-Mails sollten jetzt funktionieren.")
    else:
        print("\n💥 Einige Tests fehlgeschlagen!")
        print("Überprüfen Sie die Logs für weitere Details.")
