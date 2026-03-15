import time
from unittest.mock import patch, MagicMock
from app.services.lending_service import LendingService

# Simulate old implementation for benchmarking
class OldLendingService(LendingService):
    @staticmethod
    def validate_lending_consistency() -> tuple:
        from app.models.mongodb_database import mongodb

        issues = []
        tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
        for tool in tools:
            barcode = tool.get('barcode')
            status = tool.get('status')
            active_lending = mongodb.find_one('lendings', {
                'tool_barcode': barcode,
                'returned_at': None
            })
            if active_lending and status != 'ausgeliehen':
                pass
            elif not active_lending and status == 'ausgeliehen':
                pass

        # O(N) approach
        orphaned_lendings = list(mongodb.find('lendings', {
            'returned_at': None,
            'tool_barcode': {'$exists': True}
        }))

        for lending in orphaned_lendings:
            tool_barcode = lending.get('tool_barcode')
            tool = mongodb.find_one('tools', {'barcode': tool_barcode, 'deleted': {'$ne': True}})
            if not tool:
                pass
        return True, "Done", {}


def run_benchmark():
    num_tools = 500
    num_orphaned = 1000

    tools_data = [{'barcode': f'T{i}', 'status': 'verfügbar', 'deleted': False, 'name': f'Tool {i}'} for i in range(num_tools)]
    lendings_data = [{'tool_barcode': f'ORPHAN_{i}', 'returned_at': None, '_id': str(i)} for i in range(num_orphaned)]

    call_counts = {'find': 0, 'find_one': 0}

    def mock_find(collection, query):
        call_counts['find'] += 1
        if collection == 'tools':
            if '$in' in query.get('barcode', {}):
                barcodes = query['barcode']['$in']
                return [t for t in tools_data if t['barcode'] in barcodes]
            return tools_data
        elif collection == 'lendings':
            return lendings_data
        return []

    def mock_find_one(collection, query):
        call_counts['find_one'] += 1
        # Add artificial delay to simulate network latency
        time.sleep(0.0005)
        if collection == 'tools':
            barcode = query.get('barcode')
            for t in tools_data:
                if t['barcode'] == barcode:
                    return t
            return None
        elif collection == 'lendings':
            return None
        return None

    # Benchmark Old Implementation
    with patch('app.models.mongodb_database.mongodb.find', side_effect=mock_find), \
         patch('app.models.mongodb_database.mongodb.find_one', side_effect=mock_find_one):

        call_counts['find'] = 0
        call_counts['find_one'] = 0
        start = time.time()
        OldLendingService.validate_lending_consistency()
        end = time.time()
        old_time = end - start
        old_find_one = call_counts['find_one']

    # Benchmark New Implementation
    with patch('app.models.mongodb_database.mongodb.find', side_effect=mock_find), \
         patch('app.models.mongodb_database.mongodb.find_one', side_effect=mock_find_one):

        call_counts['find'] = 0
        call_counts['find_one'] = 0
        start = time.time()
        LendingService.validate_lending_consistency()
        end = time.time()
        new_time = end - start
        new_find_one = call_counts['find_one']

    print(f"Old approach (O(N) queries): {old_time:.4f}s with {old_find_one} find_one calls")
    print(f"New approach (O(1) queries): {new_time:.4f}s with {new_find_one} find_one calls")
    print(f"Speedup: {old_time/new_time:.2f}x")
    print(f"Query reduction: {old_find_one - new_find_one} fewer network roundtrips")

if __name__ == '__main__':
    run_benchmark()
