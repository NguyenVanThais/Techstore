"""Truy cap collection purchases (phieu nhap hang).

Moi phieu NHUNG san items (sku / ten / gia nhap tai thoi diem nhap) va ten
nha cung cap — giong cach hoa don nhung san pham: sua gia hay xoa nha cung
cap sau nay khong lam sai lich su nhap.
"""
import re
from datetime import datetime

from bson import ObjectId
from pymongo import ReturnDocument

from app.database.connection import get_db


def _coll():
    return get_db().purchases


def _counters():
    return get_db().counters


def next_receipt_code() -> str:
    """Dang PN20260710-0001, dem theo ngay bang $inc nguyen tu tren counters
    — cung ky thuat voi ma hoa don, khong bao gio trung.
    Khoa dem co tien to 'PN' rieng de khong giam chan bo dem ma hoa don."""
    key = f"PN{datetime.now():%Y%m%d}"
    doc = _counters().find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True,
    )
    return f"{key}-{doc['seq']:04d}"


def create(receipt_code: str, items: list[dict], supplier: dict,
           user: dict, note: str = "") -> ObjectId:
    doc = {
        "receipt_code": receipt_code,
        "items": items,
        "total": sum(item["subtotal"] for item in items),
        "supplier": supplier,          # {"name": ...} nhung tai thoi diem nhap
        "user": user,                  # ai lap phieu
        "note": note,
        "created_at": datetime.now(),  # datetime that de loc theo khoang ngay
    }
    return _coll().insert_one(doc).inserted_id


def get(purchase_id) -> dict | None:
    return _coll().find_one({"_id": ObjectId(purchase_id)})


def search(code: str = "", supplier: str = "",
           date_from: datetime | None = None,
           date_to: datetime | None = None) -> list[dict]:
    query: dict = {}
    if code:
        query["receipt_code"] = {"$regex": re.escape(code), "$options": "i"}
    if supplier:
        query["supplier.name"] = {"$regex": re.escape(supplier), "$options": "i"}

    date_filter = {}
    if date_from:
        date_filter["$gte"] = date_from
    if date_to:
        # bao tron ngay ket thuc, cung ly do voi tim hoa don
        date_filter["$lte"] = date_to.replace(
            hour=23, minute=59, second=59, microsecond=999999)
    if date_filter:
        query["created_at"] = date_filter

    return list(_coll().find(query).sort("created_at", -1))
