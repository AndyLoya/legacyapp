"""MongoDB connection for Task Manager.

Set MONGODB_URI in your environment or in a .env file (see .env.example).
Examples:
  - Local:    mongodb://localhost:27017/taskmanager
  - Atlas:    mongodb+srv://user:pass@cluster.mongodb.net/taskmanager
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from pymongo import MongoClient
from pymongo.database import Database
from bson import ObjectId

# Use MONGODB_URI from environment; include database name in the URL
# e.g. mongodb://localhost:27017/taskmanager or mongodb+srv://...
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/taskmanager")

_client = None
_db: Database = None


def get_db():
    """Return the MongoDB database. Call init_db() first (e.g. at app startup)."""
    global _db
    if _db is None:
        init_db()
    return _db


def init_db():
    """Initialize MongoDB client and database. Safe to call multiple times."""
    global _client, _db
    _client = MongoClient(MONGODB_URI)
    try:
        _db = _client.get_default_database()
    except AttributeError:
        _db = None
    if _db is None:
        _db = _client["taskmanager"]
    return _db


def close_db():
    """Close the MongoDB connection."""
    global _client
    if _client:
        _client.close()
        _client = None
