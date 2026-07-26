"""Man hinh tra cuu hoa don: loc theo ma don, ten khach, khoang ngay.

Double-click mot dong de mo cua so chi tiet don hang.
"""
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from app.models import order as order_model
from app.services import excel_service, pdf_service, sales_service
from app.utils.formatters import dt, money, order_status_label
from app.utils.validators import ValidationError, parse_date
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title
from app.views.widgets import OptionalDateEntry

COLUMNS = [
    ("order_code", "Mã đơn", 115),
    ("created_at", "Thời gian", 115),
    ("customer", "Khách hàng", 150),
    ("phone", "Điện thoại", 100),
    ("quantity", "SL", 40),
    ("discount", "Giảm giá", 100),
    ("total", "Tổng tiền", 115),
    ("status", "Trạng thái", 95),
]

DETAIL_COLUMNS = [
    ("name", "Sản phẩm", 210),
    ("category", "Danh mục", 110),
    ("price", "Đơn giá", 110),
    ("quantity", "SL mua", 60),
    ("returned", "Đã trả", 60),
    ("subtotal", "Thành tiền", 120),
]


class OrderView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._orders: list[dict] = []

        make_title(self, "Tra cứu hóa đơn",
                   "Double-click một dòng để xem chi tiết — hủy đơn sẽ "
                   "cộng trả tồn kho")
        self._build_filters()
        self._build_table()

    # ---------- giao dien ----------

    def _build_filters(self):
        bar = ttk.LabelFrame(self, text="Bộ lọc", padding=10)
        bar.pack(fill="x", pady=(0, 10))

        ttk.Label(bar, text="Mã đơn").grid(row=0, column=0, padx=4)
        self.code = ttk.Entry(bar, width=18)
        self.code.grid(row=0, column=1, padx=4)

        ttk.Label(bar, text="Khách hàng").grid(row=0, column=2, padx=4)
        self.customer = ttk.Entry(bar, width=20)
        self.customer.grid(row=0, column=3, padx=4)

        ttk.Label(bar, text="Từ ngày").grid(row=0, column=4, padx=4)
        self.date_from = OptionalDateEntry(bar, width=11)
        self.date_from.grid(row=0, column=5, padx=4)

        ttk.Label(bar, text="đến ngày").grid(row=0, column=6, padx=4)
        self.date_to = OptionalDateEntry(bar, width=11)
        self.date_to.grid(row=0, column=7, padx=4)

        for entry in (self.code, self.customer, self.date_from, self.date_to):
            entry.bind("<Return>", lambda e: self.reload())
        # go den dau loc den do o hai o chu
        widgets.debounce_search(self.code, self.reload)
        widgets.debounce_search(self.customer, self.reload)

        ttk.Button(bar, text="Tìm", style="Accent.TButton",
                   command=self.reload).grid(row=0, column=8, padx=6)
        ttk.Button(bar, text="Xóa lọc", command=self.clear_filters).grid(row=0, column=9)

        widgets.date_presets(bar, self.date_from, self.date_to, self.reload).grid(
            row=1, column=0, columnspan=8, sticky="w", pady=(8, 0))
        ttk.Label(bar, text="Bấm mũi tên để chọn ngày từ lịch. Để trống nghĩa là không lọc.",
                  style="Muted.TLabel").grid(
            row=2, column=0, columnspan=8, sticky="w", pady=(6, 0))

    def _build_table(self):
        self.summary = ttk.Label(self, style="Section.TLabel")
        self.summary.pack(anchor="w", pady=(0, 8))

        table = ttk.Frame(self)
        table.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table, columns=[c[0] for c in COLUMNS],
                                 show="headings")
        for key, title, width in COLUMNS:
            self.tree.heading(key, text=title,
                              command=lambda k=key: self._sort_by(k))
            anchor = "e" if key in ("quantity", "discount", "total") else "w"
            self.tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.tree, stretch_column="customer")

        theme.configure_stripes(self.tree)
        # don huy: lam mo CHU — tag chi dat mau chu nen song chung duoc
        # voi soc 'odd' (chi dat mau nen), xem ghi chu o theme.configure_stripes
        self.tree.tag_configure("cancelled", foreground=theme.MUTED)
        self.empty_hint = widgets.EmptyHint(
            self.tree, "Không có hóa đơn nào khớp bộ lọc.\nThử nới khoảng "
                       "ngày hoặc bấm \"Xóa lọc\".")
        self.tree.bind("<Double-1>", lambda e: self.show_detail())

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Xem chi tiết", style="Accent.TButton",
                   command=self.show_detail).pack(side="left")
        ttk.Button(actions, text="Xuất PDF",
                   command=self.export_pdf).pack(side="left", padx=6)
        ttk.Button(actions, text="Xuất Excel",
                   command=self.export_excel).pack(side="left")
        ttk.Button(actions, text="Tải lại",
                   command=self.reload).pack(side="left", padx=6)
        ttk.Button(actions, text="Hủy đơn", style="Danger.TButton",
                   command=self.cancel_order).pack(side="right")

    # ---------- du lieu ----------

    def on_show(self):
        self.reload()

    def reload(self):
        try:
            date_from = parse_date(self.date_from.get(), "Tu ngay")
            date_to = parse_date(self.date_to.get(), "Den ngay")
        except ValidationError as exc:
            messagebox.showwarning("Bộ lọc không hợp lệ", str(exc))
            return

        if date_from and date_to and date_from > date_to:
            messagebox.showwarning("Bộ lọc không hợp lệ",
                                   "'Từ ngày' phải trước 'đến ngày'.")
            return

        orders = order_model.search(
            code=self.code.get().strip(),
            customer=self.customer.get().strip(),
            date_from=date_from,
            date_to=date_to,
        )
        self._orders = orders   # giu lai cho nut Xuat Excel

        self.tree.delete(*self.tree.get_children())
        revenue = 0.0
        cancelled_count = 0
        for order in orders:
            cancelled = order.get("status") == "cancelled"
            refunded = order.get("refunded", 0)
            if cancelled:
                cancelled_count += 1
            else:
                # doanh thu thuc = tong - phan da hoan tra, khop voi Thong ke
                revenue += order["total"] - refunded
            status = order_status_label(order)
            quantity = sum(item["quantity"] for item in order["items"])
            self.tree.insert(
                "", "end", iid=str(order["_id"]),
                tags=("cancelled",) if cancelled else (),
                values=(
                    order["order_code"],
                    dt(order["created_at"]),
                    order["customer"]["name"],
                    order["customer"].get("phone", ""),
                    quantity,
                    money(order["discount"]),
                    money(order["total"]),
                    status,
                ),
            )

        theme.stripe_rows(self.tree)
        self.empty_hint.refresh()
        text = (f"Tìm thấy {len(orders)} hóa đơn, doanh thu {money(revenue)} "
                "(đã trừ hoàn trả)")
        if cancelled_count:
            text += f", không tính {cancelled_count} đơn đã hủy"
        self.summary.config(text=text + ".")

    def _sort_key(self, key: str, value: str):
        """Doi gia tri hien thi ve dang so sanh dung: tien ve so, thoi gian
        ve datetime — so sanh chuoi se xep '29 trieu' truoc '3 trieu'."""
        if key in ("discount", "total"):
            return float("".join(c for c in value if c.isdigit()) or 0)
        if key == "quantity":
            return int(value)
        if key == "created_at":
            return datetime.strptime(value, "%d/%m/%Y %H:%M")
        return value.lower()

    def _sort_by(self, key: str):
        rows = [(self.tree.set(iid, key), iid) for iid in self.tree.get_children("")]
        rows.sort(key=lambda r: self._sort_key(key, r[0]))
        for index, (_, iid) in enumerate(rows):
            self.tree.move(iid, "", index)
        theme.stripe_rows(self.tree)   # ke lai soc theo thu tu moi

    def clear_filters(self):
        for entry in (self.code, self.customer, self.date_from, self.date_to):
            entry.delete(0, "end")
        self.reload()

    # ---------- chi tiet ----------

    def show_detail(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một hóa đơn.")
            return

        order = order_model.get(selection[0])
        if not order:
            messagebox.showwarning("Không tìm thấy", "Hóa đơn đã bị xóa.")
            self.reload()
            return

        OrderDetailDialog(self, order)

    def export_pdf(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một hóa đơn để xuất PDF.")
            return

        order = order_model.get(selection[0])
        if not order:
            messagebox.showwarning("Không tìm thấy", "Hóa đơn đã bị xóa.")
            self.reload()
            return

        export_order_to_pdf(self, order)

    def export_excel(self):
        """Xuat danh sach DANG hien thi (ton trong bo loc) ra Excel."""
        if not self._orders:
            messagebox.showinfo("Không có dữ liệu",
                                "Không có hóa đơn nào để xuất.")
            return
        try:
            path = excel_service.export_orders(self._orders)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không xuất được Excel:\n{exc}")
            return
        _offer_open(self, f"Đã xuất {len(self._orders)} hóa đơn vào:", path)

    def cancel_order(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một hóa đơn để hủy.")
            return

        order = order_model.get(selection[0])
        if not order:
            messagebox.showwarning("Không tìm thấy", "Hóa đơn đã bị xóa.")
            self.reload()
            return
        if order.get("status") == "cancelled":
            messagebox.showinfo("Đã hủy rồi",
                                f"Hóa đơn {order['order_code']} đã bị hủy trước đó.")
            return

        confirm = messagebox.askyesno(
            "Xác nhận hủy đơn",
            f"Hủy hóa đơn {order['order_code']} ({money(order['total'])})?\n\n"
            "Tồn kho sẽ được cộng trả lại và thống kê sẽ không tính đơn này.\n"
            "Thao tác không thể hoàn tác.",
        )
        if not confirm:
            return

        try:
            sales_service.cancel_order(selection[0])
        except ValueError as exc:
            messagebox.showwarning("Không hủy được", str(exc))
            self.reload()
            return

        widgets.toast(self, f"Đã hủy hóa đơn {order['order_code']}",
                      kind="danger")
        self.reload()
        self.app.refresh_stock_badge()


def _offer_open(parent, message: str, path) -> None:
    """Bao da xuat file va hoi co mo ngay khong. Dung chung cho PDF/Excel."""
    open_it = messagebox.askyesno(
        "Đã xuất file", f"{message}\n{path}\n\nMở file ngay bây giờ?",
        parent=parent,
    )
    if open_it:
        try:
            os.startfile(path)
        except OSError as exc:
            messagebox.showwarning("Không mở được", str(exc))


def export_order_to_pdf(parent, order: dict) -> None:
    """Xuat PDF roi hoi co muon mo file khong. Dung chung cho bang va dialog."""
    try:
        path = pdf_service.export_invoice(order)
    except Exception as exc:
        messagebox.showerror("Lỗi", f"Không xuất được PDF:\n{exc}")
        return

    _offer_open(parent, f"Đã lưu hóa đơn {order['order_code']} vào:", path)


class OrderDetailDialog(tk.Toplevel):
    def __init__(self, parent, order: dict):
        super().__init__(parent)
        self.title(f"Hóa đơn {order['order_code']}")
        self.geometry("760x480")
        self.transient(parent.winfo_toplevel())

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        self.configure(background=theme.BG)
        header = ttk.Frame(body)
        header.pack(fill="x")
        ttk.Label(header, text=f"Hóa đơn {order['order_code']}",
                  style="Title.TLabel").pack(side="left")
        if order.get("status") == "cancelled":
            ttk.Label(header, text="ĐÃ HỦY", foreground=theme.DANGER,
                      font=(theme.FAMILY, 12, "bold")).pack(
                side="left", padx=12)
        ttk.Label(body, text=dt(order["created_at"]),
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 12))

        info = ttk.LabelFrame(body, text="Khách hàng", padding=8)
        info.pack(fill="x", pady=(0, 10))
        phone = order["customer"].get("phone") or "(không có)"
        ttk.Label(info, text=f"Họ tên:  {order['customer']['name']}").pack(anchor="w")
        ttk.Label(info, text=f"Điện thoại:  {phone}").pack(anchor="w")

        table = ttk.Frame(body)
        table.pack(fill="both", expand=True)

        tree = ttk.Treeview(table, columns=[c[0] for c in DETAIL_COLUMNS],
                            show="headings", height=8)
        for key, title, width in DETAIL_COLUMNS:
            tree.heading(key, text=title)
            anchor = ("e" if key in ("price", "quantity", "returned", "subtotal")
                      else "w")
            tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(tree, stretch_column="name")

        self.order = order
        self._reload_items(tree)
        self.items_tree = tree

        self.totals = ttk.Frame(body)
        self.totals.pack(fill="x", pady=(10, 0))
        self.totals.columnconfigure(0, weight=1)
        self._rebuild_totals()

        buttons = ttk.Frame(body)
        buttons.pack(pady=(14, 0))
        if order.get("status") != "cancelled":
            ttk.Button(buttons, text="Hoàn trả sản phẩm", style="Danger.TButton",
                       command=self._return_selected).pack(side="left", padx=4)
        # doc self.order tai thoi diem BAM nut: sau khi hoan tra, PDF phai in
        # theo so lieu moi chu khong phai ban chup luc mo dialog
        ttk.Button(buttons, text="Xuất PDF", style="Accent.TButton",
                   command=lambda: export_order_to_pdf(self, self.order)).pack(
            side="left", padx=4)
        ttk.Button(buttons, text="Đóng", command=self.destroy).pack(side="left", padx=4)

        self.grab_set()

    def _reload_items(self, tree) -> None:
        tree.delete(*tree.get_children())
        for index, item in enumerate(self.order["items"]):
            tree.insert("", "end", iid=str(index), values=(
                item["name"],
                item["category"],
                money(item["price"]),
                item["quantity"],
                item.get("returned", 0),
                money(item["subtotal"]),
            ))

    def _rebuild_totals(self) -> None:
        """Ve lai khoi tong tien tu self.order — goi lai sau moi lan hoan tra
        de dong 'Đã hoàn trả' / 'Thực thu' hien dung so moi."""
        for child in self.totals.winfo_children():
            child.destroy()

        order = self.order
        refunded = order.get("refunded", 0)
        bold = (theme.FAMILY, 13, "bold")
        rows = [
            ("Tạm tính", money(order["subtotal"]), None),
            ("Giảm giá", money(order["discount"]), None),
            ("Tổng cộng", money(order["total"]), None if refunded else bold),
        ]
        if refunded:
            rows.append(("Đã hoàn trả", "-" + money(refunded), None))
            rows.append(("Thực thu", money(order["total"] - refunded), bold))
        for index, (label, value, font) in enumerate(rows):
            ttk.Label(self.totals, text=label, font=font or theme.FONT_BASE).grid(
                row=index, column=0, sticky="e", padx=8, pady=1)
            ttk.Label(self.totals, text=value, font=font or theme.FONT_BASE,
                      foreground=theme.DANGER if font else theme.TEXT).grid(
                row=index, column=1, sticky="e", pady=1)

    def _return_selected(self):
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một dòng sản phẩm.",
                                parent=self)
            return
        item = self.order["items"][int(selection[0])]
        returnable = item["quantity"] - item.get("returned", 0)
        if returnable <= 0:
            messagebox.showinfo("Đã hoàn trả hết",
                                f"'{item['name']}' đã được hoàn trả toàn bộ.",
                                parent=self)
            return

        quantity = widgets.ask_quantity(
            self, "Hoàn trả sản phẩm",
            f"Số lượng hoàn trả cho '{item['name']}'\n"
            f"(đã mua {item['quantity']}, còn hoàn trả được {returnable}):",
            initial=1, minvalue=1, maxvalue=returnable,
        )
        if not quantity:
            return

        if not messagebox.askyesno(
                "Xác nhận hoàn trả",
                f"Hoàn trả {quantity} '{item['name']}'?\n"
                "Tồn kho sẽ được cộng lại và trừ vào chi tiêu của khách.",
                parent=self):
            return

        try:
            updated = sales_service.return_item(
                self.order["_id"], item["product_id"], quantity)
        except ValueError as exc:
            messagebox.showwarning("Không hoàn trả được", str(exc), parent=self)
            return

        self.order = updated
        self._reload_items(self.items_tree)
        self._rebuild_totals()
        widgets.toast(self, f"Đã hoàn trả {quantity} '{item['name']}'")
        # bang ngoai va chan sidebar cung phai cap nhat theo du lieu moi.
        # Duyet len tung master (khong dung winfo_toplevel: dialog nay co the
        # duoc mo tu MOT dialog khac — CustomerHistoryDialog — chinh no cung
        # la mot Toplevel nen winfo_toplevel se dung lai o do).
        widget = self.master
        while widget is not None and not hasattr(widget, "refresh_stock_badge"):
            widget = getattr(widget, "master", None)
        if widget is not None:
            if "orders" in widget.frames:
                widget.frames["orders"].reload()
            widget.refresh_stock_badge()
