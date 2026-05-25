import time
import mongomock

# Setup mock database
client = mongomock.MongoClient()
db = client.test_db
settings_collection = db.settings

# Populate data
print("Populating data...")
docs = []
for i in range(10000):
    docs.append({"key": f"other_setting_{i}", "value": f"value_{i}"})
for i in range(100):
    docs.append({"key": f"email_setting_{i}", "value": f"value_{i}"})
settings_collection.insert_many(docs)

def original_method():
    settings = {}
    rows = settings_collection.find({})
    for row in rows:
        if row['key'].startswith('email_'):
            settings[row['key']] = row['value']
    return settings

def optimized_method():
    settings = {}
    rows = settings_collection.find({'key': {'$regex': '^email_'}})
    for row in rows:
        settings[row['key']] = row['value']
    return settings

print("Running baseline...")
start = time.time()
for _ in range(1000):
    original_method()
baseline_time = time.time() - start

print("Running optimized...")
start = time.time()
for _ in range(1000):
    optimized_method()
optimized_time = time.time() - start

print(f"Baseline Time: {baseline_time:.4f}s")
print(f"Optimized Time: {optimized_time:.4f}s")
if baseline_time > 0:
    print(f"Improvement: {((baseline_time - optimized_time) / baseline_time) * 100:.2f}%")
