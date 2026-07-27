"""Truy cap collection suppliers (nha cung cap).

Phieu nhap NHUNG ten nha cung cap tai thoi diem nhap (giong hoa don nhung
ten san pham), nen sua / xoa nha cung cap khong lam sai lich su nhap cu.
"""
import re
from datetime import datetime

from bson import ObjectId

from app.database.connection import get_db
from app.utils.text import search_key


def _coll():
    return get_db().suppliers


def list_all(keyword: str = "") -> list[dict]:
    query: dict = {}
    if keyword:
        safe = re.escape(keyword)
        query["$or"] = [
            {"name": {"$regex": safe, "$options": "i"}},
            {"phone": {"$regex": safe}},
            {"name_search": {"$regex": re.escape(search_key(keyword))}},
        ]
    return list(_coll().find(query).sort("name", 1))


def list_names() -> list[str]:
    return [s["name"] for s in _coll().find({}, {"name": 1}).sort("name", 1)]


def get(supplier_id) -> dict | None:
    return _coll().find_one({"_id": ObjectId(supplier_id)})


def create(data: dict) -> ObjectId:
    data["name_search"] = search_key(data.get("name", ""))
    data["created_at"] = datetime.now()
    return _coll().insert_one(data).inserted_id


def update(supplier_id, data: dict) -> None:
    if "name" in data:
        data["name_search"] = search_key(data["name"])
    data["updated_at"] = datetime.now()
    _coll().update_one({"_id": ObjectId(supplier_id)}, {"$set": data})


def delete(supplier_id) -> None:
    _coll().delete_one({"_id": ObjectId(supplier_id)})


def name_exists(name: str, exclude_id=None) -> bool:
    query: dict = {"name": name}
    if exclude_id:
        query["_id"] = {"$ne": ObjectId(exclude_id)}
    return _coll().count_documents(query) > 0


def purchase_stats(name: str) -> dict:
    """So lan nhap va tong tien da nhap tu nha cung cap nay
    (dem theo TEN da nhung trong phieu, khop voi cach luu phieu)."""
    rows = list(get_db().purchases.aggregate([
        {"$match": {"supplier.name": name}},
        {"$group": {"_id": None, "count": {"$sum": 1},
                    "total": {"$sum": "$total"}}},
    ]))
    if not rows:
        return {"count": 0, "total": 0}
    return {"count": rows[0]["count"], "total": rows[0]["total"]}
