"""Truy cap collection products.

Luu y: xoa san pham la XOA MEM (is_active=False) vi san pham co the
dang nam trong cac hoa don cu.
"""
import re
from datetime import datetime

from bson import ObjectId

from app.database.connection import get_db
from app.utils.text import search_key


def _coll():
    return get_db().products


def search(keyword: str = "", category: str = "",
           min_price: float | None = None,
           max_price: float | None = None) -> list[dict]:
    query: dict = {"is_active": True}

    if keyword:
        # re.escape: nguoi dung go "(" hay "[" la chuoi tim kiem, khong phai
        # cu phap regex -- khong escape thi Mongo nem OperationFailure.
        safe = re.escape(keyword)
        query["$or"] = [
            {"name": {"$regex": safe, "$options": "i"}},
            {"sku": {"$regex": safe, "$options": "i"}},
            # name_search luu san ban khong dau: go "dien thoai"
            # van tim ra "Điện thoại"
            {"name_search": {"$regex": re.escape(search_key(keyword))}},
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

    # san pham yeu thich noi len dau danh sach (favorite giam dan,
    # thieu truong thi Mongo xep sau True — dung y muon)
    return list(_coll().find(query).sort([("favorite", -1), ("name", 1)]))


def get(product_id) -> dict | None:
    return _coll().find_one({"_id": ObjectId(product_id)})


def create(data: dict) -> ObjectId:
    data.setdefault("is_active", True)
    data.setdefault("min_stock", 5)
    data.setdefault("cost", 0.0)       # gia von, cap nhat qua phieu nhap
    data.setdefault("favorite", False)
    data["name_search"] = search_key(data.get("name", ""))
    data["created_at"] = datetime.now()
    return _coll().insert_one(data).inserted_id


def update(product_id, data: dict) -> None:
    if "name" in data:
        data["name_search"] = search_key(data["name"])
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


def sku_exists(sku: str, exclude_id=None) -> bool:
    """SKU la ma tra cuu nhanh cua nhan vien, trung la mat y nghia."""
    query = {"sku": sku, "is_active": True}
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


def apply_purchase(product_id, quantity: int, unit_cost: float) -> bool:
    """Nhap hang tu phieu nhap: cong ton kho va tinh lai gia von.

    Gia von tinh theo BINH QUAN GIA QUYEN: (ton cu x von cu + nhap x gia nhap)
    / tong so luong — dot nhap gia cao khong lam loi nhuan cac don sau do
    nhay dung nhu kieu "lay gia nhap moi nhat". San pham chua co gia von
    (von = 0) thi lay thang gia nhap lan nay.
    Tra ve False neu san pham khong ton tai.
    """
    product = _coll().find_one({"_id": ObjectId(product_id)})
    if not product:
        return False

    old_stock = max(product.get("stock", 0), 0)
    old_cost = product.get("cost", 0) or 0
    if old_cost > 0 and old_stock > 0:
        new_cost = (old_stock * old_cost + quantity * unit_cost) / (
            old_stock + quantity)
    else:
        new_cost = unit_cost

    _coll().update_one(
        {"_id": ObjectId(product_id)},
        {"$inc": {"stock": quantity},
         "$set": {"cost": round(new_cost, 2), "updated_at": datetime.now()}},
    )
    return True


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
