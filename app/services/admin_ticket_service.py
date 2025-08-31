"""
Admin Ticket Service

Dieser Service enthält alle Funktionen für die Ticket-Verwaltung,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from docxtpl import DocxTemplate
from flask import current_app, send_file
from app.models.mongodb_database import mongodb
from app.models.mongodb_models import MongoDBUser
from app.utils.id_helpers import find_document_by_id, convert_id_for_query

logger = logging.getLogger(__name__)

class AdminTicketService:
    """Service für Admin-Ticket-Funktionen"""
    
    @staticmethod
    def get_ticket_by_id(ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Hole ein Ticket anhand der ID
        
        Args:
            ticket_id: ID des Tickets
            
        Returns:
            Ticket-Daten oder None
        """
        try:
            ticket = find_document_by_id('tickets', ticket_id)
            if ticket and '_id' in ticket:
                ticket['_id'] = str(ticket['_id'])
            return ticket
            
        except Exception as e:
            logger.error(f"Fehler beim Laden des Tickets {ticket_id}: {str(e)}")
            return None

    @staticmethod
    def get_ticket_details(ticket_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Hole Ticket-Details, Auftragsdetails und Materialliste
        
        Args:
            ticket_id: ID des Tickets
            
        Returns:
            (ticket, auftrag_details, material_list)
        """
        try:
            # Robuste ID-Behandlung
            ticket = find_document_by_id('tickets', ticket_id)
            if not ticket:
                return None, None, []
            
            ticket_id_for_query = convert_id_for_query(ticket_id)
            
            # Hole Auftragsdetails
            auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query}) or {}
            
            # Hole Materialliste
            material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id_for_query})) or []
            
            return ticket, auftrag_details, material_list
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ticket-Details {ticket_id}: {str(e)}")
            return None, None, []

    @staticmethod
    def add_ticket_message(ticket_id: str, message: str, message_type: str = 'message') -> Tuple[bool, str]:
        """
        Fügt eine Nachricht zu einem Ticket hinzu
        
        Args:
            ticket_id: ID des Tickets
            message: Nachrichtentext
            message_type: Typ der Nachricht (message, note)
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Ticket existiert
            ticket = find_document_by_id('tickets', ticket_id)
            if not ticket:
                return False, "Ticket nicht gefunden"
            
            # Erstelle Nachricht
            message_data = {
                'ticket_id': ticket_id,
                'message': message,
                'type': message_type,
                'created_by': 'admin',  # Könnte später erweitert werden
                'created_at': datetime.now()
            }
            
            mongodb.insert_one('ticket_messages', message_data)
            
            logger.info(f"Nachricht zu Ticket {ticket_id} hinzugefügt")
            return True, "Nachricht erfolgreich hinzugefügt"
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Nachricht zu Ticket {ticket_id}: {str(e)}")
            return False, f"Fehler beim Hinzufügen der Nachricht: {str(e)}"

    @staticmethod
    def update_ticket_status(ticket_id: str, new_status: str) -> Tuple[bool, str]:
        """
        Aktualisiert den Status eines Tickets
        
        Args:
            ticket_id: ID des Tickets
            new_status: Neuer Status
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Ticket existiert
            ticket = find_document_by_id('tickets', ticket_id)
            if not ticket:
                return False, "Ticket nicht gefunden"
            
            # Aktualisiere Status
            mongodb.update_one('tickets', {'_id': ticket_id}, {
                '$set': {
                    'status': new_status,
                    'updated_at': datetime.now()
                }
            })
            
            logger.info(f"Status von Ticket {ticket_id} auf '{new_status}' geändert")
            return True, f"Status erfolgreich auf '{new_status}' geändert"
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Status von Ticket {ticket_id}: {str(e)}")
            return False, f"Fehler beim Aktualisieren des Status: {str(e)}"

    @staticmethod
    def update_ticket_assignment(ticket_id: str, assigned_to: str) -> Tuple[bool, str]:
        """
        Aktualisiert die Zuweisung eines Tickets
        
        Args:
            ticket_id: ID des Tickets
            assigned_to: Nutzendename des zugewiesenen Nutzendes
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Ticket existiert
            ticket = find_document_by_id('tickets', ticket_id)
            if not ticket:
                return False, "Ticket nicht gefunden"
            
            # Prüfe ob Nutzende existiert (falls zugewiesen)
            if assigned_to:
                user = MongoDBUser.get_by_username(assigned_to)
                if not user:
                    return False, "Zugewiesener Nutzende nicht gefunden"
            
            # Aktualisiere Zuweisung
            mongodb.update_one('tickets', {'_id': ticket_id}, {
                '$set': {
                    'assigned_to': assigned_to,
                    'updated_at': datetime.now()
                }
            })
            
            # Wenn Zuweisung entfernt wurde, setze Status auf 'offen' (sofern nicht final)
            if not assigned_to:
                try:
                    current = find_document_by_id('tickets', ticket_id)
                    if current and current.get('status') not in ['gelöst', 'geschlossen']:
                        mongodb.update_one('tickets', {'_id': ticket_id}, {
                            '$set': {
                                'status': 'offen',
                                'updated_at': datetime.now()
                            }
                        })
                except Exception as status_err:
                    logger.error(f"Fehler beim Zurücksetzen des Status für Ticket {ticket_id}: {status_err}")
            
            logger.info(f"Zuweisung von Ticket {ticket_id} auf '{assigned_to}' geändert")
            return True, f"Zuweisung erfolgreich auf '{assigned_to}' geändert"
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Zuweisung von Ticket {ticket_id}: {str(e)}")
            return False, f"Fehler beim Aktualisieren der Zuweisung: {str(e)}"

    @staticmethod
    def delete_ticket(ticket_id: str, permanent: bool = False) -> Tuple[bool, str]:
        """
        Löscht ein Ticket
        
        Args:
            ticket_id: ID des Tickets
            permanent: Ob das Ticket permanent gelöscht werden soll
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Ticket existiert
            ticket = find_document_by_id('tickets', ticket_id)
            if not ticket:
                return False, "Ticket nicht gefunden"
            
            if permanent:
                # Permanent löschen
                mongodb.delete_one('tickets', {'_id': ticket_id})
                # Auch zugehörige Daten löschen
                mongodb.delete_many('ticket_messages', {'ticket_id': ticket_id})
                mongodb.delete_many('auftrag_details', {'ticket_id': ticket_id})
                mongodb.delete_many('auftrag_material', {'ticket_id': ticket_id})
                
                logger.info(f"Ticket {ticket_id} permanent gelöscht")
                return True, "Ticket permanent gelöscht"
            else:
                # Soft delete
                mongodb.update_one('tickets', {'_id': ticket_id}, {
                    '$set': {
                        'deleted': True,
                        'deleted_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                })
                
                logger.info(f"Ticket {ticket_id} als gelöscht markiert")
                return True, "Ticket als gelöscht markiert"
                
        except Exception as e:
            logger.error(f"Fehler beim Löschen von Ticket {ticket_id}: {str(e)}")
            return False, f"Fehler beim Löschen des Tickets: {str(e)}"

    @staticmethod
    def export_ticket_as_word(ticket_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Exportiert ein Ticket als Word-Dokument
        
        Args:
            ticket_id: ID des Tickets
            
        Returns:
            (success, message, file_path)
        """
        try:
            # Hole Ticket-Daten
            ticket = find_document_by_id('tickets', ticket_id)
            if not ticket:
                return False, "Ticket nicht gefunden", None
            
            ticket_id_for_query = convert_id_for_query(ticket_id)
            
            # Hole Auftragsdetails und Materialliste
            auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query}) or {}
            material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id_for_query})) or []

            # Auftragnehmer (Vorname Nachname)
            auftragnehmer_user = None
            if ticket.get('assigned_to'):
                auftragnehmer_user = MongoDBUser.get_by_username(ticket['assigned_to'])
            if auftragnehmer_user:
                # MongoDBUser.get_by_username() gibt ein Dictionary zurück, kein Objekt
                auftragnehmer_name = f"{auftragnehmer_user.get('firstname', '') or ''} {auftragnehmer_user.get('lastname', '') or ''}".strip()
            else:
                auftragnehmer_name = ''

            # Ausgeführte Arbeiten (bis zu 5)
            arbeiten_liste = auftrag_details.get('ausgefuehrte_arbeiten', '')
            arbeiten_zeilen = []
            if arbeiten_liste:
                for zeile in arbeiten_liste.split('\n'):
                    if not zeile.strip():
                        continue
                    teile = [t.strip() for t in zeile.split('|')]
                    eintrag = {
                        'arbeiten': teile[0] if len(teile) > 0 else '',
                        'arbeitsstunden': teile[1] if len(teile) > 1 else '',
                        'leistungskategorie': teile[2] if len(teile) > 2 else ''
                    }
                    arbeiten_zeilen.append(eintrag)
            
            # Fülle auf 5 Zeilen auf
            while len(arbeiten_zeilen) < 5:
                arbeiten_zeilen.append({'arbeiten':'','arbeitsstunden':'','leistungskategorie':''})

            # Materialdaten aufbereiten
            material_rows = []
            summe_material = 0
            for m in material_list:
                menge = float(m.get('menge') or 0)
                einzelpreis = float(m.get('einzelpreis') or 0)
                gesamtpreis = menge * einzelpreis
                summe_material += gesamtpreis
                material_rows.append({
                    'material': m.get('material', '') or '',
                    'materialmenge': f"{menge:.2f}".replace('.', ',') if menge else '',
                    'materialpreis': f"{einzelpreis:.2f}".replace('.', ',') if einzelpreis else '',
                    'materialpreisges': f"{gesamtpreis:.2f}".replace('.', ',') if gesamtpreis else ''
                })
            
            while len(material_rows) < 5:
                material_rows.append({'material':'','materialmenge':'','materialpreis':'','materialpreisges':''})

            # Berechnungen
            arbeitspausch = 0
            ubertrag = 0
            zwischensumme = summe_material + arbeitspausch + ubertrag
            mwst = zwischensumme * 0.07
            gesamtsumme = zwischensumme + mwst

            # Kontext für docxtpl bauen
            context = {
                'auftragnehmer': auftragnehmer_name,
                'auftragnummer': ticket.get('ticket_number', ticket_id),
                'datum': datetime.now().strftime('%d.%m.%Y'),
                'internchk': '☒' if auftrag_details.get('auftraggeber_intern') else '☐',
                'externchk': '☒' if auftrag_details.get('auftraggeber_extern') else '☐',
                'auftraggebername': auftrag_details.get('auftraggeber_name', ''),
                'auftraggebermail': auftrag_details.get('kontakt', ''),
                'bereich': auftrag_details.get('bereich', ''),
                'auftragsbeschreibung': auftrag_details.get('auftragsbeschreibung', ''),
                'duedate': auftrag_details.get('fertigstellungstermin', ''),
                'gesamtsumme': f"{gesamtsumme:.2f}".replace('.', ','),
                'matsum': f"{summe_material:.2f}".replace('.', ','),
                'ubertrag': f"{ubertrag:.2f}".replace('.', ','),
                'arpausch': f"{arbeitspausch:.2f}".replace('.', ','),
                'zwsum': f"{zwischensumme:.2f}".replace('.', ','),
                'mwst': f"{mwst:.2f}".replace('.', ','),
                'arbeitenblock': '\n'.join([arbeit['arbeiten'] for arbeit in arbeiten_zeilen]),
                'stundenblock': '\n'.join([arbeit['arbeitsstunden'] for arbeit in arbeiten_zeilen]),
                'kategorieblock': '\n'.join([arbeit['leistungskategorie'] for arbeit in arbeiten_zeilen]),
                'materialblock': '\n'.join([material['material'] for material in material_rows]),
                'mengenblock': '\n'.join([material['materialmenge'] for material in material_rows]),
                'preisblock': '\n'.join([material['materialpreis'] for material in material_rows]),
                'gesamtblock': '\n'.join([material['materialpreisges'] for material in material_rows])
            }

            # Word-Dokument generieren
            logger.info(f"Starte Admin-Export für Ticket {ticket_id}")
            
            # Lade das Template
            template_path = os.path.join(current_app.root_path, 'static', 'word', 'btzauftrag.docx')
            logger.info(f"Template-Pfad: {template_path}")
            
            if not os.path.exists(template_path):
                logger.error(f"Template-Datei nicht gefunden: {template_path}")
                return False, "Word-Template nicht gefunden", None
            
            doc = DocxTemplate(template_path)
            logger.info("Template erfolgreich geladen")
            
            # Rendere das Dokument
            logger.info(f"Rendere Dokument mit Kontext: {context}")
            doc.render(context)
            logger.info("Dokument erfolgreich gerendert")
            
            # Erstelle das uploads-Verzeichnis falls es nicht existiert
            uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Speichere das generierte Dokument
            ticket_number = ticket.get('ticket_number', ticket_id)
            output_path = os.path.join(uploads_dir, f'ticket_{ticket_number}_export.docx')
            
            logger.info(f"Speichere Dokument unter: {output_path}")
            doc.save(output_path)
            logger.info("Dokument erfolgreich gespeichert")
            
            logger.info(f"Word-Dokument erfolgreich generiert: {output_path}")
            return True, f"Word-Dokument erfolgreich generiert: {output_path}", output_path
            
        except Exception as e:
            logger.error(f"Fehler beim Generieren des Word-Dokuments: {str(e)}", exc_info=True)
            return False, f"Fehler beim Generieren des Dokuments: {str(e)}", None

    @staticmethod
    def update_ticket_details(ticket_id: str, details_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Aktualisiert die Details eines Tickets
        
        Args:
            ticket_id: ID des Tickets
            details_data: Neue Details-Daten
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Ticket existiert
            ticket = find_document_by_id('tickets', ticket_id)
            if not ticket:
                return False, "Ticket nicht gefunden"

            # Auftragsdetails aktualisieren
            auftrag_details = {
                'ticket_id': ticket_id,
                'auftrag_an': details_data.get('auftrag_an', ''),
                'bereich': details_data.get('bereich', ''),
                'auftraggeber_intern': details_data.get('auftraggeber_typ') == 'intern',
                'auftraggeber_extern': details_data.get('auftraggeber_typ') == 'extern',
                'beschreibung': details_data.get('beschreibung', ''),
                'prioritaet': details_data.get('prioritaet', 'normal'),
                'deadline': details_data.get('deadline'),
                'updated_at': datetime.now()
            }
            
            # Update oder Insert Auftragsdetails
            if not mongodb.update_one('auftrag_details', {'ticket_id': ticket_id}, {'$set': auftrag_details}):
                mongodb.insert_one('auftrag_details', auftrag_details)
            
            logger.info(f"Ticket-Details für {ticket_id} aktualisiert")
            return True, "Ticket-Details erfolgreich aktualisiert"
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Ticket-Details {ticket_id}: {str(e)}")
            return False, f"Fehler beim Aktualisieren der Ticket-Details: {str(e)}"

    @staticmethod
    def get_ticket_statistics() -> Dict[str, Any]:
        """Hole Ticket-Statistiken"""
        try:
            # Gesamtanzahl Tickets
            total_tickets = mongodb.count_documents('tickets', {})
            
            # Tickets nach Status
            status_stats = {}
            statuses = ['offen', 'zugewiesen', 'in_bearbeitung', 'erledigt', 'geschlossen']
            
            for status in statuses:
                count = mongodb.count_documents('tickets', {'status': status})
                status_stats[status] = count
            
            # Tickets nach Kategorie
            category_stats = {}
            categories = list(mongodb.distinct('tickets', 'category'))
            
            for category in categories:
                count = mongodb.count_documents('tickets', {'category': category})
                category_stats[category] = count
            
            # Aktuelle Tickets (letzte 30 Tage)
            from datetime import timedelta
            recent_date = datetime.now() - timedelta(days=30)
            recent_tickets = mongodb.count_documents('tickets', {'created_at': {'$gte': recent_date}})
            
            return {
                'total_tickets': total_tickets,
                'status_stats': status_stats,
                'category_stats': category_stats,
                'recent_tickets': recent_tickets
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ticket-Statistiken: {str(e)}")
            return {
                'total_tickets': 0,
                'status_stats': {},
                'category_stats': {},
                'recent_tickets': 0
            } 