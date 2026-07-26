"""Truy cap collection orders.

Moi don hang NHUNG san mang items, trong do moi item da copy san
name / category / price tai thoi diem ban. Nho vay:
  - sua gia san pham sau nay khong lam sai doanh thu cu
  - thong ke theo loai san pham khong can $lookup
"""
import re
from datetime import datetime

from bson import ObjectId
from pymongo import ReturnDocument

from app.database.connection import get_db


def _coll():
    return get_db().orders


def _counters():
    return get_db().counters


def _init_counter(key: str) -> None:
    """Khoi tao bo dem tu ma don lon nhat da co trong ngay.

    Can thiet cho du lieu tao truoc khi co collection counters (vi du seed_data),
    neu khong bo dem se bat dau lai tu 0 va sinh ma trung.
    """
    if _counters().count_documents({"_id": key}) > 0:
        return

    last = list(
        _coll().find({"order_code": {"$regex": f"^HD{key}-"}})
        .sort("order_code", -1).limit(1)
    )
    start = int(last[0]["order_code"].split("-")[1]) if last else 0
    _counters().update_one({"_id": key}, {"$setOnInsert": {"seq": start}}, upsert=True)


def next_order_code() -> str:
    """Dang HD20260709-0001, dem theo tung ngay.

    Dung $inc tren collection counters chu KHONG dem so don trong ngay:
    dem thi hai nhan vien ban cung luc se ra cung mot ma, va xoa mot don cu
    cung lam ma tiep theo dam vao ma da ton tai. find_one_and_update la thao
    tac nguyen tu nen moi lan goi chac chan ra mot so khac nhau.
    """
    key = f"{datetime.now():%Y%m%d}"
    _init_counter(key)

    doc = _counters().find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True,
    )
    return f"HD{key}-{doc['seq']:04d}"


def create(order_code: str, items: list[dict], customer: dict,
           discount: float = 0.0) -> ObjectId:
    subtotal = sum(item["subtotal"] for item in items)
    total = subtotal - discount

    doc = {
        "order_code": order_code,
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "customer": customer,
        "status": "completed",   # "cancelled" khi bi huy; thong ke bo qua don huy
        # BAT BUOC la datetime, khong phai chuoi -- toan bo phan thong ke
        # dua vao $dateToString tren truong nay.
        "created_at": datetime.now(),
    }
    return _coll().insert_one(doc).inserted_id


def mark_cancelled(order_id) -> dict | None:
    """Danh dau huy va tra ve don SAU khi huy; None neu khong co don
    hoac don da huy roi.

    Dieu kien status != cancelled nam trong filter nen hai nguoi cung bam
    Huy mot don thi chi mot nguoi thanh cong — nguoi con lai khong lam
    ton kho bi cong tra hai lan.
    """
    return _coll().find_one_and_update(
        {"_id": ObjectId(order_id), "status": {"$ne": "cancelled"}},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now()}},
        return_document=ReturnDocument.AFTER,
    )


def register_return(order_id, product_id, quantity: int, amount: float,
                    reason: str = "", user: str = "") -> dict | None:
    """Ghi nhan hoan tra MOT dong san pham cua don. Tra ve don SAU cap nhat,
    None neu khong hop le (don da huy, hoac so luong tra vuot so da mua).

    Choi cung kieu voi mark_cancelled: dieu kien nam ngay trong filter nen
    hai nguoi cung tra mot mon thi chi mot nguoi thanh cong.
    'returned' la so da tra cong don tren tung item; filter chi khop khi
    returned hien tai <= (so da mua - so muon tra), tuc sau khi $inc thi
    returned van khong vuot qua so da mua. $not/$gt de item CHUA co truong
    returned (don cu) van khop.
    """
    order = get(order_id)
    if not order or order.get("status") == "cancelled":
        return None
    item = next((i for i in order["items"]
                 if str(i["product_id"]) == str(product_id)), None)
    if not item or quantity <= 0:
        return None
    limit = item["quantity"] - quantity   # returned hien tai toi da duoc phep

    return _coll().find_one_and_update(
        {
            "_id": ObjectId(order_id),
            "status": {"$ne": "cancelled"},
            "items": {"$elemMatch": {
                "product_id": item["product_id"],
                "returned": {"$not": {"$gt": limit}},
            }},
        },
        {
            "$inc": {"items.$.returned": quantity, "refunded": amount},
            "$push": {"returns": {
                "product_id": item["product_id"],
                "name": item["name"],
                "quantity": quantity,
                "amount": amount,
                "reason": reason,
                "user": user,
                "created_at": datetime.now(),
            }},
        },
        return_document=ReturnDocument.AFTER,
    )


def by_phone(phone: str, limit: int = 200) -> list[dict]:
    """Lich su mua cua mot khach (tra cuu theo so dien thoai)."""
    return list(_coll().find({"customer.phone": phone})
                .sort("created_at", -1).limit(limit))


def get(order_id) -> dict | None:
    return _coll().find_one({"_id": ObjectId(order_id)})


def get_by_code(order_code: str) -> dict | None:
    return _coll().find_one({"order_code": order_code})


def search(code: str = "", customer: str = "",
           date_from: datetime | None = None,
           date_to: datetime | None = None) -> list[dict]:
    query: dict = {}

    # re.escape de ky tu dac biet nguoi dung go khong bi hieu la cu phap regex
    if code:
        query["order_code"] = {"$regex": re.escape(code), "$options": "i"}
    if customer:
        safe = re.escape(customer)
        query["$or"] = [
            {"customer.name": {"$regex": safe, "$options": "i"}},
            {"customer.phone": {"$regex": safe, "$options": "i"}},
        ]

    date_filter = {}
    if date_from:
        date_filter["$gte"] = date_from
    if date_to:
        # bao gom tron ngay ket thuc. Phai dat ca microsecond, neu khong
        # bien tren la 23:59:59.000000 va don luc 23:59:59.5 bi bo sot.
        date_filter["$lte"] = date_to.replace(
            hour=23, minute=59, second=59, microsecond=999999)
    if date_filter:
        query["created_at"] = date_filter

    return list(_coll().find(query).sort("created_at", -1))


def recent(limit: int = 20) -> list[dict]:
    return list(_coll().find().sort("created_at", -1).limit(limit))
