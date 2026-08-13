"""Nang cap du lieu cu len schema moi, chay MOI lan khoi dong.

Tung buoc deu idempotent (chay lai khong doi ket qua) va chi dong den
document con thieu truong, nen voi database da nang cap thi gan nhu
khong ton chi phi.
"""
from app.database.connection import get_db
from app.services import auth_service
from app.utils.text import search_key


def migrate() -> None:
    db = get_db()

    # 1) san pham tao truoc khi co tim-khong-dau: bo sung name_search
    for product in db.products.find(
            {"name_search": {"$exists": False}}, {"name": 1}):
        db.products.update_one(
            {"_id": product["_id"]},
            {"$set": {"name_search": search_key(product.get("name", ""))}})

    # 2) don tao truoc khi co tinh nang huy don: coi nhu da hoan tat
    db.orders.update_many({"status": {"$exists": False}},
                          {"$set": {"status": "completed"}})

    # 3) dung ho so khach hang tu cac don cu (chi lam khi collection trong,
    #    ve sau checkout tu cap nhat). $nin [""] cung loai don khong co phone.
    if db.customers.count_documents({}) == 0:
        pipeline = [
            {"$match": {"customer.phone": {"$nin": ["", None]},
                        "status": {"$ne": "cancelled"}}},
            {"$sort": {"created_at": 1}},
            {"$group": {
                "_id": "$customer.phone",
                "name": {"$last": "$customer.name"},   # ten theo don gan nhat
                "visits": {"$sum": 1},
                "total_spent": {"$sum": "$total"},
                "first_at": {"$min": "$created_at"},
                "last_at": {"$max": "$created_at"},
            }},
        ]
        for row in db.orders.aggregate(pipeline):
            db.customers.insert_one({
                "phone": row["_id"],
                "name": row["name"],
                "name_search": search_key(row["name"]),
                "visits": row["visits"],
                "total_spent": row["total_spent"],
                "created_at": row["first_at"],
                "last_order_at": row["last_at"],
            })

    # 4) tai khoan dang nhap mac dinh (chi khi chua co tai khoan nao)
    auth_service.ensure_default_users()

    # 5) san pham tao truoc khi co gia von / yeu thich: gan gia tri mac dinh
    db.products.update_many(
        {"cost": {"$exists": False}}, {"$set": {"cost": 0.0}})
    db.products.update_many(
        {"favorite": {"$exists": False}}, {"$set": {"favorite": False}})

    # 6) khach hang tao truoc khi co VIP: mac dinh khong VIP
    db.customers.update_many(
        {"vip": {"$exists": False}}, {"$set": {"vip": False}})
