"""Ket noi MongoDB cho ung dung TechStore."""

from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "techstore"

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)


def get_db():
    """Lay database TechStore."""
    return client[DB_NAME]


def check_connection():
    """Kiem tra MongoDB co hoat dong hay khong."""
    try:
        client.admin.command("ping")
        return True, "Ket noi MongoDB thanh cong."
    except Exception as error:
        return False, f"Ket noi MongoDB that bai: {error}"
