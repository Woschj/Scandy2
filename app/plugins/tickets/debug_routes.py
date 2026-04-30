from flask import render_template, request, jsonify, session, redirect, url_for, flash, abort, send_file, render_template_string, current_app
from flask import g
from app.models.mongodb_models import MongoDBTicket
from app.models.mongodb_database import mongodb, is_feature_enabled
from app.utils.decorators import login_required, admin_required, not_teilnehmer_required
from app.utils.permissions import permission_required
from app.utils.id_helpers import convert_id_for_query, find_document_by_id
from .routes import bp, get_ticket_service
import logging
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger(__name__)

@bp.route('/debug/tickets')
@login_required
@permission_required('tickets', 'view')
def debug_tickets():
    """Debug-Route um alle Tickets anzuzeigen"""
    try:
        all_tickets = mongodb.find('tickets', {})
        ticket_info = []

        for ticket in all_tickets:
            ticket_info.append({
                'id': str(ticket.get('_id')),
                'id_type': type(ticket.get('_id')).__name__,
                'title': ticket.get('title', 'No Title'),
                'status': ticket.get('status', 'Unknown'),
                'created_by': ticket.get('created_by', 'Unknown'),
                'ticket_number': ticket.get('ticket_number', 'No Number')
            })

        return jsonify({
            'total_tickets': len(ticket_info),
            'tickets': ticket_info
        })

    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/debug/test-ticket/<ticket_id>')
@login_required
@permission_required('tickets', 'view')
def test_ticket(ticket_id):
    """Testet das Finden eines spezifischen Tickets"""
    try:
        print(f"DEBUG: Teste Ticket-ID: {ticket_id}")

        # Teste verschiedene Suchmethoden
        results = {}

        # Methode 1: Direkte String-Suche
        ticket = mongodb.find_one('tickets', {'_id': ticket_id})
        results['string_search'] = {
            'found': ticket is not None,
            'title': ticket.get('title') if ticket else None
        }

        # Methode 2: ObjectId-Suche
        try:
            from bson import ObjectId
            obj_id = ObjectId(ticket_id)
            ticket = mongodb.find_one('tickets', {'_id': obj_id})
            results['objectid_search'] = {
                'found': ticket is not None,
                'title': ticket.get('title') if ticket else None
            }
        except Exception as e:
            results['objectid_search'] = {
                'found': False,
                'error': 'Ein interner Fehler ist aufgetreten.'
            }

        # Methode 3: find_document_by_id
        ticket = find_document_by_id('tickets', ticket_id)
        results['find_document_by_id'] = {
            'found': ticket is not None,
            'title': ticket.get('title') if ticket else None
        }

        return jsonify({
            'ticket_id': ticket_id,
            'results': results
        })

    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/debug/normalize-ticket-ids')
@login_required
@permission_required('tickets', 'view')
def normalize_ticket_ids():
    """Normalisiert alle Ticket-IDs zu Strings"""
    try:
        from bson import ObjectId

        all_tickets = mongodb.find('tickets', {})
        updated_count = 0

        for ticket in all_tickets:
            ticket_id = ticket.get('_id')

            # Falls die ID ein ObjectId ist, konvertiere sie zu String
            if isinstance(ticket_id, ObjectId):
                string_id = str(ticket_id)

                # Erstelle ein neues Dokument mit String-ID
                new_ticket = ticket.copy()
                new_ticket['_id'] = string_id

                # Lösche das alte Dokument und füge das neue ein
                mongodb.delete_one('tickets', {'_id': ticket_id})
                mongodb.insert_one('tickets', new_ticket)

                updated_count += 1
                print(f"Ticket-ID normalisiert: {ticket.get('title', 'Unknown')} von {ticket_id} zu {string_id}")

        return jsonify({
            'status': 'success',
            'message': f'{updated_count} Ticket-IDs normalisiert',
            'updated_count': updated_count
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Ein interner Fehler ist aufgetreten.'
        }), 500

@bp.route('/debug/normalize-all-ids')
@login_required
def normalize_all_ids():
    """Normalisiert alle IDs in allen Collections zu Strings"""
    try:
        from bson import ObjectId

        collections_to_normalize = [
            'tickets', 'users', 'tools', 'consumables', 'workers',
            'ticket_messages', 'ticket_notes', 'auftrag_details',
            'auftrag_material', 'auftrag_arbeit'
        ]

        total_updated = 0
        results = {}

        for collection_name in collections_to_normalize:
            try:
                documents = mongodb.find(collection_name, {})
                updated_count = 0

                for doc in documents:
                    doc_id = doc.get('_id')

                    # Falls die ID ein ObjectId ist, konvertiere sie zu String
                    if isinstance(doc_id, ObjectId):
                        string_id = str(doc_id)

                        # Erstelle ein neues Dokument mit String-ID
                        new_doc = doc.copy()
                        new_doc['_id'] = string_id

                        # Lösche das alte Dokument und füge das neue ein
                        mongodb.delete_one(collection_name, {'_id': doc_id})
                        mongodb.insert_one(collection_name, new_doc)

                        updated_count += 1

                results[collection_name] = updated_count
                total_updated += updated_count
                print(f"Collection {collection_name}: {updated_count} IDs normalisiert")

            except Exception as e:
                results[collection_name] = f"Fehler: [Interner Fehler]"
                print(f"Fehler bei Collection {collection_name}: [Interner Fehler]")

        return jsonify({
            'status': 'success',
            'message': f'{total_updated} IDs in allen Collections normalisiert',
            'total_updated': total_updated,
            'results': results
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Ein interner Fehler ist aufgetreten.'
        }), 500

@bp.route('/debug/test-update-ticket/<ticket_id>')
@login_required
@permission_required('tickets', 'edit')
def test_update_ticket(ticket_id):
    """Testet die update_ticket-Route mit einer spezifischen Ticket-ID"""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', ticket_id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(ticket_id)

        # Teste ein einfaches Update
        test_data = {'priority': 'normal', 'updated_at': datetime.now()}
        result = mongodb.update_one('tickets', {'_id': ticket_id_for_query}, {'$set': test_data})

        return jsonify({
            'success': True,
            'message': 'Test-Update erfolgreich',
            'ticket_id': ticket_id,
            'ticket_id_for_query': str(ticket_id_for_query),
            'ticket_id_type': type(ticket_id_for_query).__name__,
            'update_result': str(result)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Ein interner Fehler ist aufgetreten.',
            'ticket_id': ticket_id
        })

@bp.route('/debug/test-mongodb')
@login_required
@permission_required('tickets', 'view')
def test_mongodb():
    """Testet die MongoDB-Verbindung und -Operationen"""
    try:
        # Teste einfache Abfrage
        count = mongodb.count_documents('tickets', {})

        # Teste einfaches Update
        test_ticket = mongodb.find_one('tickets', {})
        if test_ticket:
            test_id = test_ticket['_id']
            result = mongodb.update_one('tickets', {'_id': test_id}, {'$set': {'test_field': 'test_value'}})

            # Entferne das Test-Feld wieder
            mongodb.update_one('tickets', {'_id': test_id}, {'$unset': {'test_field': ''}})

            return jsonify({
                'success': True,
                'message': 'MongoDB-Verbindung funktioniert',
                'ticket_count': count,
                'test_update_result': str(result)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Keine Tickets in der Datenbank gefunden'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'MongoDB-Fehler: [Interner Fehler]'
        })

@bp.route('/debug/test-specific-ticket/<ticket_id>')
@login_required
@permission_required('tickets', 'view')
def test_specific_ticket(ticket_id):
    """Testet eine spezifische Ticket-ID mit allen Methoden"""
    try:
        results = {}

        # Teste find_document_by_id
        ticket = find_document_by_id('tickets', ticket_id)
        results['find_document_by_id'] = {
            'found': ticket is not None,
            'title': ticket.get('title') if ticket else None,
            'id': str(ticket.get('_id')) if ticket else None
        }

        # Teste convert_id_for_query
        converted_id = convert_id_for_query(ticket_id)
        results['convert_id_for_query'] = {
            'converted_id': str(converted_id),
            'type': type(converted_id).__name__
        }

        # Teste direkte MongoDB-Abfrage
        direct_result = mongodb.find_one('tickets', {'_id': converted_id})
        results['direct_mongodb_query'] = {
            'found': direct_result is not None,
            'title': direct_result.get('title') if direct_result else None
        }

        # Teste einfaches Update
        if ticket:
            test_data = {'test_update': datetime.now()}
            update_result = mongodb.update_one('tickets', {'_id': converted_id}, {'$set': test_data})

            # Entferne das Test-Feld wieder
            mongodb.update_one('tickets', {'_id': converted_id}, {'$unset': {'test_update': ''}})

            results['test_update'] = {
                'success': bool(update_result),
                'result': str(update_result)
            }

        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Ein interner Fehler ist aufgetreten.',
            'ticket_id': ticket_id
        })

@bp.route('/debug/test-update-operation/<ticket_id>')
@login_required
@permission_required('tickets', 'edit')
def test_update_operation(ticket_id):
    """Testet die Update-Operation für ein spezifisches Ticket"""
    try:
        print(f"DEBUG: Teste Update-Operation für Ticket-ID: {ticket_id}")

        # Finde das Ticket
        ticket = find_document_by_id('tickets', ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket nicht gefunden'}), 404

        actual_ticket_id = ticket.get('_id')
        print(f"DEBUG: Gefundene Ticket-ID: {actual_ticket_id}")
        print(f"DEBUG: Ticket-ID Typ: {type(actual_ticket_id).__name__}")

        # Teste verschiedene Update-Methoden
        results = {}

        # Methode 1: Direkte MongoDB-Operation
        try:
            result = mongodb.db.tickets.update_one(
                {'_id': actual_ticket_id},
                {'$set': {'test_field': 'test_value', 'updated_at': datetime.now()}}
            )
            results['direct_mongodb'] = {
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
                'success': result.modified_count > 0
            }
        except Exception as e:
            results['direct_mongodb'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        # Methode 2: Wrapper-Methode
        try:
            result = mongodb.update_one('tickets', {'_id': actual_ticket_id}, {'$set': {'test_field2': 'test_value2'}})
            results['wrapper_method'] = {
                'result': result,
                'result_type': type(result).__name__
            }
        except Exception as e:
            results['wrapper_method'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        # Methode 3: Mit verschiedenen ID-Formaten
        try:
            # Versuche mit String-ID
            string_result = mongodb.update_one('tickets', {'_id': str(actual_ticket_id)}, {'$set': {'test_field3': 'test_value3'}})
            results['string_id'] = {
                'result': string_result,
                'result_type': type(string_result).__name__
            }
        except Exception as e:
            results['string_id'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        return jsonify({
            'ticket_id': ticket_id,
            'actual_ticket_id': str(actual_ticket_id),
            'actual_ticket_id_type': type(actual_ticket_id).__name__,
            'results': results
        })

    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/debug/analyze-ticket/<ticket_id>')
def analyze_ticket(ticket_id):
    """Analysiert ein Ticket ohne Authentifizierung (nur für Debugging)"""
    try:
        print(f"DEBUG: Analysiere Ticket-ID: {ticket_id}")

        # Teste verschiedene Suchmethoden
        results = {}

        # Methode 1: Direkte String-Suche
        ticket = mongodb.find_one('tickets', {'_id': ticket_id})
        results['string_search'] = {
            'found': ticket is not None,
            'title': ticket.get('title') if ticket else None,
            'id': str(ticket.get('_id')) if ticket else None,
            'id_type': type(ticket.get('_id')).__name__ if ticket else None
        }

        # Methode 2: ObjectId-Suche
        try:
            from bson import ObjectId
            obj_id = ObjectId(ticket_id)
            ticket = mongodb.find_one('tickets', {'_id': obj_id})
            results['objectid_search'] = {
                'found': ticket is not None,
                'title': ticket.get('title') if ticket else None,
                'id': str(ticket.get('_id')) if ticket else None,
                'id_type': type(ticket.get('_id')).__name__ if ticket else None
            }
        except Exception as e:
            results['objectid_search'] = {
                'found': False,
                'error': 'Ein interner Fehler ist aufgetreten.'
            }

        # Methode 3: Direkte MongoDB-Abfrage
        try:
            direct_ticket = mongodb.db.tickets.find_one({'_id': ticket_id})
            results['direct_mongodb_string'] = {
                'found': direct_ticket is not None,
                'title': direct_ticket.get('title') if direct_ticket else None,
                'id': str(direct_ticket.get('_id')) if direct_ticket else None,
                'id_type': type(direct_ticket.get('_id')).__name__ if direct_ticket else None
            }
        except Exception as e:
            results['direct_mongodb_string'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        # Methode 4: Direkte MongoDB-Abfrage mit ObjectId
        try:
            from bson import ObjectId
            obj_id = ObjectId(ticket_id)
            direct_ticket = mongodb.db.tickets.find_one({'_id': obj_id})
            results['direct_mongodb_objectid'] = {
                'found': direct_ticket is not None,
                'title': direct_ticket.get('title') if direct_ticket else None,
                'id': str(direct_ticket.get('_id')) if direct_ticket else None,
                'id_type': type(direct_ticket.get('_id')).__name__ if direct_ticket else None
            }
        except Exception as e:
            results['direct_mongodb_objectid'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        # Teste Update-Operationen
        update_results = {}

        # Finde das Ticket für Updates
        found_ticket = None
        found_id = None

        if results['string_search']['found']:
            found_ticket = mongodb.find_one('tickets', {'_id': ticket_id})
            found_id = ticket_id
        elif results['objectid_search']['found']:
            found_ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
            found_id = ObjectId(ticket_id)

        if found_ticket:
            # Teste Update mit String-ID
            try:
                result = mongodb.db.tickets.update_one(
                    {'_id': ticket_id},
                    {'$set': {'debug_test': 'string_update'}}
                )
                update_results['string_update'] = {
                    'matched_count': result.matched_count,
                    'modified_count': result.modified_count,
                    'success': result.modified_count > 0
                }
                # Entferne das Test-Feld
                mongodb.db.tickets.update_one(
                    {'_id': ticket_id},
                    {'$unset': {'debug_test': ''}}
                )
            except Exception as e:
                update_results['string_update'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

            # Teste Update mit ObjectId
            try:
                result = mongodb.db.tickets.update_one(
                    {'_id': ObjectId(ticket_id)},
                    {'$set': {'debug_test': 'objectid_update'}}
                )
                update_results['objectid_update'] = {
                    'matched_count': result.matched_count,
                    'modified_count': result.modified_count,
                    'success': result.modified_count > 0
                }
                # Entferne das Test-Feld
                mongodb.db.tickets.update_one(
                    {'_id': ObjectId(ticket_id)},
                    {'$unset': {'debug_test': ''}}
                )
            except Exception as e:
                update_results['objectid_update'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        return jsonify({
            'ticket_id': ticket_id,
            'search_results': results,
            'update_results': update_results
        })

    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/debug/unassigned-tickets')
@login_required
@permission_required('tickets', 'view')
def debug_unassigned_tickets():
    """Debug-Route um nicht zugewiesene Tickets anzuzeigen"""
    try:
        # Hole alle nicht zugewiesenen Tickets
        unassigned_tickets = mongodb.find('tickets', {
            '$and': [
                {
                    '$or': [
                        {'assigned_to': None},
                        {'assigned_to': ''},
                        {'assigned_to': {'$exists': False}}
                    ]
                },
                {'status': 'offen'},
                {'deleted': {'$ne': True}}
            ]
        })

        # Konvertiere zu Liste für bessere Darstellung
        tickets_list = list(unassigned_tickets)

        # Debug-Informationen
        debug_info = {
            'total_unassigned': len(tickets_list),
            'tickets': []
        }

        for ticket in tickets_list:
            debug_info['tickets'].append({
                'id': str(ticket.get('_id')),
                'title': ticket.get('title', 'No Title'),
                'status': ticket.get('status', 'No Status'),
                'assigned_to': ticket.get('assigned_to', 'None'),
                'created_by': ticket.get('created_by', 'Unknown'),
                'created_at': ticket.get('created_at', 'Unknown'),
                'deleted': ticket.get('deleted', False)
            })

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500