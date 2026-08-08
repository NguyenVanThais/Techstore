"""Ket noi MongoDB dung chung cho toan bo ung dung."""
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError

from app.config import MONGO_URI, DB_NAME

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[DB_NAME]


def check_connection() -> tuple[bool, str]:
    """Ping server. Goi luc khoi dong de bao loi som thay vi treo giao dien."""
    try:
        get_client().admin.command("ping")
        return True, "Kết nối MongoDB thành công."
    except ServerSelectionTimeoutError as exc:
        return False, f"Không kết nối được MongoDB:\n{exc}"


def ensure_indexes() -> None:
    db = get_db()
    db.products.create_index([("name", ASCENDING)])
    db.products.create_index([("category", ASCENDING)])
    db.products.create_index([("name_search", ASCENDING)])
    db.categories.create_index([("name", ASCENDING)], unique=True)
    db.orders.create_index([("order_code", ASCENDING)], unique=True)
    db.orders.create_index([("created_at", ASCENDING)])
    db.orders.create_index([("customer.phone", ASCENDING)])
    db.customers.create_index([("phone", ASCENDING)], unique=True)
    db.users.create_index([("username", ASCENDING)], unique=True)
    db.suppliers.create_index([("name", ASCENDING)], unique=True)
    db.purchases.create_index([("receipt_code", ASCENDING)], unique=True)
    db.purchases.create_index([("created_at", ASCENDING)])
    db.audit_logs.create_index([("created_at", ASCENDING)])
