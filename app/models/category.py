"""Truy cap collection categories."""
from bson import ObjectId

from app.database.connection import get_db


def _coll():
    return get_db().categories


def list_all() -> list[dict]:
    return list(_coll().find().sort("name", 1))


def list_names() -> list[str]:
    return [c["name"] for c in list_all()]


def get(category_id) -> dict | None:
    return _coll().find_one({"_id": ObjectId(category_id)})


def create(name: str, description: str = "") -> ObjectId:
    return _coll().insert_one({"name": name, "description": description}).inserted_id


def update(category_id, name: str, description: str = "") -> None:
    """Doi ten danh muc thi phai doi theo o moi san pham dang dung ten cu.

    San pham luu category bang TEN chu khong bang id, nen neu chi sua o day
    thi cac san pham cu se tro vao mot danh muc khong con ton tai.
    Hoa don thi khong dong toi: item da chup ten danh muc tai thoi diem ban.
    """
    old = get(category_id)
    _coll().update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {"name": name, "description": description}},
    )
    if old and old["name"] != name:
        get_db().products.update_many(
            {"category": old["name"]}, {"$set": {"category": name}}
        )


def delete(category_id) -> None:
    _coll().delete_one({"_id": ObjectId(category_id)})


def name_exists(name: str, exclude_id=None) -> bool:
    query: dict = {"name": name}
    if exclude_id:
        query["_id"] = {"$ne": ObjectId(exclude_id)}
    return _coll().count_documents(query) > 0


def product_count(name: str) -> int:
    return get_db().products.count_documents({"category": name, "is_active": True})


def is_used(name: str) -> bool:
    """Danh muc dang duoc san pham nao su dung khong."""
    return product_count(name) > 0
