"""Truy cap collection products.

Luu y: xoa san pham la XOA MEM (is_active=False) vi san pham co the
dang nam trong cac hoa don cu.
"""
from datetime import datetime

from bson import ObjectId

from app.database.connection import get_db


def _coll():
    return get_db().products


def search(keyword: str = "", category: str = "",
           min_price: float | None = None,
           max_price: float | None = None) -> list[dict]:
    query: dict = {"is_active": True}

    if keyword:
        query["$or"] = [
            {"name": {"$regex": keyword, "$options": "i"}},
            {"sku": {"$regex": keyword, "$options": "i"}},
        ]
    if category:
        query["category"] = category

    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        query["price"] = price_filter

    return list(_coll().find(query).sort("name", 1))


def get(product_id) -> dict | None:
    return _coll().find_one({"_id": ObjectId(product_id)})


def create(data: dict) -> ObjectId:
    data.setdefault("is_active", True)
    data.setdefault("min_stock", 5)
    data["created_at"] = datetime.now()
    return _coll().insert_one(data).inserted_id


def update(product_id, data: dict) -> None:
    data["updated_at"] = datetime.now()
    _coll().update_one({"_id": ObjectId(product_id)}, {"$set": data})


def soft_delete(product_id) -> None:
    _coll().update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"is_active": False, "deleted_at": datetime.now()}},
    )


def name_exists(name: str, exclude_id=None) -> bool:
    query = {"name": name, "is_active": True}
    if exclude_id:
        query["_id"] = {"$ne": ObjectId(exclude_id)}
    return _coll().count_documents(query) > 0


# ---------- Ton kho ----------

def low_stock() -> list[dict]:
    """San pham co ton kho <= muc toi thieu.

    Phai dung $expr vi day la so sanh giua hai truong voi nhau,
    khong phai so sanh truong voi hang so.
    """
    return list(
        _coll()
        .find({"is_active": True, "$expr": {"$lte": ["$stock", "$min_stock"]}})
        .sort("stock", 1)
    )


def low_stock_count() -> int:
    return _coll().count_documents(
        {"is_active": True, "$expr": {"$lte": ["$stock", "$min_stock"]}}
    )


def restock(product_id, quantity: int) -> None:
    _coll().update_one(
        {"_id": ObjectId(product_id)},
        {"$inc": {"stock": quantity}, "$set": {"updated_at": datetime.now()}},
    )


def decrease_stock(product_id, quantity: int) -> bool:
    """Tru ton kho mot cach an toan.

    Dieu kien stock >= quantity nam ngay trong filter, nen neu hai nhan vien
    cung ban san pham cuoi cung thi chi mot nguoi thanh cong.
    is_active cung nam trong filter de khong ban duoc san pham vua bi xoa
    trong luc no dang nam trong gio hang.
    Tra ve False neu khong du hang hoac san pham da ngung ban.
    """
    result = _coll().find_one_and_update(
        {"_id": ObjectId(product_id), "is_active": True,
         "stock": {"$gte": quantity}},
        {"$inc": {"stock": -quantity}},
    )
    return result is not None


def increase_stock(product_id, quantity: int) -> None:
    """Hoan tac khi tao don that bai giua chung."""
    _coll().update_one({"_id": ObjectId(product_id)}, {"$inc": {"stock": quantity}})
