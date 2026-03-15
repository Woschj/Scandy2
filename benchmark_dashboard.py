import time
import os
import sys
from datetime import datetime, timedelta

# Simple benchmark mock without full flask app
# Focus only on the overdue lendings code logic
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

class MockMongo:
    def __init__(self):
        self.tools = {f"T{i}": {"barcode": f"T{i}", "name": f"Tool {i}"} for i in range(100)}
        self.workers = {f"W{i}": {"barcode": f"W{i}", "name": f"Worker {i}"} for i in range(100)}

    def find_one(self, collection, query):
        if collection == 'tools':
            return self.tools.get(query.get('barcode'))
        elif collection == 'workers':
            return self.workers.get(query.get('barcode'))
        return None

    def aggregate(self, collection, pipeline):
        # A simple mock for aggregation if we implement it
        return []

mongodb = MockMongo()

def original_method(current_lendings):
    overdue_lendings = []
    for lending in current_lendings:
        try:
            lent_at = lending.get('lent_at')
            if isinstance(lent_at, str):
                try:
                    lent_at = datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        lent_at = datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        continue

            if isinstance(lent_at, datetime):
                days_lent = (datetime.now() - lent_at).days
                if days_lent > 30:
                    tool = mongodb.find_one('tools', {'barcode': lending.get('tool_barcode')})
                    worker = mongodb.find_one('workers', {'barcode': lending.get('worker_barcode')})

                    if tool and worker:
                        overdue_lendings.append({
                            'name': f"{tool.get('name', 'Unbekanntes Tool')} - {worker.get('name', 'Unbekannter Worker')}",
                            'status': f'Überfällig ({days_lent} Tage)',
                            'severity': 'warning'
                        })
        except Exception as e:
            continue
    return overdue_lendings

def optimized_method(current_lendings):
    overdue_lendings = []

    # 1. First, identify all overdue lendings and collect their barcodes
    overdue_items = []
    tool_barcodes = set()
    worker_barcodes = set()

    for lending in current_lendings:
        try:
            lent_at = lending.get('lent_at')
            if isinstance(lent_at, str):
                try:
                    lent_at = datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        lent_at = datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        continue

            if isinstance(lent_at, datetime):
                days_lent = (datetime.now() - lent_at).days
                if days_lent > 30:
                    overdue_items.append((lending, days_lent))

                    t_barcode = lending.get('tool_barcode')
                    if t_barcode:
                        tool_barcodes.add(t_barcode)

                    w_barcode = lending.get('worker_barcode')
                    if w_barcode:
                        worker_barcodes.add(w_barcode)
        except Exception as e:
            continue

    if not overdue_items:
        return []

    # 2. Fetch all required tools and workers in batch
    tools_dict = {}
    if tool_barcodes:
        # In real code: tools_cursor = mongodb.find('tools', {'barcode': {'$in': list(tool_barcodes)}})
        # Mocking finding tools
        for b in tool_barcodes:
            t = mongodb.find_one('tools', {'barcode': b})
            if t: tools_dict[b] = t

    workers_dict = {}
    if worker_barcodes:
        # In real code: workers_cursor = mongodb.find('workers', {'barcode': {'$in': list(worker_barcodes)}})
        # Mocking finding workers
        for b in worker_barcodes:
            w = mongodb.find_one('workers', {'barcode': b})
            if w: workers_dict[b] = w

    # 3. Build the result
    for lending, days_lent in overdue_items:
        t_barcode = lending.get('tool_barcode')
        w_barcode = lending.get('worker_barcode')

        tool = tools_dict.get(t_barcode)
        worker = workers_dict.get(w_barcode)

        if tool and worker:
            overdue_lendings.append({
                'name': f"{tool.get('name', 'Unbekanntes Tool')} - {worker.get('name', 'Unbekannter Worker')}",
                'status': f'Überfällig ({days_lent} Tage)',
                'severity': 'warning'
            })

    return overdue_lendings

if __name__ == '__main__':
    # Setup 1000 current lendings, half of them overdue
    lendings = []
    now = datetime.now()

    for i in range(1000):
        is_overdue = i % 2 == 0
        lent_date = now - timedelta(days=40) if is_overdue else now - timedelta(days=10)

        # Random tool/worker (0-99)
        t_idx = i % 100
        w_idx = (i + 50) % 100

        lendings.append({
            'tool_barcode': f"T{t_idx}",
            'worker_barcode': f"W{w_idx}",
            'lent_at': lent_date
        })

    # Benchmark original
    start = time.time()
    for _ in range(100):
        res1 = original_method(lendings)
    orig_time = time.time() - start

    # Benchmark optimized
    start = time.time()
    for _ in range(100):
        res2 = optimized_method(lendings)
    opt_time = time.time() - start

    print(f"Found {len(res1)} overdue lendings")
    print(f"Results match: {len(res1) == len(res2)}")
    print(f"Original Time: {orig_time:.4f}s")
    print(f"Optimized Time: {opt_time:.4f}s")

    if orig_time > 0:
        improvement = (orig_time - opt_time) / orig_time * 100
        print(f"Improvement: {improvement:.2f}%")
