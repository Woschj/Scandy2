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
        # OPTIMIERUNG: Erst sortieren und limitieren, dann Lookups durchführen
        pipeline = [
            {
                '$sort': {'lent_at': -1}
            },
            {
                '$limit': 50
            },
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
            }
        ]

        history = list(mongodb.aggregate('lendings', pipeline))

    except Exception as e:
        print(f"Fehler beim Laden der Historie: {e}")
        history = []

    return render_template('history.html', history=history)
