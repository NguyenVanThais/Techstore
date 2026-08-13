"""Thong ke doanh thu bang MongoDB aggregation pipeline.

Toan bo phep cong duoc thuc hien tren server MongoDB, khong keo du lieu
ve Python roi cong bang vong for.

Moi con so deu da tru phan HOAN TRA: don co truong `refunded` (tong tien
da hoan) va tung item co `returned` (so luong da tra lai). $ifNull de don
tao truoc khi co tinh nang hoan tra van tinh dung.
"""
from datetime import datetime

from app.database.connection import get_db

# ngay / thang / nam chi khac nhau o chuoi format
GROUP_FORMATS = {
    "day": "%Y-%m-%d",
    "month": "%Y-%m",
    "year": "%Y",
}

# doanh thu thuc cua mot don = tong tien - phan da hoan tra
_NET_REVENUE = {"$subtract": ["$total", {"$ifNull": ["$refunded", 0]}]}

# so luong thuc cua mot item = da mua - da tra lai
_NET_QTY = {"$subtract": ["$items.quantity",
                          {"$ifNull": ["$items.returned", 0]}]}


def _match_stage(date_from: datetime | None, date_to: datetime | None) -> dict:
    """$match dung chung: LUON loai don da huy, kem khoang ngay neu co.

    $ne thay vi $eq "completed" de don cu (tao truoc khi co truong status)
    van duoc tinh.
    """
    match: dict = {"status": {"$ne": "cancelled"}}
    rng = {}
    if date_from:
        rng["$gte"] = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_to:
        # microsecond=999999 de khong bo sot don trong nua giay cuoi cua ngay
        rng["$lte"] = date_to.replace(
            hour=23, minute=59, second=59, microsecond=999999)
    if rng:
        match["created_at"] = rng
    return {"$match": match}


def summary(date_from=None, date_to=None) -> dict:
    """Cac con so tong quan cho dashboard, gom ca gia von va loi nhuan."""
    pipeline = [_match_stage(date_from, date_to)]

    # gia von cua mot don = tong (gia von x so luong chua tra) tren tung item
    cost_expr = {"$sum": {"$map": {
        "input": "$items", "as": "i",
        "in": {"$multiply": [
            {"$ifNull": ["$$i.cost", 0]},
            {"$subtract": ["$$i.quantity", {"$ifNull": ["$$i.returned", 0]}]},
        ]},
    }}}
    sold_expr = {"$sum": {"$map": {
        "input": "$items", "as": "i",
        "in": {"$subtract": ["$$i.quantity", {"$ifNull": ["$$i.returned", 0]}]},
    }}}

    pipeline.append({
        "$group": {
            "_id": None,
            "revenue": {"$sum": _NET_REVENUE},
            "cost": {"$sum": cost_expr},
            "orders": {"$sum": 1},
            "products_sold": {"$sum": sold_expr},
        }
    })

    result = list(get_db().orders.aggregate(pipeline))
    if not result:
        return {"revenue": 0, "cost": 0, "profit": 0, "orders": 0,
                "products_sold": 0, "avg_order": 0}

    row = result[0]
    row["profit"] = row["revenue"] - row["cost"]
    row["avg_order"] = row["revenue"] / row["orders"] if row["orders"] else 0
    row.pop("_id", None)
    return row


def revenue_by_period(group_by: str = "month", date_from=None, date_to=None) -> list[dict]:
    """Doanh thu theo ngay / thang / nam."""
    fmt = GROUP_FORMATS.get(group_by, "%Y-%m")

    pipeline = [_match_stage(date_from, date_to)]

    pipeline += [
        {"$group": {
            "_id": {"$dateToString": {"format": fmt, "date": "$created_at"}},
            "revenue": {"$sum": _NET_REVENUE},
            "orders": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    return list(get_db().orders.aggregate(pipeline))


def revenue_by_category(date_from=None, date_to=None) -> list[dict]:
    """Doanh thu theo loai san pham.

    Phai $unwind mang items truoc, de moi dong san pham thanh mot document
    rieng, roi moi $group theo category duoc.
    """
    pipeline = [_match_stage(date_from, date_to)]

    pipeline += [
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.category",
            "revenue": {"$sum": {"$multiply": ["$items.price", _NET_QTY]}},
            "quantity": {"$sum": _NET_QTY},
        }},
        {"$sort": {"revenue": -1}},
    ]
    return list(get_db().orders.aggregate(pipeline))


def top_products(limit: int = 10, date_from=None, date_to=None) -> list[dict]:
    pipeline = [_match_stage(date_from, date_to)]

    pipeline += [
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.name",
            "quantity": {"$sum": _NET_QTY},
            "revenue": {"$sum": {"$multiply": ["$items.price", _NET_QTY]}},
        }},
        {"$sort": {"quantity": -1}},
        {"$limit": limit},
    ]
    return list(get_db().orders.aggregate(pipeline))


def top_customers(limit: int = 10, date_from=None, date_to=None) -> list[dict]:
    """Khach chi tieu nhieu nhat TRONG khoang ngay dang loc.

    Tinh tu cac don (khong doc collection customers) de ton trong bo loc
    thoi gian giong moi bieu do khac; khach le khong co so dien thoai thi
    khong nhom lai duoc nen bo qua.
    """
    pipeline = [_match_stage(date_from, date_to)]

    pipeline += [
        {"$match": {"customer.phone": {"$nin": ["", None]}}},
        {"$group": {
            "_id": "$customer.phone",
            "name": {"$last": "$customer.name"},
            "revenue": {"$sum": _NET_REVENUE},
            "orders": {"$sum": 1},
        }},
        {"$sort": {"revenue": -1}},
        {"$limit": limit},
    ]
    return list(get_db().orders.aggregate(pipeline))
