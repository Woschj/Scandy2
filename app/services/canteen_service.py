"""
Kantinenplan Service für Scandy
API-basierte Verwaltung von Mahlzeiten
"""
import csv
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from io import StringIO
import logging

logger = logging.getLogger(__name__)

class CanteenService:
    """API-basierter Kantinenplan Service"""
    
    def __init__(self):
        pass
    
    def _generate_csv(self, meals_data: List[Dict]) -> str:
        """Generiert CSV-Inhalt für Kantinenplan im WordPress-Format"""
        try:
            output = StringIO()
            writer = csv.writer(output)
            
            # Wochentage für WordPress-Format
            weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']
            
            # Daten im WordPress-Format
            for i, meal in enumerate(meals_data):
                date = meal.get('date', '')
                meat_dish = meal.get('meat_dish', '').strip()
                vegan_dish = meal.get('vegan_dish', '').strip()
                dessert = meal.get('dessert', '').strip()  # Neues Dessert-Feld
                
                # Formatiere Datum für WordPress (z.B. "Montag, 15.01.2024")
                if date:
                    try:
                        date_obj = datetime.strptime(date, '%Y-%m-%d')
                        formatted_date = f"{weekdays[i % 5]}, {date_obj.strftime('%d.%m.%Y')}"
                    except:
                        formatted_date = f"{weekdays[i % 5]}, {date}"
                else:
                    # Fallback: Verwende aktuelles Datum für diese Woche
                    today = datetime.now()
                    monday = today - timedelta(days=today.weekday())
                    target_date = monday + timedelta(days=i)
                    formatted_date = f"{weekdays[i % 5]}, {target_date.strftime('%d.%m.%Y')}"
                
                # Entferne Kommas aus den Gerichten (verursachen CSV-Probleme)
                meat_dish = meat_dish.replace(',', ';') if meat_dish else ''
                vegan_dish = vegan_dish.replace(',', ';') if vegan_dish else ''
                dessert = dessert.replace(',', ';') if dessert else ''  # Dessert auch bereinigen
                
                writer.writerow([formatted_date, meat_dish, vegan_dish, dessert])  # 4 Spalten wie in alter CSV
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Fehler beim Generieren der CSV: {str(e)}")
            return ""
    
    def get_current_week_meals(self) -> List[Dict]:
        """Holt Mahlzeiten für die aktuelle Woche (Montag-Freitag)"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Berechne Montag der aktuellen Woche
            today = datetime.now()
            monday = today - timedelta(days=today.weekday())
            monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Erstelle Datumsliste für Montag-Freitag
            week_dates = []
            for i in range(5):  # Montag bis Freitag
                week_date = monday + timedelta(days=i)
                week_dates.append(week_date.strftime('%Y-%m-%d'))
            
            # Lade Mahlzeiten aus der Datenbank
            meals = []
            for date in week_dates:
                meal = mongodb.find_one('canteen_meals', {'date': date})
                if meal:
                    meals.append(meal)
                else:
                    # Erstelle leeren Eintrag für fehlende Tage
                    meals.append({
                        'date': date,
                        'meat_dish': '',
                        'vegan_dish': '',
                        'dessert': '',  # Neues Dessert-Feld
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    })
            
            return meals
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Mahlzeiten: {str(e)}")
            return []
    
    def get_two_weeks_meals(self) -> List[Dict]:
        """Holt Mahlzeiten für 2 Wochen (Montag-Freitag)"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Berechne Montag der aktuellen Woche
            today = datetime.now()
            monday = today - timedelta(days=today.weekday())
            monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Erstelle Datumsliste für 2 Wochen (Montag-Freitag)
            week_dates = []
            for week in range(2):  # 2 Wochen
                for day in range(5):  # Montag bis Freitag
                    week_date = monday + timedelta(days=(week * 7) + day)
                    week_dates.append(week_date.strftime('%Y-%m-%d'))
            
            # Lade Mahlzeiten aus der Datenbank
            meals = []
            for i, date in enumerate(week_dates):
                meal = mongodb.find_one('canteen_meals', {'date': date})
                if meal:
                    # Berechne Kalenderwoche
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    calendar_week = date_obj.isocalendar()[1]
                    
                    meal['calendar_week'] = calendar_week
                    meals.append(meal)
                else:
                    # Erstelle leeren Eintrag für fehlende Tage
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    calendar_week = date_obj.isocalendar()[1]
                    
                    meals.append({
                        'date': date,
                        'meat_dish': '',
                        'vegan_dish': '',
                        'dessert': '',  # Neues Dessert-Feld
                        'calendar_week': calendar_week,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    })
            
            return meals
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Mahlzeiten: {str(e)}")
            return []

    def get_today_meal(self) -> Dict:
        """Holt die Mahlzeit für den aktuellen Tag.

        Returns ein Dict mit Schlüsseln: date (YYYY-MM-DD), meat_dish, vegan_dish, dessert.
        Wenn kein Eintrag vorhanden ist, werden leere Felder zurückgegeben.
        """
        try:
            from app.models.mongodb_database import mongodb

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            date_str = today.strftime('%Y-%m-%d')

            meal = mongodb.find_one('canteen_meals', {'date': date_str})
            if meal:
                return {
                    'date': meal.get('date', date_str),
                    'meat_dish': (meal.get('meat_dish') or '').strip(),
                    'vegan_dish': (meal.get('vegan_dish') or '').strip(),
                    'dessert': (meal.get('dessert') or '').strip(),
                }
            else:
                return {
                    'date': date_str,
                    'meat_dish': '',
                    'vegan_dish': '',
                    'dessert': ''
                }
        except Exception as e:
            logger.error(f"Fehler beim Laden der Tagesmahlzeit: {str(e)}")
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'meat_dish': '',
                'vegan_dish': '',
                'dessert': ''
            }
    
    def save_meals(self, meals_data: List[Dict]) -> Tuple[bool, str]:
        """Speichert Mahlzeiten in der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Lösche alte Daten (älter als 30 Tage) - nur wenn created_at existiert
            thirty_days_ago = datetime.now() - timedelta(days=30)
            mongodb.delete_many('canteen_meals', {
                'created_at': {'$lt': thirty_days_ago}
            })
            
            for meal in meals_data:
                date = meal.get('date')
                meat_dish = meal.get('meat_dish', '').strip()
                vegan_dish = meal.get('vegan_dish', '').strip()
                dessert = meal.get('dessert', '').strip()  # Neues Dessert-Feld
                
                if not date:
                    continue
                
                # Prüfe ob Eintrag bereits existiert
                existing_meal = mongodb.find_one('canteen_meals', {'date': date})
                
                meal_data = {
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert,  # Neues Dessert-Feld
                    'updated_at': datetime.now()
                }
                
                if existing_meal:
                    # Update existierenden Eintrag
                    mongodb.update_one('canteen_meals', {'date': date}, meal_data)
                else:
                    # Erstelle neuen Eintrag
                    meal_data['created_at'] = datetime.now()
                    mongodb.insert_one('canteen_meals', meal_data)
            
            return True, "Mahlzeiten erfolgreich gespeichert"
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Mahlzeiten: {str(e)}")
            return False, f"Fehler beim Speichern: {str(e)}"
    
    def update_canteen_plan(self, meals_data: List[Dict]) -> Tuple[bool, str]:
        """Aktualisiert Kantinenplan (API-basiert)"""
        try:
            # Speichere in Datenbank
            save_success, save_message = self.save_meals(meals_data)
            if not save_success:
                return False, save_message
            
            return True, f"Kantinenplan erfolgreich aktualisiert (API-basiert)"
                
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Kantinenplans: {str(e)}")
            return False, f"Fehler: {str(e)}"
    
    def get_credentials_status(self) -> Dict:
        """Gibt Status der API-Konfiguration zurück"""
        try:
            return {
                'configured': True,
                'api_enabled': True,
                'message': 'API-basierte Kantinenplan-Verwaltung aktiv'
            }
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des API-Status: {str(e)}")
            return {
                'configured': False,
                'api_enabled': False,
                'message': 'API nicht verfügbar'
            } 