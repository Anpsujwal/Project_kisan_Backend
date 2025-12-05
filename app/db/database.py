import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI","mongodb+srv://anpsujwal:aE4CEwJzAOGC98N7@cluster0.k5xrdmr.mongodb.net/project_kisan?retryWrites=true&w=majority")
DB_NAME = os.getenv("DB_NAME","project_kisan")

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[DB_NAME]


def users_col():
    return get_db()["users"]


def chats_col():
    return get_db()["chats"]


def memories_col():
    return get_db()["memories"]
