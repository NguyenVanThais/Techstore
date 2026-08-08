"""Dinh dang hien thi."""
from datetime import datetime


def money(value: float) -> str:
    """1500000 -> '1.500.000 đ'"""
    return f"{value:,.0f}".replace(",", ".") + " đ"


def money_short(value: float) -> str:
    """Dung cho nhan truc bieu do."""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} tỷ"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} tr"
    if value >= 1_000:
        return f"{value / 1_000:.0f} ng"
    return f"{value:.0f}"


def dt(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M") if value else ""


def order_status_label(order: dict) -> str:
    """Nhan trang thai don hang, dung chung cho bang hoa don, lich su mua
    va file Excel — mot cho quyet dinh de ba noi khong lech nhau."""
    if order.get("status") == "cancelled":
        return "Đã hủy"
    if not order.get("refunded"):
        return "Hoàn tất"
    if all(item.get("returned", 0) >= item["quantity"]
           for item in order["items"]):
        return "Trả toàn bộ"
    return "Hoàn 1 phần"
