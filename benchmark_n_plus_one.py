import time
from unittest.mock import MagicMock
from datetime import datetime

class MockMongoDB:
    def __init__(self, num_lendings=100):
        self.num_lendings = num_lendings
        self.find_one_calls = 0
        self.find_calls = 0

    def find_one(self, collection, query):
        self.find_one_calls += 1
        # Simulate some network delay
        time.sleep(0.001)
        if collection == 'tools':
            return {'barcode': query.get('barcode'), 'name': 'Test Tool'}
        if collection == 'workers':
            return {'barcode': query.get('barcode'), 'name': 'Test Worker'}

    def find(self, collection, query, **kwargs):
        self.find_calls += 1
        # Simulate some network delay
        time.sleep(0.001)
        if collection == 'lendings':
            return [{'tool_barcode': f'T{i}', 'worker_barcode': f'W{i}', 'lent_at': datetime.now()} for i in range(self.num_lendings)]
        if collection == 'tools':
            barcodes = query.get('barcode', {}).get('$in', [])
            return [{'barcode': b, 'name': 'Test Tool'} for b in barcodes]
        if collection == 'workers':
            barcodes = query.get('barcode', {}).get('$in', [])
            return [{'barcode': b, 'name': 'Test Worker'} for b in barcodes]
        return []

def run_original(mongodb):
    current_lendings = list(mongodb.find('lendings', {'returned_at': {'$exists': False}}))
    processed_lendings = []

    start = time.time()
    for lending in current_lendings:
        tool = mongodb.find_one('tools', {'barcode': lending.get('tool_barcode', '')})
        worker = mongodb.find_one('workers', {'barcode': lending.get('worker_barcode', '')})

        if tool and worker:
            lent_at = lending.get('lent_at')
            processed_lendings.append({
                'tool_name': tool.get('name', 'Unbekanntes Tool'),
                'worker_name': worker.get('name', 'Unbekannter Worker'),
                'lent_at': lent_at,
                'days_lent': 0
            })
    end = time.time()
    return end - start

def run_optimized(mongodb):
    current_lendings = list(mongodb.find('lendings', {'returned_at': {'$exists': False}}))
    processed_lendings = []

    start = time.time()

    tool_barcodes = {l.get('tool_barcode') for l in current_lendings if l.get('tool_barcode')}
    worker_barcodes = {l.get('worker_barcode') for l in current_lendings if l.get('worker_barcode')}

    tools_cache = {}
    if tool_barcodes:
        tools = mongodb.find('tools', {'barcode': {'$in': list(tool_barcodes)}})
        tools_cache = {t.get('barcode'): t for t in tools}

    workers_cache = {}
    if worker_barcodes:
        workers = mongodb.find('workers', {'barcode': {'$in': list(worker_barcodes)}})
        workers_cache = {w.get('barcode'): w for w in workers}

    for lending in current_lendings:
        tool = tools_cache.get(lending.get('tool_barcode', ''))
        worker = workers_cache.get(lending.get('worker_barcode', ''))

        if tool and worker:
            lent_at = lending.get('lent_at')
            processed_lendings.append({
                'tool_name': tool.get('name', 'Unbekanntes Tool'),
                'worker_name': worker.get('name', 'Unbekannter Worker'),
                'lent_at': lent_at,
                'days_lent': 0
            })
    end = time.time()
    return end - start

if __name__ == '__main__':
    print("Running with 100 lendings...")

    db1 = MockMongoDB(100)
    time1 = run_original(db1)
    print(f"Original: {time1:.4f}s ({db1.find_one_calls} find_one calls)")

    db2 = MockMongoDB(100)
    time2 = run_optimized(db2)
    print(f"Optimized: {time2:.4f}s ({db2.find_one_calls} find_one calls, {db2.find_calls-1} extra find calls)")
    print(f"Improvement: {time1/time2:.2f}x faster")
