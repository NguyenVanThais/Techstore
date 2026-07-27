"""Logic nhap hang: lap phieu nhap, cong kho va cap nhat gia von.

Phieu nhap la nguon du lieu duy nhat lam thay doi gia von: gia von tinh
binh quan gia quyen trong product_model.apply_purchase.
"""
from app.models import product as product_model
from app.models import purchase as purchase_model
from app.services import audit_service
from app.utils.formatters import money


class PurchaseCart:
    """Danh sach san pham dang go tren phieu nhap, nam trong bo nho
    (giong Cart cua ban hang): chi ghi xuong database khi bam Tao phieu."""

    def __init__(self):
        self._items: dict[str, dict] = {}   # product_id (str) -> item

    def add(self, product: dict, quantity: int, unit_cost: float) -> None:
        if quantity <= 0:
            raise ValueError("Số lượng nhập phải lớn hơn 0.")
        if unit_cost < 0:
            raise ValueError("Giá nhập không được âm.")

        pid = str(product["_id"])
        existing = self._items.get(pid)
        if existing:
            # cung san pham them lan nua: cong don so luong, lay gia moi nhat
            quantity += existing["quantity"]

        self._items[pid] = {
            "product_id": product["_id"],
            "sku": product.get("sku", ""),
            "name": product["name"],
            "quantity": quantity,
            "cost": unit_cost,
            "subtotal": unit_cost * quantity,
        }

    def remove(self, product_id: str) -> None:
        self._items.pop(product_id, None)

    def clear(self) -> None:
        self._items.clear()

    def items(self) -> list[dict]:
        return list(self._items.values())

    def is_empty(self) -> bool:
        return not self._items

    def total(self) -> float:
        return sum(item["subtotal"] for item in self._items.values())


def create_receipt(cart: PurchaseCart, supplier_name: str, user: dict,
                   note: str = "") -> str:
    """Cong kho + cap nhat gia von cho tung san pham roi ghi phieu.
    Tra ve ma phieu.

    Neu mot san pham bien mat giua chung (bi xoa cung tay trong DB),
    hoan tac phan kho da cong cua cac san pham truoc do roi bao loi.
    """
    if cart.is_empty():
        raise ValueError("Phiếu nhập chưa có sản phẩm nào.")
    if not supplier_name.strip():
        raise ValueError("Hãy chọn nhà cung cấp.")

    items = cart.items()
    applied: list[tuple] = []
    try:
        for item in items:
            ok = product_model.apply_purchase(
                item["product_id"], item["quantity"], item["cost"])
            if not ok:
                raise ValueError(f"Sản phẩm '{item['name']}' không còn tồn tại.")
            applied.append((item["product_id"], item["quantity"]))

        code = purchase_model.next_receipt_code()
        purchase_model.create(
            code, items,
            supplier={"name": supplier_name.strip()},
            user={"username": user.get("username", ""),
                  "display_name": user.get("display_name", "")},
            note=note.strip(),
        )
    except Exception:
        # chi go lai phan SO LUONG; gia von binh quan chap nhan lech mot
        # chut trong tinh huong cuc hiem nay, con hon ghi phieu nua voi
        for pid, qty in applied:
            product_model.restock(pid, -qty)
        raise

    audit_service.log(
        "Nhập hàng",
        f"Phiếu {code} · {supplier_name.strip()} · {money(cart.total())}")
    return code
