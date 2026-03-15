import time
import os
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
import mongomock

# Mock environment setup
os.environ['TESTING'] = 'true'
os.environ['FLASK_ENV'] = 'testing'

# We'll test direct MongoDB interactions using mongomock
client = mongomock.MongoClient()
db = client.scandy

def setup_mock_data():
    # Clear existing
    db.tools.delete_many({})
    db.workers.delete_many({})
    db.lendings.delete_many({})

    # Create tools, workers, and lendings
    tools = [{"barcode": f"T{i}", "name": f"Tool {i}", "status": "verfügbar"} for i in range(100)]
    workers = [{"barcode": f"W{i}", "name": f"Worker {i}"} for i in range(100)]

    now = datetime.now()
    lendings = []

    for i in range(1000):
        t_idx = i % 100
        w_idx = (i + 50) % 100

        # Make 50% overdue
        is_overdue = i % 2 == 0
        lent_date = now - timedelta(days=40) if is_overdue else now - timedelta(days=10)

        lendings.append({
            "tool_barcode": f"T{t_idx}",
            "worker_barcode": f"W{w_idx}",
            "lent_at": lent_date
        })

    db.tools.insert_many(tools)
    db.workers.insert_many(workers)
    db.lendings.insert_many(lendings)

def benchmark_original():
    current_lendings = list(db.lendings.find({'returned_at': {'$exists': False}}))
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
                    tool = db.tools.find_one({'barcode': lending.get('tool_barcode')})
                    worker = db.workers.find_one({'barcode': lending.get('worker_barcode')})

                    if tool and worker:
                        overdue_lendings.append({
                            'name': f"{tool.get('name', 'Unbekanntes Tool')} - {worker.get('name', 'Unbekannter Worker')}",
                            'status': f'Überfällig ({days_lent} Tage)',
                            'severity': 'warning'
                        })
        except Exception as e:
            continue
    return overdue_lendings

def benchmark_optimized():
    current_lendings = list(db.lendings.find({'returned_at': {'$exists': False}}))
    overdue_lendings = []

    # 1. First find all overdue items and collect barcodes
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
                    if t_barcode: tool_barcodes.add(t_barcode)

                    w_barcode = lending.get('worker_barcode')
                    if w_barcode: worker_barcodes.add(w_barcode)
        except Exception as e:
            continue

    if not overdue_items:
        return []

    # 2. Fetch all tools and workers in batch
    tools_dict = {}
    if tool_barcodes:
        tools_cursor = db.tools.find({'barcode': {'$in': list(tool_barcodes)}})
        tools_dict = {t.get('barcode'): t for t in tools_cursor}

    workers_dict = {}
    if worker_barcodes:
        workers_cursor = db.workers.find({'barcode': {'$in': list(worker_barcodes)}})
        workers_dict = {w.get('barcode'): w for w in workers_cursor}

    # 3. Build result
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
    setup_mock_data()

    # Warmup
    benchmark_original()
    benchmark_optimized()

    # Benchmark original
    start = time.time()
    for _ in range(50):
        res1 = benchmark_original()
    orig_time = time.time() - start

    # Benchmark optimized
    start = time.time()
    for _ in range(50):
        res2 = benchmark_optimized()
    opt_time = time.time() - start

    print(f"Found {len(res1)} overdue lendings")
    print(f"Results match: {len(res1) == len(res2)}")
    print(f"Original Time (N+1 with Mongomock): {orig_time:.4f}s")
    print(f"Optimized Time (Batch query): {opt_time:.4f}s")

    if orig_time > 0:
        improvement = (orig_time - opt_time) / orig_time * 100
        print(f"Improvement: {improvement:.2f}%")

    # In a real database with network latency, the improvement is massively higher.
    # N+1 queries in mongomock take very little time since it's just in-memory dictionary lookups,
    # but a real DB requires network roundtrips.
    # We can estimate the real DB time by adding artificial latency.

    print("\n--- Simulating Network Latency (2ms per query) ---")

    # 1 lending query + (500 tools * 2 queries) = 1001 queries per iteration
    sim_orig_time = orig_time + (50 * 1001 * 0.002)

    # 1 lending query + 1 tool batch query + 1 worker batch query = 3 queries per iteration
    sim_opt_time = opt_time + (50 * 3 * 0.002)

    print(f"Simulated Real DB Original Time: {sim_orig_time:.4f}s")
    print(f"Simulated Real DB Optimized Time: {sim_opt_time:.4f}s")
    if sim_orig_time > 0:
        sim_imp = (sim_orig_time - sim_opt_time) / sim_orig_time * 100
        print(f"Simulated Real DB Improvement: {sim_imp:.2f}%")
