"""Tao CSDL va du lieu mau cho TechStore."""

from app.database.connection import get_db


def create_sample_data():
    db = get_db()

    # Tao rang buoc khong trung ma san pham.
    db.products.create_index("code", unique=True, sparse=True)

    # Chi them du lieu khi collection dang trong.
    if db.categories.count_documents({}) == 0:
        db.categories.insert_many([
            {"name": "Laptop"},
            {"name": "Dien thoai"},
            {"name": "Phu kien"},
        ])

    if db.products.count_documents({}) == 0:
        db.products.insert_many([
            {
                "code": "SP001",
                "name": "Laptop Dell",
                "category": "Laptop",
                "price": 15_000_000,
                "quantity": 10,
            },
            {
                "code": "SP002",
                "name": "Dien thoai Samsung",
                "category": "Dien thoai",
                "price": 8_000_000,
                "quantity": 20,
            },
            {
                "code": "SP003",
                "name": "Chuot khong day",
                "category": "Phu kien",
                "price": 350_000,
                "quantity": 50,
            },
        ])


if __name__ == "__main__":
    create_sample_data()
    print("Da tao CSDL va du lieu mau.")
