"""Truy cap collection customers.

Khach hang KHONG nhap tay: moi lan thanh toan co so dien thoai, app tu
tao moi hoac cap nhat khach do (upsert). So dien thoai la khoa nhan dien.
"""
import re
from datetime import datetime

from app.database.connection import get_db
from app.utils.text import search_key


def _coll():
    return get_db().customers


def upsert_on_checkout(name: str, phone: str, total: float) -> None:
    """Ghi nhan mot lan mua. Khach moi thi tao, khach cu thi cong don."""
    if not phone:
        return   # khach le khong de lai so dien thoai thi khong theo doi duoc
    now = datetime.now()
    _coll().update_one(
        {"phone": phone},
        {
            # ten lay theo lan mua gan nhat (khach co the sua chinh ta)
            "$set": {"name": name, "name_search": search_key(name),
                     "last_order_at": now},
            "$inc": {"visits": 1, "total_spent": total},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


def phone_exists(phone: str) -> bool:
    return _coll().count_documents({"phone": phone}) > 0


def create_manual(phone: str, name: str, email: str = "", address: str = "",
                  note: str = "", vip: bool = False) -> None:
    """Tao khach hang bang tay (khac upsert_on_checkout: khong co don nao
    di kem, visits/total_spent bat dau tu 0). Goi tu man Khach hang."""
    now = datetime.now()
    _coll().insert_one({
        "phone": phone,
        "name": name,
        "name_search": search_key(name),
        "email": email,
        "address": address,
        "note": note,
        "vip": vip,
        "visits": 0,
        "total_spent": 0.0,
        "created_at": now,
        "last_order_at": None,
    })


def rollback_order(phone: str, total: float) -> None:
    """Khi huy don: tru lai luot mua va tong chi tieu cho dung thuc te."""
    if not phone:
        return
    _coll().update_one({"phone": phone},
                       {"$inc": {"visits": -1, "total_spent": -total}})


def refund(phone: str, amount: float) -> None:
    """Khach tra lai hang: tru phan tien hoan vao tong chi tieu.
    Khac voi rollback_order, so lan mua giu nguyen (don van ton tai)."""
    if not phone:
        return
    _coll().update_one({"phone": phone}, {"$inc": {"total_spent": -amount}})


def update_info(phone: str, data: dict) -> None:
    """Sua thong tin lien he / VIP. Chi nhan cac truong cho phep de
    khong ai ghi de duoc visits hay total_spent tu form."""
    allowed = {k: data[k] for k in ("name", "email", "address", "note", "vip")
               if k in data}
    if "name" in allowed:
        allowed["name_search"] = search_key(allowed["name"])
    if not allowed:
        return
    _coll().update_one({"phone": phone}, {"$set": allowed})


def search(keyword: str = "") -> list[dict]:
    query: dict = {}
    if keyword:
        safe = re.escape(keyword)
        skey = re.escape(search_key(keyword))
        query["$or"] = [
            {"name": {"$regex": safe, "$options": "i"}},
            {"phone": {"$regex": safe}},
            # name_search: go 'nguyen van' khong dau van tim ra 'Nguyễn Văn'
            {"name_search": {"$regex": skey}},
        ]
    return list(_coll().find(query).sort("last_order_at", -1))


def get_by_phone(phone: str) -> dict | None:
    if not phone:
        return None
    return _coll().find_one({"phone": phone})


def top_spenders(limit: int = 5) -> list[dict]:
    return list(_coll().find({"total_spent": {"$gt": 0}})
                .sort("total_spent", -1).limit(limit))


def count() -> int:
    return _coll().count_documents({})
