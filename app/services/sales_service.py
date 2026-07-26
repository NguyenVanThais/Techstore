"""Logic ban hang: gio hang, thanh toan, huy don va hoan tra."""
from app.models import customer as customer_model
from app.models import order as order_model
from app.models import product as product_model
from app.services import audit_service
from app.utils.formatters import money


class OutOfStockError(Exception):
    pass


class Cart:
    """Gio hang trong bo nho. Chi ghi xuong DB khi thanh toan."""

    def __init__(self):
        self._items: dict[str, dict] = {}  # product_id (str) -> item

    def add(self, product: dict, quantity: int = 1) -> None:
        pid = str(product["_id"])
        current = self._items.get(pid, {}).get("quantity", 0)
        wanted = current + quantity

        if wanted > product["stock"]:
            raise OutOfStockError(
                f"'{product['name']}' chỉ còn {product['stock']} sản phẩm."
            )

        self._items[pid] = {
            "product_id": product["_id"],
            "sku": product.get("sku", ""),
            "name": product["name"],
            # copy category / price / cost tai thoi diem ban — gia von de
            # thong ke loi nhuan khong bi sai khi gia nhap doi ve sau
            "category": product["category"],
            "price": product["price"],
            "cost": product.get("cost", 0) or 0,
            "quantity": wanted,
            "subtotal": product["price"] * wanted,
            "_stock": product["stock"],
        }

    def set_quantity(self, product_id: str, quantity: int) -> None:
        item = self._items.get(product_id)
        if not item:
            return
        if quantity <= 0:
            self.remove(product_id)
            return

        # Doc lai ton kho tu DB thay vi tin vao so da chup luc them vao gio:
        # neu vua nhap them hang thi so cu se chan oan nguoi ban.
        fresh = product_model.get(item["product_id"])
        if fresh:
            item["_stock"] = fresh["stock"]

        if quantity > item["_stock"]:
            raise OutOfStockError(
                f"'{item['name']}' chỉ còn {item['_stock']} sản phẩm."
            )
        item["quantity"] = quantity
        item["subtotal"] = item["price"] * quantity

    def remove(self, product_id: str) -> None:
        self._items.pop(product_id, None)

    def clear(self) -> None:
        self._items.clear()

    def items(self) -> list[dict]:
        return list(self._items.values())

    def is_empty(self) -> bool:
        return not self._items

    def subtotal(self) -> float:
        return sum(item["subtotal"] for item in self._items.values())

    def total_quantity(self) -> int:
        return sum(item["quantity"] for item in self._items.values())


def checkout(cart: Cart, customer: dict, discount: float = 0.0) -> str:
    """Tru ton kho roi ghi don hang. Tra ve ma don.

    Neu mot san pham het hang giua chung, hoan tac nhung san pham da tru
    truoc do roi bao loi -- khong de database o trang thai nua voi.
    """
    if cart.is_empty():
        raise ValueError("Giỏ hàng đang trống.")

    # Khong tin vao giao dien: kiem tra lai o ngay tang nghiep vu,
    # neu khong mot lenh goi sai se ghi xuong don co total am.
    if discount < 0:
        raise ValueError("Giảm giá không được âm.")
    if discount > cart.subtotal():
        raise ValueError("Giảm giá không được lớn hơn tạm tính.")

    items = cart.items()
    decreased: list[tuple] = []

    try:
        for item in items:
            ok = product_model.decrease_stock(item["product_id"], item["quantity"])
            if not ok:
                raise OutOfStockError(
                    f"'{item['name']}' vừa hết hàng hoặc đã ngừng bán."
                )
            decreased.append((item["product_id"], item["quantity"]))

        clean_items = [
            {k: v for k, v in item.items() if not k.startswith("_")}
            for item in items
        ]
        code = order_model.next_order_code()
        order_model.create(code, clean_items, customer, discount)

    except Exception:
        for pid, qty in decreased:
            product_model.increase_stock(pid, qty)
        raise

    # Don da ghi thanh cong. Ho so khach hang chi la du lieu phu, dat NGOAI
    # khoi try o tren: neu buoc nay loi thi khong duoc hoan tac ton kho cua
    # mot don da ton tai.
    try:
        customer_model.upsert_on_checkout(
            customer.get("name", ""), customer.get("phone", ""),
            cart.subtotal() - discount)
    except Exception:
        pass
    audit_service.log("Thanh toán",
                      f"Đơn {code} · {money(cart.subtotal() - discount)}")
    return code


def cancel_order(order_id) -> dict:
    """Huy hoa don: cong tra ton kho, tru lai so lieu khach hang.

    mark_cancelled la thao tac nguyen tu (filter status != cancelled) nen
    hai nguoi cung bam Huy thi chi mot nguoi qua duoc buoc danh dau —
    ton kho khong bi cong tra hai lan.
    """
    order = order_model.mark_cancelled(order_id)
    if not order:
        raise ValueError("Hóa đơn không tồn tại hoặc đã bị hủy trước đó.")

    for item in order["items"]:
        # cong tra ca san pham da ngung ban: hang van quay ve kho.
        # phan da hoan tra truoc do thi DA cong kho roi, khong cong lai.
        quantity = item["quantity"] - item.get("returned", 0)
        if quantity > 0:
            product_model.increase_stock(item["product_id"], quantity)

    # phan tien da hoan cung da tru khoi chi tieu cua khach roi
    customer_model.rollback_order(
        order["customer"].get("phone", ""),
        order["total"] - order.get("refunded", 0))
    audit_service.log("Hủy hóa đơn",
                      f"Đơn {order['order_code']} · {money(order['total'])}")
    return order


def return_item(order_id, product_id, quantity: int, reason: str = "") -> dict:
    """Hoan tra mot phan don hang: khach tra lai `quantity` cai cua mot san
    pham. Cong tra ton kho, tru chi tieu cua khach, ghi lich su vao don.

    Tien hoan tinh theo gia ban TRU phan giam gia chia deu theo ty le
    (don giam 10% thi moi mon tra lai cung hoan it hon 10%) — hoan du gia
    ban se tra cho khach nhieu hon so ho da tra.
    Tra ve don hang sau cap nhat.
    """
    order = order_model.get(order_id)
    if not order:
        raise ValueError("Hóa đơn không tồn tại.")
    if order.get("status") == "cancelled":
        raise ValueError("Hóa đơn đã hủy — tồn kho đã được cộng trả toàn bộ.")

    item = next((i for i in order["items"]
                 if str(i["product_id"]) == str(product_id)), None)
    if not item:
        raise ValueError("Sản phẩm này không có trong hóa đơn.")

    returnable = item["quantity"] - item.get("returned", 0)
    if quantity <= 0 or quantity > returnable:
        raise ValueError(
            f"Chỉ còn {returnable} sản phẩm '{item['name']}' có thể hoàn trả.")

    ratio = order["total"] / order["subtotal"] if order["subtotal"] else 1.0
    amount = round(item["price"] * quantity * ratio)

    updated = order_model.register_return(
        order_id, product_id, quantity, amount, reason,
        audit_service.current_username())
    if not updated:
        # nguoi khac vua tra truoc / vua huy don trong luc minh thao tac
        raise ValueError("Không hoàn trả được — hóa đơn vừa bị thay đổi, "
                         "hãy mở lại chi tiết đơn.")

    # ghi nhan xong moi dong den kho va khach, cung thu tu voi huy don
    product_model.increase_stock(product_id, quantity)
    customer_model.refund(updated["customer"].get("phone", ""), amount)
    audit_service.log(
        "Hoàn trả hàng",
        f"Đơn {updated['order_code']} · {item['name']} x{quantity} · "
        f"hoàn {money(amount)}" + (f" · lý do: {reason}" if reason else ""))
    return updated
