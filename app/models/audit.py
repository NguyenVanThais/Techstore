"""Truy cap collection audit_logs (nhat ky hoat dong).

Chi co hai thao tac: ghi mot dong va doc ra — nhat ky khong bao gio sua/xoa
tu trong app, do la ca y nghia cua no.
"""
import re
from datetime import datetime

from app.database.connection import get_db


def _coll():
    return get_db().audit_logs


def add(user: str, role: str, action: str, detail: str = "") -> None:
    _coll().insert_one({
        "user": user,
        "role": role,
        "action": action,
        "detail": detail,
        "created_at": datetime.now(),
    })


def recent(keyword: str = "", limit: int = 500) -> list[dict]:
    query: dict = {}
    if keyword:
        safe = re.escape(keyword)
        query["$or"] = [
            {"user": {"$regex": safe, "$options": "i"}},
            {"action": {"$regex": safe, "$options": "i"}},
            {"detail": {"$regex": safe, "$options": "i"}},
        ]
    return list(_coll().find(query).sort("created_at", -1).limit(limit))


def count() -> int:
    return _coll().count_documents({})
