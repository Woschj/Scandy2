import time
from unittest.mock import MagicMock

class MockMongo:
    def __init__(self):
        self.find_calls = 0
        self.find_one_calls = 0

    def find(self, collection, query, **kwargs):
        self.find_calls += 1
        if collection == 'lendings':
            return [{'tool_barcode': f'T{i}', 'worker_barcode': f'W{i}'} for i in range(10000)]
        elif collection == 'tools':
            return [{'barcode': f'T{i}', 'name': f'Tool {i}'} for i in range(10000)]
        elif collection == 'workers':
            return [{'barcode': f'W{i}', 'firstname': 'F', 'lastname': 'L'} for i in range(10000)]
        return []

    def find_one(self, collection, query):
        self.find_one_calls += 1
        # Simulate network latency
        time.sleep(0.001)
        if collection == 'tools':
            return {'barcode': query['barcode'], 'name': 'Tool'}
        elif collection == 'workers':
            return {'barcode': query['barcode'], 'firstname': 'F', 'lastname': 'L'}
        return None

def run_benchmark():
    import app.services.excel_export_service as mod

    mock_mongo = MockMongo()
    mod.mongodb = mock_mongo

    service = mod.ExcelExportService()
    import openpyxl
    service.workbook = openpyxl.Workbook()

    start_time = time.time()
    service._create_lendings_sheet()
    end_time = time.time()

    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"find() calls: {mock_mongo.find_calls}")
    print(f"find_one() calls: {mock_mongo.find_one_calls}")

if __name__ == '__main__':
    run_benchmark()
