"""Tao du lieu mau: danh muc, san pham, va vai don hang cu.

Chay:  python seed_data.py --force
Demo voi database rong trong rat te, luon chay file nay truoc khi bao ve.
"""
import random
import sys
from datetime import datetime, timedelta

from app.database.connection import get_db, check_connection, ensure_indexes
from app.services.auth_service import ensure_default_users
from app.utils.text import search_key

# Console Windows mac dinh la cp1252, in chu co dau se nem UnicodeEncodeError.
sys.stdout.reconfigure(encoding="utf-8")

CATEGORIES = [
    ("Điện thoại", "Smartphone các hãng"),
    ("Laptop", "Máy tính xách tay"),
    ("Tai nghe", "Tai nghe có dây và không dây"),
    ("Phụ kiện", "Sạc, cáp, ốp lưng, chuột, bàn phím"),
    ("Máy tính bảng", "Tablet"),
]

PRODUCTS = [
    # (sku, ten, danh muc, gia, ton kho, ton toi thieu)
    ("DT001", "iPhone 15 Pro Max 256GB", "Điện thoại", 29990000, 12, 5),
    ("DT002", "iPhone 15 128GB", "Điện thoại", 21990000, 20, 5),
    ("DT003", "Samsung Galaxy S24 Ultra", "Điện thoại", 27990000, 8, 5),
    ("DT004", "Samsung Galaxy A55", "Điện thoại", 9490000, 25, 8),
    ("DT005", "Xiaomi 14", "Điện thoại", 16990000, 3, 5),
    ("DT006", "OPPO Reno11 F", "Điện thoại", 8290000, 15, 5),
    ("DT007", "Google Pixel 8", "Điện thoại", 15990000, 2, 4),

    ("LT001", "MacBook Air M3 13 inch", "Laptop", 27990000, 10, 4),
    ("LT002", "MacBook Pro 14 M3 Pro", "Laptop", 45990000, 5, 3),
    ("LT003", "Dell XPS 13 Plus", "Laptop", 32990000, 6, 3),
    ("LT004", "Asus ROG Strix G16", "Laptop", 35990000, 4, 3),
    ("LT005", "Lenovo ThinkPad X1 Carbon", "Laptop", 38990000, 1, 3),
    ("LT006", "HP Pavilion 15", "Laptop", 15990000, 14, 5),
    ("LT007", "Acer Nitro 5", "Laptop", 19990000, 9, 4),

    ("TN001", "AirPods Pro 2", "Tai nghe", 5990000, 30, 10),
    ("TN002", "AirPods 4", "Tai nghe", 3990000, 22, 10),
    ("TN003", "Sony WH-1000XM5", "Tai nghe", 7990000, 7, 5),
    ("TN004", "Samsung Galaxy Buds3 Pro", "Tai nghe", 4290000, 18, 8),
    ("TN005", "JBL Tune 720BT", "Tai nghe", 1690000, 4, 8),
    ("TN006", "Soundcore Life Q30", "Tai nghe", 1490000, 26, 10),

    ("PK001", "Sạc nhanh Anker 65W", "Phụ kiện", 890000, 45, 15),
    ("PK002", "Cáp USB-C to Lightning 1m", "Phụ kiện", 390000, 60, 20),
    ("PK003", "Ốp lưng iPhone 15 Pro Max", "Phụ kiện", 250000, 80, 20),
    ("PK004", "Chuột Logitech MX Master 3S", "Phụ kiện", 2490000, 12, 5),
    ("PK005", "Bàn phím Keychron K2", "Phụ kiện", 2190000, 8, 5),
    ("PK006", "Pin dự phòng Xiaomi 20000mAh", "Phụ kiện", 690000, 5, 10),
    ("PK007", "Giá đỡ laptop nhôm", "Phụ kiện", 450000, 33, 10),

    ("MT001", "iPad Air M2 11 inch", "Máy tính bảng", 16990000, 11, 4),
    ("MT002", "iPad Pro M4 11 inch", "Máy tính bảng", 26990000, 6, 3),
    ("MT003", "Samsung Galaxy Tab S9", "Máy tính bảng", 18990000, 2, 4),
    ("MT004", "Xiaomi Pad 6", "Máy tính bảng", 7990000, 13, 5),
]

CUSTOMERS = [
    ("Nguyễn Văn An", "0912345678"),
    ("Trần Thị Bình", "0987654321"),
    ("Lê Hoàng Cường", "0901122334"),
    ("Phạm Thu Dung", "0938877665"),
    ("Hoàng Minh Đức", "0977001122"),
    ("Võ Thị Lan", "0966554433"),
    ("Khách lẻ", ""),
]

# SKU noi bat, danh dau yeu thich de demo tinh nang o man Ban hang
FAVORITE_SKUS = {"DT001", "LT001", "TN001", "PK003"}

SUPPLIERS = [
    ("Digiworld Việt Nam", "0281234567", "sales@digiworld.vn",
     "68 Nguyễn Huệ, Q.1, TP.HCM"),
    ("FPT Trading", "0243333888", "contact@fpttrading.vn",
     "17 Duy Tân, Cầu Giấy, Hà Nội"),
    ("Petrosetco", "0287007007", "info@petrosetco.vn",
     "97 Nguyễn Thị Minh Khai, Q.3, TP.HCM"),
    ("Synnex FPT", "0247300888", "cskh@synnexfpt.com.vn",
     "10 Phạm Văn Bạch, Cầu Giấy, Hà Nội"),
]


def seed(force: bool = False):
    if not force:
        print("LENH BI CHAN: seed se xoa du lieu nghiep vu hien tai.")
        print("Chi dung database phat trien va chay lai voi: "
              "python seed_data.py --force")
        return

    ok, message = check_connection()
    if not ok:
        print(message)
        return

    db = get_db()

    print("Xóa dữ liệu cũ...")
    db.categories.delete_many({})
    db.products.delete_many({})
    db.orders.delete_many({})
    db.customers.delete_many({})
    db.suppliers.delete_many({})
    db.purchases.delete_many({})
    db.audit_logs.delete_many({})
    # bo dem ma don phai xoa cung, neu khong ma don moi se nhay so
    db.counters.delete_many({})
    # KHONG xoa users: mat tai khoan admin sau moi lan seed thi rat phien

    print("Tạo danh mục...")
    db.categories.insert_many(
        [{"name": name, "description": desc} for name, desc in CATEGORIES]
    )

    now = datetime.now()

    print("Tạo nhà cung cấp...")
    db.suppliers.insert_many([
        {"name": name, "name_search": search_key(name), "phone": phone,
         "email": email, "address": address, "note": "", "created_at": now}
        for name, phone, email, address in SUPPLIERS
    ])
    suppliers = list(db.suppliers.find())

    print("Tạo sản phẩm...")
    docs = []
    for sku, name, category, price, stock, min_stock in PRODUCTS:
        # gia von ~72% gia ban (bien thien nhe) de demo the "Loi nhuan"
        cost = round(price * random.uniform(0.65, 0.78), -3)
        docs.append({
            "sku": sku,
            "name": name,
            "name_search": search_key(name),   # tim khong dau
            "category": category,
            "price": float(price),
            "cost": float(cost),
            "favorite": sku in FAVORITE_SKUS,
            "stock": stock,
            "min_stock": min_stock,
            "description": "",
            "image_path": "",
            "is_active": True,
            "created_at": now,
        })
    db.products.insert_many(docs)

    products = list(db.products.find({"is_active": True}))

    print("Tạo phiếu nhập hàng mẫu...")
    purchases = []
    pn_counters: dict[str, int] = {}
    for days_ago in sorted(random.sample(range(1, 360), 24), reverse=True):
        day = now - timedelta(days=days_ago)
        chosen = random.sample(products, random.randint(2, 4))
        items = []
        for product in chosen:
            qty = random.randint(10, 40)
            # gia nhap dao dong quanh gia von hien tai cua san pham
            unit_cost = round(product["cost"] * random.uniform(0.95, 1.05), -3)
            items.append({
                "product_id": product["_id"],
                "sku": product["sku"],
                "name": product["name"],
                "quantity": qty,
                "cost": unit_cost,
                "subtotal": unit_cost * qty,
            })

        key = f"PN{day:%Y%m%d}"
        pn_counters[key] = pn_counters.get(key, 0) + 1
        purchases.append({
            "receipt_code": f"{key}-{pn_counters[key]:04d}",
            "items": items,
            "total": sum(i["subtotal"] for i in items),
            "supplier": {"name": random.choice(suppliers)["name"]},
            "user": {"username": "admin", "display_name": "Quản trị viên"},
            "note": "",
            "created_at": day.replace(hour=random.randint(8, 17),
                                      minute=random.randint(0, 59),
                                      second=0, microsecond=0),
        })
    db.purchases.insert_many(purchases)

    print("Tạo đơn hàng mẫu (12 tháng gần nhất)...")
    orders = []
    counters: dict[str, int] = {}

    for days_ago in range(365, -1, -1):
        day = now - timedelta(days=days_ago)
        # cuoi tuan ban nhieu hon, thang cuoi nam ban nhieu hon
        base = 3 if day.weekday() >= 5 else 2
        if day.month in (11, 12, 1):
            base += 1
        num_orders = random.randint(0, base)

        for _ in range(num_orders):
            chosen = random.sample(products, random.randint(1, 3))
            items = []
            for product in chosen:
                qty = random.randint(1, 2)
                items.append({
                    "product_id": product["_id"],
                    "sku": product["sku"],
                    "name": product["name"],
                    "category": product["category"],
                    "price": product["price"],
                    "cost": product["cost"],   # de the "Loi nhuan" co so lieu that
                    "quantity": qty,
                    "subtotal": product["price"] * qty,
                })

            subtotal = sum(i["subtotal"] for i in items)
            discount = 0.0
            if random.random() < 0.15:
                discount = round(subtotal * 0.05, -3)

            key = f"{day:%Y%m%d}"
            counters[key] = counters.get(key, 0) + 1

            name, phone = random.choice(CUSTOMERS)
            created = day.replace(
                hour=random.randint(8, 20),
                minute=random.randint(0, 59),
                second=0, microsecond=0,
            )
            # Don cua hom nay khong duoc mang dau thoi gian o tuong lai:
            # gio ngau nhien co the roi vao sau thoi diem chay seed.
            if created > now:
                created = now.replace(second=0, microsecond=0)

            orders.append({
                "order_code": f"HD{key}-{counters[key]:04d}",
                "items": items,
                "subtotal": subtotal,
                "discount": discount,
                "total": subtotal - discount,
                "customer": {"name": name, "phone": phone},
                "status": "completed",
                "created_at": created,   # datetime that, khong phai chuoi
            })

    db.orders.insert_many(orders)

    print("Tạo hồ sơ khách hàng từ các đơn trên...")
    for name, phone in CUSTOMERS:
        if not phone:
            continue   # "Khách lẻ" không có số thì không lập hồ sơ được
        mine = [o for o in orders if o["customer"]["phone"] == phone]
        if not mine:
            continue
        db.customers.insert_one({
            "phone": phone,
            "name": name,
            "name_search": search_key(name),
            "vip": False,
            "visits": len(mine),
            "total_spent": sum(o["total"] for o in mine),
            "created_at": min(o["created_at"] for o in mine),
            "last_order_at": max(o["created_at"] for o in mine),
        })

    print("Tạo index và tài khoản mặc định...")
    ensure_indexes()
    ensure_default_users()

    print()
    print(f"Xong. {len(CATEGORIES)} danh mục, {len(PRODUCTS)} sản phẩm, "
          f"{len(orders)} đơn hàng, {db.customers.count_documents({})} khách hàng, "
          f"{len(suppliers)} nhà cung cấp, {len(purchases)} phiếu nhập.")
    low = db.products.count_documents(
        {"is_active": True, "$expr": {"$lte": ["$stock", "$min_stock"]}}
    )
    print(f"Có {low} sản phẩm đang dưới mức tồn kho tối thiểu (để test cảnh báo).")
    print("Đăng nhập: admin / admin123 (Quản lý) hoặc nhanvien / 123456 (Nhân viên).")


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
