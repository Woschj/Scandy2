import pytest
from datetime import datetime
import mongomock

def test_history_pipeline_logic():
    # Setup mock DB
    client = mongomock.MongoClient()
    db = client.scandy

    # Insert sample data
    db.tools.insert_one({'barcode': 'T1', 'name': 'Hammer'})
    db.workers.insert_one({'barcode': 'W1', 'firstname': 'John', 'lastname': 'Doe'})
    db.lendings.insert_one({
        'tool_barcode': 'T1',
        'worker_barcode': 'W1',
        'lent_at': datetime(2023, 1, 1),
        'returned_at': None
    })

    # This is the optimized pipeline from routes.py
    pipeline = [
        {'$sort': {'lent_at': -1}},
        {'$limit': 50},
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
            '$unwind': {
                'path': '$tool',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$unwind': {
                'path': '$worker',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$project': {
                'id': '$_id',
                'lent_at': 1,
                'returned_at': 1,
                'tool_name': {'$ifNull': ['$tool.name', 'Unbekanntes Werkzeug']},
                'tool_barcode': {'$ifNull': ['$tool.barcode', '$tool_barcode']},
                'worker_name': {
                    '$cond': {
                        'if': {'$and': [{'$gt': ['$worker.firstname', None]}, {'$gt': ['$worker.lastname', None]}]},
                        'then': {'$concat': ['$worker.firstname', ' ', '$worker.lastname']},
                        'else': 'Unbekannter Mitarbeiter'
                    }
                },
                'worker_barcode': {'$ifNull': ['$worker.barcode', '$worker_barcode']}
            }
        }
    ]

    results = list(db.lendings.aggregate(pipeline))

    assert len(results) == 1
    assert results[0]['tool_name'] == 'Hammer'
    assert results[0]['worker_name'] == 'John Doe'
    assert results[0]['tool_barcode'] == 'T1'

def test_history_pipeline_missing_joins():
    # Setup mock DB
    client = mongomock.MongoClient()
    db = client.scandy

    # Insert lending without matching tool/worker
    db.lendings.insert_one({
        'tool_barcode': 'MISSING_T',
        'worker_barcode': 'MISSING_W',
        'lent_at': datetime(2023, 1, 1),
        'returned_at': None
    })

    # Optimized pipeline
    pipeline = [
        {'$sort': {'lent_at': -1}},
        {'$limit': 50},
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
            '$unwind': {
                'path': '$tool',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$unwind': {
                'path': '$worker',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$project': {
                'id': '$_id',
                'lent_at': 1,
                'returned_at': 1,
                'tool_name': {'$ifNull': ['$tool.name', 'Unbekanntes Werkzeug']},
                'tool_barcode': {'$ifNull': ['$tool.barcode', '$tool_barcode']},
                'worker_name': {
                    '$cond': {
                        'if': {'$and': [{'$gt': ['$worker.firstname', None]}, {'$gt': ['$worker.lastname', None]}]},
                        'then': {'$concat': ['$worker.firstname', ' ', '$worker.lastname']},
                        'else': 'Unbekannter Mitarbeiter'
                    }
                },
                'worker_barcode': {'$ifNull': ['$worker.barcode', '$worker_barcode']}
            }
        }
    ]

    results = list(db.lendings.aggregate(pipeline))

    assert len(results) == 1
    assert results[0]['tool_name'] == 'Unbekanntes Werkzeug'
    assert results[0]['worker_name'] == 'Unbekannter Mitarbeiter'
    assert results[0]['tool_barcode'] == 'MISSING_T'
    assert results[0]['worker_barcode'] == 'MISSING_W'

if __name__ == '__main__':
    test_history_pipeline_logic()
    test_history_pipeline_missing_joins()
    print("Pipeline tests passed!")
