import pytest
from unittest.mock import patch
from app.services.consumable_service import ConsumableService
import mongomock

class TestConsumableServiceStats:
    @pytest.fixture
    def mock_db(self):
        client = mongomock.MongoClient()
        db = client.scandy
        return db

    def test_get_statistics_empty(self, mock_db):
        """Testet Statistiken bei leerer Datenbank"""
        with patch('app.services.consumable_service.mongodb') as mock_mongodb:
            # Simuliere das Verhalten von mongodb.aggregate
            mock_mongodb.aggregate.side_effect = lambda coll, pipe: list(mock_db[coll].aggregate(pipe))

            stats = ConsumableService.get_statistics()

            assert stats['total_consumables'] == 0
            assert stats['categories'] == {}
            assert stats['locations'] == {}
            assert stats['stock_levels'] == {
                'sufficient': 0,
                'warning': 0,
                'critical': 0
            }

    def test_get_statistics_with_data(self, mock_db):
        """Testet Statistiken mit verschiedenen Testdaten"""
        # Testdaten einfügen
        mock_db.consumables.insert_many([
            {'name': 'C1', 'category': 'Cat1', 'location': 'Loc1', 'quantity': 10, 'min_quantity': 5, 'deleted': False},
            {'name': 'C2', 'category': 'Cat1', 'location': 'Loc2', 'quantity': 3, 'min_quantity': 5, 'deleted': False},
            {'name': 'C3', 'category': 'Cat2', 'location': 'Loc1', 'quantity': 0, 'min_quantity': 5, 'deleted': False},
            {'name': 'C4', 'category': 'Cat2', 'location': 'Loc2', 'quantity': 10, 'min_quantity': 5, 'deleted': True}, # Gelöscht, sollte ignoriert werden
        ])

        with patch('app.services.consumable_service.mongodb') as mock_mongodb:
            mock_mongodb.aggregate.side_effect = lambda coll, pipe: list(mock_db[coll].aggregate(pipe))

            stats = ConsumableService.get_statistics()

            assert stats['total_consumables'] == 3
            assert stats['categories'] == {'Cat1': 2, 'Cat2': 1}
            assert stats['locations'] == {'Loc1': 2, 'Loc2': 1}
            assert stats['stock_levels'] == {
                'sufficient': 1, # C1: 10 >= 5
                'warning': 1,    # C2: 3 < 5 und > 0
                'critical': 1    # C3: 0
            }

    def test_get_statistics_missing_fields(self, mock_db):
        """Testet Statistiken bei fehlenden Feldern (Kategorie/Standort)"""
        # Daten mit fehlenden Feldern
        mock_db.consumables.insert_many([
            {'name': 'C1', 'quantity': 10, 'min_quantity': 5, 'deleted': False},
        ])

        with patch('app.services.consumable_service.mongodb') as mock_mongodb:
            mock_mongodb.aggregate.side_effect = lambda coll, pipe: list(mock_db[coll].aggregate(pipe))

            stats = ConsumableService.get_statistics()

            assert stats['total_consumables'] == 1
            assert stats['categories'] == {'Keine Kategorie': 1}
            assert stats['locations'] == {'Kein Standort': 1}
            assert stats['stock_levels']['sufficient'] == 1
