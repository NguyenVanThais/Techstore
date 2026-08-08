"""Truy cap collection users (tai khoan dang nhap)."""
from datetime import datetime

from app.database.connection import get_db


def _coll():
    return get_db().users


def get_by_username(username: str) -> dict | None:
    return _coll().find_one({"username": username})


def create(data: dict):
    data["created_at"] = datetime.now()
    return _coll().insert_one(data).inserted_id


def count() -> int:
    return _coll().count_documents({})


def list_all() -> list[dict]:
    return list(_coll().find().sort("username", 1))
