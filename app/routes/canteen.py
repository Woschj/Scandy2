"""
Kantinenplan Routes für Scandy
Verwaltet Mahlzeiten und API-Zugriff
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import admin_required, mitarbeiter_required
from app.services.canteen_service import CanteenService
from app.models.mongodb_database import is_feature_enabled
from app.config.config import config
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

bp = Blueprint('canteen', __name__)

@bp.route('/canteen')
def index():
    """Hauptseite für Kantinenplan"""
    if not is_feature_enabled('canteen_plan'):
        flash('Kantinenplan-Feature ist nicht aktiviert', 'error')
        return redirect(url_for('dashboard.index'))
    
    try:
        service = CanteenService()
        meals = service.get_current_week_meals()
        credentials_status = service.get_credentials_status()
        
        meals = service.get_two_weeks_meals()  # Hole 2 Wochen Daten
        api_current = url_for('canteen.api_current_week', _external=True)
        api_today = url_for('canteen.api_today', _external=True)
        api_two_weeks = url_for('canteen.api_two_weeks', _external=True)
        api_status = url_for('canteen.api_status', _external=True)
        embed_url = url_for('canteen.embed', _external=True)
        embed_today_url = url_for('canteen.embed_today', _external=True)
        api_key_value = config.get('CANTEEN_API_KEY')
        return render_template('canteen/index.html', 
                             meals=meals, 
                             credentials_status=credentials_status,
                             api_current=api_current,
                             api_today=api_today,
                             api_two_weeks=api_two_weeks,
                             api_status=api_status,
                             embed_url=embed_url,
                             embed_today_url=embed_today_url,
                             canteen_api_key=api_key_value)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Kantinenplan-Seite: {e}")
        flash('Fehler beim Laden der Daten', 'error')
        return redirect(url_for('dashboard.index'))

@bp.route('/canteen/embed')
def embed():
    """Schlanke Einbettungsansicht (für iframe/WordPress). Optionaler api_key via Querystring."""
    try:
        # Basis-API-URL
        api_current = url_for('canteen.api_current_week', _external=True)
        # Optionalen API-Key anfügen (falls in WordPress gewünscht)
        api_key = request.args.get('api_key', '').strip()
        if api_key:
            sep = '&' if '?' in api_current else '?'
            api_current = f"{api_current}{sep}api_key={api_key}"
        return render_template('canteen/embed.html', api_current=api_current)
    except Exception as e:
        logger.error(f"Fehler beim Rendern der Canteen-Embed-Ansicht: {e}")
        return jsonify({'success': False, 'error': 'Embed nicht verfügbar'}), 500

@bp.route('/canteen/embed/today')
def embed_today():
    """Schlanke Einbettungsansicht nur für den aktuellen Tag (iframe). Optionaler api_key via Querystring."""
    try:
        api_today = url_for('canteen.api_today', _external=True)
        api_key = request.args.get('api_key', '').strip()
        if api_key:
            sep = '&' if '?' in api_today else '?'
            api_today = f"{api_today}{sep}api_key={api_key}"
        return render_template('canteen/embed_today.html', api_today=api_today)
    except Exception as e:
        logger.error(f"Fehler beim Rendern der Canteen-Embed-Today-Ansicht: {e}")
        return jsonify({'success': False, 'error': 'Embed Today nicht verfügbar'}), 500

@bp.route('/canteen/update', methods=['POST'])
def update_canteen_plan():
    """Aktualisiert den Kantinenplan (2 Wochen)"""
    try:
        # Prüfe Berechtigung
        if not current_user.canteen_plan_enabled:
            is_ajax = (request.headers.get('Content-Type', '').startswith('application/json') or 
                       request.headers.get('X-Requested-With') == 'XMLHttpRequest')
            if is_ajax:
                return jsonify({'success': False, 'error': 'Keine Berechtigung für Kantinenplan-Eingabe'}), 403
            flash('Keine Berechtigung für Kantinenplan-Eingabe', 'error')
            return redirect(url_for('canteen.index'))
        
        service = CanteenService()
        
        # Sammle Daten für 2 Wochen (10 Tage)
        meals_data = []
        for i in range(10):  # 2 Wochen = 10 Tage
            date = request.form.get(f'date_{i}')
            meat_dish = request.form.get(f'meat_dish_{i}', '').strip()
            vegan_dish = request.form.get(f'vegan_dish_{i}', '').strip()
            dessert = 'Tagesdessert'
            
            if date:
                meals_data.append({
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert
                })
        
        # Speichere in Datenbank
        success, message = service.save_meals(meals_data)
        
        # Prüfe ob es ein AJAX-Request ist
        is_ajax = (request.headers.get('Content-Type', '').startswith('application/json') or 
                   request.headers.get('X-Requested-With') == 'XMLHttpRequest')
        
        if is_ajax:
            if success:
                return jsonify({'success': True, 'message': 'Kantinenplan erfolgreich aktualisiert!'})
            else:
                return jsonify({'success': False, 'error': message}), 500
        else:
            # Normaler Form-Submit
            if success:
                flash('Kantinenplan erfolgreich aktualisiert!', 'success')
            else:
                flash(f'Fehler beim Speichern: {message}', 'error')
            
            return redirect(url_for('canteen.index'))
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Kantinenplans: {e}")
        error_message = f'Fehler beim Speichern: {str(e)}'
        
        is_ajax = (request.headers.get('Content-Type', '').startswith('application/json') or 
                   request.headers.get('X-Requested-With') == 'XMLHttpRequest')
        if is_ajax:
            return jsonify({'success': False, 'error': error_message}), 500
        else:
            flash(error_message, 'error')
            return redirect(url_for('canteen.index'))

@bp.route('/admin/canteen_status')
@admin_required
def canteen_status():
    """Gibt Status der Kantinenplan-Konfiguration zurück"""
    if not is_feature_enabled('canteen_plan'):
        return jsonify({'enabled': False})
    
    try:
        service = CanteenService()
        
        return jsonify({
            'enabled': True,
            'api_configured': True,
            'message': 'API-basierte Kantinenplan-Verwaltung aktiv'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Kantinenplan-Status: {e}")
        return jsonify({'enabled': True, 'error': str(e)})

@bp.route('/api/canteen/current_week', methods=['GET'])
def api_current_week():
    """API-Endpunkt für aktuelle Woche (WordPress-kompatibel)"""
    try:
        # Optional API Key Check
        api_key = request.args.get('api_key')
        if config.get('CANTEEN_API_KEY') and api_key != config.get('CANTEEN_API_KEY'):
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        service = CanteenService()
        meals = service.get_current_week_meals()
        
        # Formatiere für WordPress-Kompatibilität
        week_data = []
        weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']
        
        for i, meal in enumerate(meals):
            date = meal.get('date', '')
            meat_dish = meal.get('meat_dish', '').strip()
            vegan_dish = meal.get('vegan_dish', '').strip()
            dessert = meal.get('dessert', '').strip()

            # Datum ohne Wochentag (Format: 15.01.2024)
            if date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    date_label = date_obj.strftime('%d.%m.%Y')
                except Exception as e:
                    logger.warning(f"Fehler bei Datumskonvertierung: {e}")
                    date_label = date
            else:
                # Fallback: Datum anhand aktueller Woche bestimmen
                today = datetime.now()
                monday = today - timedelta(days=today.weekday())
                target_date = monday + timedelta(days=i)
                date_label = target_date.strftime('%d.%m.%Y')

            week_data.append({
                'date': date_label,
                'weekday': weekdays[i % 5],
                'meat_dish': meat_dish,
                'vegan_dish': vegan_dish,
                'dessert': dessert
            })
        
        return jsonify({
            'success': True,
            'week': week_data,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API-Fehler: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/canteen/today', methods=['GET'])
def api_today():
    """API-Endpunkt für den aktuellen Tag"""
    try:
        # Optional API Key Check
        api_key = request.args.get('api_key')
        if config.get('CANTEEN_API_KEY') and api_key != config.get('CANTEEN_API_KEY'):
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401

        service = CanteenService()
        meal = service.get_today_meal()

        # Wochentag ermitteln
        weekday_map = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        try:
            date_obj = datetime.strptime(meal.get('date'), '%Y-%m-%d')
            weekday_label = weekday_map[date_obj.weekday()]
            date_label = date_obj.strftime('%d.%m.%Y')
        except Exception:
            weekday_label = ''
            date_label = meal.get('date')

        return jsonify({
            'success': True,
            'date': date_label,
            'weekday': weekday_label,
            'meat_dish': meal.get('meat_dish', ''),
            'vegan_dish': meal.get('vegan_dish', ''),
            'dessert': meal.get('dessert', '') or 'Tagesdessert',
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"API-Fehler (today): {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/canteen/two_weeks', methods=['GET'])
def api_two_weeks():
    """API-Endpunkt für 2 Wochen (WordPress-kompatibel)"""
    try:
        # Optional API Key Check
        api_key = request.args.get('api_key')
        if config.get('CANTEEN_API_KEY') and api_key != config.get('CANTEEN_API_KEY'):
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        service = CanteenService()
        meals = service.get_two_weeks_meals()
        
        # Formatiere für WordPress-Kompatibilität
        two_weeks_data = []
        weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']
        
        for i, meal in enumerate(meals):
            date = meal.get('date', '')
            meat_dish = meal.get('meat_dish', '').strip()
            vegan_dish = meal.get('vegan_dish', '').strip()
            dessert = meal.get('dessert', '').strip()

            if date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    date_label = date_obj.strftime('%d.%m.%Y')
                except Exception as e:
                    logger.warning(f"Fehler bei Datumskonvertierung: {e}")
                    date_label = date
            else:
                today = datetime.now()
                monday = today - timedelta(days=today.weekday())
                target_date = monday + timedelta(days=i)
                date_label = target_date.strftime('%d.%m.%Y')

            two_weeks_data.append({
                'date': date_label,
                'weekday': weekdays[i % 5],
                'meat_dish': meat_dish,
                'vegan_dish': vegan_dish,
                'dessert': dessert
            })
        
        return jsonify({
            'success': True,
            'two_weeks': two_weeks_data,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API-Fehler: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/canteen/status', methods=['GET'])
def api_status():
    """API-Endpoint für Status-Informationen"""
    try:
        service = CanteenService()
        status = service.get_credentials_status()
        
        return jsonify({
            'success': True,
            'feature_enabled': is_feature_enabled('canteen_plan'),
            'sftp_configured': status.get('configured', False),
            'last_update': status.get('last_update'),
            'server_info': {
                'host': status.get('host'),
                'path': status.get('path')
            },
            'api_urls': {
                'current_week': url_for('canteen.api_current_week', _external=True),
                'two_weeks': url_for('canteen.api_two_weeks', _external=True),
                'status': url_for('canteen.api_status', _external=True)
            }
        })
        
    except Exception as e:
        logger.error(f"Status-API-Fehler: {e}")
        return jsonify({'error': 'Interner Server-Fehler'}), 500

@bp.route('/canteen/debug', methods=['GET'])
def debug_canteen():
    """Debug-Route für Kantinenplan-Probleme"""
    try:
        from app.models.mongodb_database import mongodb
        
        # Prüfe Datenbank-Verbindung
        db_status = "OK"
        try:
            mongodb.find_one('users', {})
        except Exception as e:
            db_status = f"Fehler: {e}"
        
        # Prüfe Feature-Status
        feature_enabled = is_feature_enabled('canteen_plan')
        
        # Prüfe Nutzende-Status
        user_status = "Nicht eingeloggt"
        if current_user.is_authenticated:
            user_status = f"Eingeloggt: {current_user.username} (Role: {current_user.role})"
            if hasattr(current_user, 'canteen_plan_enabled'):
                user_status += f", Canteen enabled: {current_user.canteen_plan_enabled}"
        
        return jsonify({
            'database_status': db_status,
            'feature_enabled': feature_enabled,
            'user_status': user_status,
            'current_user_id': str(current_user.get_id()) if current_user.is_authenticated else None,
            'api_urls': {
                'current_week': url_for('canteen.api_current_week', _external=True),
                'two_weeks': url_for('canteen.api_two_weeks', _external=True),
                'status': url_for('canteen.api_status', _external=True)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/canteen/simple_save', methods=['POST'])
def simple_save():
    """Einfache Test-Route für Speicherung (ohne Authentifizierung)"""
    try:
        service = CanteenService()
        
        # Sammle Daten für 2 Wochen (10 Tage)
        meals_data = []
        for i in range(10):  # 2 Wochen = 10 Tage
            date = request.form.get(f'date_{i}')
            meat_dish = request.form.get(f'meat_dish_{i}', '').strip()
            vegan_dish = request.form.get(f'vegan_dish_{i}', '').strip()
            dessert = request.form.get(f'dessert_{i}', '').strip()
            
            if date:
                meals_data.append({
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert
                })
        
        # Verwende die normale Service-Methode
        success, message = service.save_meals(meals_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Daten erfolgreich gespeichert!'
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    try:
        from app.models.mongodb_database import mongodb
        
        # Hole alle Daten aus der Datenbank
        all_meals = mongodb.find('canteen_meals', {})
        
        # Hole Daten für spezifisches Datum
        test_meal = mongodb.find_one('canteen_meals', {'date': '2025-08-04'})
        
        return jsonify({
            'all_meals': list(all_meals),
            'test_meal': test_meal,
            'count': len(list(all_meals))
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@bp.route('/canteen/debug_form', methods=['POST'])
def debug_form():
    """Debug-Route um zu sehen, was das Formular sendet"""
    try:
        # Sammle alle Formular-Daten
        form_data = {}
        for i in range(10):  # 2 Wochen = 10 Tage
            date = request.form.get(f'date_{i}')
            meat_dish = request.form.get(f'meat_dish_{i}', '').strip()
            vegan_dish = request.form.get(f'vegan_dish_{i}', '').strip()
            dessert = request.form.get(f'dessert_{i}', '').strip()
            
            if date:
                form_data[f'day_{i}'] = {
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert
                }
        
        return jsonify({
            'success': True,
            'form_data': form_data,
            'all_form_data': dict(request.form)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/canteen/debug_complete', methods=['POST'])
def debug_complete():
    """Komplette Debug-Route um alle Formular-Daten zu sehen"""
    try:
        # Sammle alle Formular-Daten
        all_data = dict(request.form)
        
        # Sammle Daten für 2 Wochen (10 Tage)
        meals_data = []
        for i in range(10):  # 2 Wochen = 10 Tage
            date = request.form.get(f'date_{i}')
            meat_dish = request.form.get(f'meat_dish_{i}', '').strip()
            vegan_dish = request.form.get(f'vegan_dish_{i}', '').strip()
            dessert = request.form.get(f'dessert_{i}', '').strip()
            
            if date:
                meals_data.append({
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert
                })
        
        # Speichere in Datenbank
        service = CanteenService()
        success, message = service.save_meals(meals_data)
        
        return jsonify({
            'success': True,
            'all_form_data': all_data,
            'meals_data': meals_data,
            'save_success': success,
            'save_message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/canteen/direct_save', methods=['POST'])
def direct_save():
    """Direkte Test-Route die die Datenbank verwendet"""
    try:
        from app.models.mongodb_database import mongodb
        from datetime import datetime
        
        # Sammle Daten für 2 Wochen (10 Tage)
        meals_data = []
        for i in range(10):  # 2 Wochen = 10 Tage
            date = request.form.get(f'date_{i}')
            meat_dish = request.form.get(f'meat_dish_{i}', '').strip()
            vegan_dish = request.form.get(f'vegan_dish_{i}', '').strip()
            dessert = request.form.get(f'dessert_{i}', '').strip()
            
            if date:
                meals_data.append({
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert
                })
        
        # Speichere direkt in Datenbank
        for meal in meals_data:
            date = meal.get('date')
            meat_dish = meal.get('meat_dish', '').strip()
            vegan_dish = meal.get('vegan_dish', '').strip()
            dessert = meal.get('dessert', '').strip()
            
            if not date:
                continue
            
            # Prüfe ob Eintrag bereits existiert
            existing_meal = mongodb.find_one('canteen_meals', {'date': date})
            
            meal_data = {
                'date': date,
                'meat_dish': meat_dish,
                'vegan_dish': vegan_dish,
                'dessert': dessert,
                'updated_at': datetime.now()
            }
            
            if existing_meal:
                # Update existierenden Eintrag
                mongodb.update_one('canteen_meals', {'date': date}, meal_data)
            else:
                # Erstelle neuen Eintrag
                meal_data['created_at'] = datetime.now()
                mongodb.insert_one('canteen_meals', meal_data)
        
        return jsonify({
            'success': True,
            'message': 'Daten direkt in Datenbank gespeichert!',
            'meals_data': meals_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/canteen/test_save', methods=['POST'])
def test_save():
    """Test-Route die alle Formular-Daten loggt"""
    try:
        # Logge alle Formular-Daten
        all_form_data = dict(request.form)
        logger.info(f"Alle Formular-Daten: {all_form_data}")
        
        # Sammle Daten für 2 Wochen (10 Tage)
        meals_data = []
        for i in range(10):  # 2 Wochen = 10 Tage
            date = request.form.get(f'date_{i}')
            meat_dish = request.form.get(f'meat_dish_{i}', '').strip()
            vegan_dish = request.form.get(f'vegan_dish_{i}', '').strip()
            dessert = request.form.get(f'dessert_{i}', '').strip()
            
            logger.info(f"Tag {i}: date={date}, meat={meat_dish}, vegan={vegan_dish}, dessert={dessert}")
            
            if date:
                meals_data.append({
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert
                })
        
        # Speichere direkt in Datenbank
        from app.models.mongodb_database import mongodb
        from datetime import datetime
        
        for meal in meals_data:
            date = meal.get('date')
            meat_dish = meal.get('meat_dish', '').strip()
            vegan_dish = meal.get('vegan_dish', '').strip()
            dessert = meal.get('dessert', '').strip()
            
            if not date:
                continue
            
            # Prüfe ob Eintrag bereits existiert
            existing_meal = mongodb.find_one('canteen_meals', {'date': date})
            
            meal_data = {
                'date': date,
                'meat_dish': meat_dish,
                'vegan_dish': vegan_dish,
                'dessert': dessert,
                'updated_at': datetime.now()
            }
            
            if existing_meal:
                # Update existierenden Eintrag
                mongodb.update_one('canteen_meals', {'date': date}, meal_data)
                logger.info(f"Update: {date} -> {meat_dish}")
            else:
                # Erstelle neuen Eintrag
                meal_data['created_at'] = datetime.now()
                mongodb.insert_one('canteen_meals', meal_data)
                logger.info(f"Insert: {date} -> {meat_dish}")
        
        return jsonify({
            'success': True,
            'message': 'Daten gespeichert!',
            'all_form_data': all_form_data,
            'meals_data': meals_data
        })
        
    except Exception as e:
        logger.error(f"Fehler in test_save: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/canteen/debug_request', methods=['GET', 'POST'])
def debug_request():
    """Debug-Route die alle Requests loggt"""
    logger.info(f"=== DEBUG REQUEST ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    if request.method == 'POST':
        logger.info(f"Form Data: {dict(request.form)}")
        try:
            json_data = request.get_json()
            logger.info(f"JSON Data: {json_data}")
        except Exception as e:
            logger.info(f"JSON Data: None (not JSON content-type) - {e}")
    
    return jsonify({
        'method': request.method,
        'url': request.url,
        'headers': dict(request.headers),
        'form_data': dict(request.form) if request.method == 'POST' else None
    })

@bp.route('/canteen/simple_test', methods=['GET', 'POST'])
def simple_test():
    """Einfache Test-Route die direkt im Browser funktioniert"""
    if request.method == 'POST':
        logger.info(f"=== SIMPLE TEST POST ===")
        logger.info(f"Form Data: {dict(request.form)}")
        
        # Sammle Daten
        meals_data = []
        for i in range(10):
            date = request.form.get(f'date_{i}')
            meat_dish = request.form.get(f'meat_dish_{i}', '').strip()
            vegan_dish = request.form.get(f'vegan_dish_{i}', '').strip()
            dessert = request.form.get(f'dessert_{i}', '').strip()
            
            if date:
                meals_data.append({
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert
                })
        
        # Speichere in Datenbank
        from app.models.mongodb_database import mongodb
        from datetime import datetime
        
        for meal in meals_data:
            date = meal.get('date')
            meat_dish = meal.get('meat_dish', '').strip()
            vegan_dish = meal.get('vegan_dish', '').strip()
            dessert = meal.get('dessert', '').strip()
            
            if not date:
                continue
            
            meal_data = {
                'date': date,
                'meat_dish': meat_dish,
                'vegan_dish': vegan_dish,
                'dessert': dessert,
                'updated_at': datetime.now()
            }
            
            existing_meal = mongodb.find_one('canteen_meals', {'date': date})
            if existing_meal:
                mongodb.update_one('canteen_meals', {'date': date}, meal_data)
                logger.info(f"Update: {date} -> {meat_dish}")
            else:
                meal_data['created_at'] = datetime.now()
                mongodb.insert_one('canteen_meals', meal_data)
                logger.info(f"Insert: {date} -> {meat_dish}")
        
        return f"""
        <html>
        <head><title>Test Erfolgreich</title></head>
        <body>
        <h1>Test Erfolgreich!</h1>
        <p>Daten gespeichert:</p>
        <pre>{meals_data}</pre>
        <p><a href="/canteen">Zurück zum Kantinenplan</a></p>
        </body>
        </html>
        """
    
    # GET - Zeige einfaches Formular
    return f"""
    <html>
    <head><title>Einfacher Test</title></head>
    <body>
    <h1>Einfacher Test</h1>
    <form method="POST">
        <p>Datum: <input type="date" name="date_0" value="2025-08-04"></p>
        <p>Fleisch: <input type="text" name="meat_dish_0" value="TestFleisch"></p>
        <p>Vegan: <input type="text" name="vegan_dish_0" value="TestVegan"></p>
        <p>Dessert: <input type="text" name="dessert_0" value="TestDessert"></p>
        <p><input type="submit" value="Speichern"></p>
    </form>
    <p><a href="/canteen">Zurück zum Kantinenplan</a></p>
    </body>
    </html>
    """