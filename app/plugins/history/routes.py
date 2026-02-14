from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBLending
from app.models.mongodb_database import MongoDB

bp = Blueprint('history', __name__)
mongodb = MongoDB()

@bp.route('/history')
def history():
    """Zeigt die Historie der Ausleihen an"""
    try:
        # Hole die letzten 50 Ausleihen mit Details
        pipeline = [
            {
                '$lookup': {
                    'from': 'tools',
                    'localField': 'tool_barcode',
                    'foreignField': 'barcode',
                    'as': 'tool'
                }
            },
            {
                '$lookup': {
                    'from': 'workers',
                    'localField': 'worker_barcode',
                    'foreignField': 'barcode',
                    'as': 'worker'
                }
            },
            {
                '$unwind': '$tool'
            },
            {
                '$unwind': '$worker'
            },
            {
                '$project': {
                    'id': '$_id',
                    'lent_at': 1,
                    'returned_at': 1,
                    'tool_name': '$tool.name',
                    'tool_barcode': '$tool.barcode',
                    'worker_name': {'$concat': ['$worker.firstname', ' ', '$worker.lastname']},
                    'worker_barcode': '$worker.barcode'
                }
            },
            {
                '$sort': {'lent_at': -1}
            },
            {
                '$limit': 50
            }
        ]
        
        history_data = list(mongodb.aggregate('lendings', pipeline))
        
        # Konvertiere MongoDB-Objekte in das erwartete Format
        history = []
        for item in history_data:
            history.append({
                'id': str(item['id']),
                'lent_at': item['lent_at'],
                'returned_at': item.get('returned_at'),
                'tool_name': item['tool_name'],
                'tool_barcode': item['tool_barcode'],
                'worker_name': item['worker_name'],
                'worker_barcode': item['worker_barcode']
            })
            
    except Exception as e:
        print(f"Fehler beim Laden der Historie: {e}")
        history = []
            
    return render_template('history.html', history=history) 