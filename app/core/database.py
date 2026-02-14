"""
Database initialization and management module.

Handles MongoDB connection, index creation, and database utilities.
"""

import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


def normalize_database_ids():
    """
    Normalizes all IDs in the database to strings when the system starts.
    This prevents problems with mixed ID types after imports.

    Returns:
        int: Number of normalized IDs
    """
    try:
        from app.models.mongodb_database import mongodb

        collections_to_normalize = [
            'tickets', 'users', 'tools', 'consumables', 'workers',
            'ticket_messages', 'ticket_notes', 'auftrag_details',
            'auftrag_material', 'auftrag_arbeit'
        ]

        total_updated = 0

        for collection_name in collections_to_normalize:
            try:
                documents = mongodb.find(collection_name, {})
                updated_count = 0

                for doc in documents:
                    doc_id = doc.get('_id')

                    # Convert ObjectId to string if needed
                    if isinstance(doc_id, ObjectId):
                        string_id = str(doc_id)

                        # Create new document with string ID
                        new_doc = doc.copy()
                        new_doc['_id'] = string_id

                        # Delete old document and insert new one
                        mongodb.delete_one(collection_name, {'_id': doc_id})
                        mongodb.insert_one(collection_name, new_doc)

                        updated_count += 1

                if updated_count > 0:
                    logging.info(f"Collection {collection_name}: {updated_count} IDs normalized")
                total_updated += updated_count

            except Exception as e:
                logging.warning(f"Error normalizing IDs in collection {collection_name}: {str(e)}")

        if total_updated > 0:
            logging.info(f"ID normalization completed: {total_updated} IDs normalized across all collections")
        else:
            logging.info("ID normalization: All IDs are already normalized")

        return total_updated

    except Exception as e:
        logging.error(f"Error during ID normalization: {str(e)}")
        return 0


def init_database(app):
    """
    Initialize database connections and create indexes.

    Args:
        app: Flask application instance
    """
    try:
        from app.models.mongodb_models import create_mongodb_indexes
        with app.app_context():
            create_mongodb_indexes()
            logging.info("MongoDB indexes created")
    except Exception as e:
        logging.error(f"Error initializing MongoDB: {str(e)}")


def init_database_with_id_normalization(app, enable_normalization=False):
    """
    Initialize database with optional ID normalization.

    Args:
        app: Flask application instance
        enable_normalization: Whether to enable ID normalization
    """
    init_database(app)

    # ID normalization (opt-in feature)
    if enable_normalization:
        try:
            with app.app_context():
                normalize_database_ids()
                logging.info("Database IDs normalized")
        except Exception as e:
            logging.error(f"Error during ID normalization: {str(e)}")
    else:
        logging.info("ID normalization on startup is disabled (ENABLE_ID_NORMALIZATION_ON_START=false)")
