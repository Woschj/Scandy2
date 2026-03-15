import time
import mongomock
from datetime import datetime, timedelta

# Create our own mock database logic with simulated latency
class MockMongo:
    def __init__(self, simulated_latency=0.005):
        self.client = mongomock.MongoClient()
        self.db = self.client.db
        self.simulated_latency = simulated_latency

    def find(self, collection, query, sort=None, limit=None):
        time.sleep(self.simulated_latency)
        res = self.db[collection].find(query)
        if sort:
            res = res.sort(sort)
        if limit:
            res = res.limit(limit)
        return list(res)

    def find_one(self, collection, query):
        time.sleep(self.simulated_latency)
        return self.db[collection].find_one(query)

    def aggregate(self, collection, pipeline):
        time.sleep(self.simulated_latency)
        return list(self.db[collection].aggregate(pipeline))

mongodb = MockMongo(simulated_latency=0.005) # 5ms roundtrip typical for db

def populate_mock_data():
    db = mongodb.db
    db.tools.delete_many({})
    db.workers.delete_many({})
    db.consumables.delete_many({})
    db.lendings.delete_many({})
    db.consumable_usages.delete_many({})

    tools = [{'barcode': f'T{i}', 'name': f'Tool {i}', 'status': 'verfügbar'} for i in range(100)]
    workers = [{'barcode': f'W{i}', 'firstname': f'First{i}', 'lastname': f'Last{i}'} for i in range(100)]
    consumables = [{'barcode': f'C{i}', 'name': f'Consumable {i}'} for i in range(100)]

    if tools: db.tools.insert_many(tools)
    if workers: db.workers.insert_many(workers)
    if consumables: db.consumables.insert_many(consumables)

    now = datetime.now()
    lendings = []
    usages = []
    for i in range(100): # 100 lendings, 100 usages
        t_idx = i % 100
        w_idx = (i + 5) % 100
        lendings.append({
            'tool_barcode': f'T{t_idx}',
            'worker_barcode': f'W{w_idx}',
            'lent_at': now - timedelta(days=i),
            'returned_at': None
        })
        usages.append({
            'consumable_barcode': f'C{t_idx}',
            'worker_barcode': f'W{w_idx}',
            'used_at': now - timedelta(days=i % 30),
            'quantity': -1
        })

    if lendings: db.lendings.insert_many(lendings)
    if usages: db.consumable_usages.insert_many(usages)

def run_unoptimized():
    current_lendings = []

    # Tools
    active_tool_lendings = mongodb.find('lendings', {'returned_at': None})
    for lending in active_tool_lendings:
        tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
        worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})

        if tool and worker:
            current_lendings.append({
                'item_name': tool['name'],
                'item_barcode': tool['barcode'],
                'worker_name': f"{worker['firstname']} {worker['lastname']}",
                'worker_barcode': worker['barcode'],
                'action_date': lending['lent_at'],
                'category': 'Werkzeug',
                'amount': None
            })

    # Consumables
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_consumable_usages = mongodb.find('consumable_usages', {
        'used_at': {'$gte': thirty_days_ago},
        'quantity': {'$lt': 0}
    })

    for usage in recent_consumable_usages:
        consumable = mongodb.find_one('consumables', {'barcode': usage['consumable_barcode']})
        worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})

        if consumable and worker:
            current_lendings.append({
                'item_name': consumable['name'],
                'item_barcode': consumable['barcode'],
                'worker_name': f"{worker['firstname']} {worker['lastname']}",
                'worker_barcode': worker['barcode'],
                'action_date': usage['used_at'],
                'category': 'Verbrauchsmaterial',
                'amount': usage['quantity']
            })
    return len(current_lendings)

def run_optimized():
    current_lendings = []

    # Tools
    pipeline = [
        {'$match': {'returned_at': None}},
        {'$lookup': {'from': 'tools', 'localField': 'tool_barcode', 'foreignField': 'barcode', 'as': 'tool'}},
        {'$lookup': {'from': 'workers', 'localField': 'worker_barcode', 'foreignField': 'barcode', 'as': 'worker'}},
        {'$unwind': {'path': '$tool', 'preserveNullAndEmptyArrays': False}},
        {'$unwind': {'path': '$worker', 'preserveNullAndEmptyArrays': False}}
    ]

    active_tool_lendings = list(mongodb.aggregate('lendings', pipeline))
    for item in active_tool_lendings:
        tool = item.get('tool', {})
        worker = item.get('worker', {})
        current_lendings.append({
            'item_name': tool.get('name'),
            'item_barcode': tool.get('barcode'),
            'worker_name': f"{worker.get('firstname', '')} {worker.get('lastname', '')}",
            'worker_barcode': worker.get('barcode'),
            'action_date': item.get('lent_at'),
            'category': 'Werkzeug',
            'amount': None
        })

    # Consumables
    thirty_days_ago = datetime.now() - timedelta(days=30)
    c_pipeline = [
        {'$match': {'used_at': {'$gte': thirty_days_ago}, 'quantity': {'$lt': 0}}},
        {'$lookup': {'from': 'consumables', 'localField': 'consumable_barcode', 'foreignField': 'barcode', 'as': 'consumable'}},
        {'$lookup': {'from': 'workers', 'localField': 'worker_barcode', 'foreignField': 'barcode', 'as': 'worker'}},
        {'$unwind': {'path': '$consumable', 'preserveNullAndEmptyArrays': False}},
        {'$unwind': {'path': '$worker', 'preserveNullAndEmptyArrays': False}}
    ]

    recent_consumable_usages = list(mongodb.aggregate('consumable_usages', c_pipeline))
    for item in recent_consumable_usages:
        consumable = item.get('consumable', {})
        worker = item.get('worker', {})
        current_lendings.append({
            'item_name': consumable.get('name'),
            'item_barcode': consumable.get('barcode'),
            'worker_name': f"{worker.get('firstname', '')} {worker.get('lastname', '')}",
            'worker_barcode': worker.get('barcode'),
            'action_date': item.get('used_at'),
            'category': 'Verbrauchsmaterial',
            'amount': item.get('quantity')
        })

    return len(current_lendings)

populate_mock_data()

start_time = time.time()
unopt_len = run_unoptimized()
unopt_time = time.time() - start_time
print(f"Unoptimized time: {unopt_time:.4f} seconds (Rows: {unopt_len})")

start_time = time.time()
opt_len = run_optimized()
opt_time = time.time() - start_time
print(f"Optimized time: {opt_time:.4f} seconds (Rows: {opt_len})")

print(f"Speedup: {unopt_time / opt_time:.2f}x")
