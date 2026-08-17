"""Man hinh khach hang.

Khach KHONG nhap tay: moi don thanh toan co so dien thoai se tu tao/cap
nhat mot khach (xem customer model). Man nay chi de tra cuu va xem
lich su mua.
"""
import tkinter as tk
from tkinter import messagebox, ttk

from app.models import customer as customer_model
from app.models import order as order_model
from app.services import audit_service
from app.utils.formatters import dt, money, order_status_label
from app.utils.validators import ValidationError, parse_phone, require_text
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title
from app.views.order_view import OrderDetailDialog

COLUMNS = [
    ("name", "Khách hàng", 210),
    ("phone", "Điện thoại", 120),
    ("visits", "Số lần mua", 85),
    ("total_spent", "Tổng chi tiêu", 140),
    ("last_order_at", "Mua gần nhất", 130),
]

HISTORY_COLUMNS = [
    ("order_code", "Mã đơn", 140),
    ("created_at", "Thời gian", 140),
    ("quantity", "SL", 50),
    ("total", "Tổng tiền", 130),
    ("status", "Trạng thái", 90),
]


class CustomerView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        make_title(self, "Khách hàng",
                   "Tự ghi nhận từ các đơn có số điện thoại — "
                   "double-click để xem lịch sử mua")
        self._build_filters()
        self._build_table()

    def _build_filters(self):
        bar = ttk.LabelFrame(self, text="Tìm kiếm", padding=10)
        bar.pack(fill="x", pady=(0, 10))

        ttk.Label(bar, text="Tên hoặc số điện thoại").grid(row=0, column=0, padx=4)
        self.keyword = ttk.Entry(bar, width=30)
        self.keyword.grid(row=0, column=1, padx=4)
        self.keyword.bind("<Return>", lambda e: self.reload())
        widgets.debounce_search(self.keyword, self.reload)

        ttk.Button(bar, text="Tìm", style="Accent.TButton",
                   command=self.reload).grid(row=0, column=2, padx=6)
        ttk.Button(bar, text="Xóa lọc", command=self.clear_filters).grid(
            row=0, column=3)

        ttk.Label(bar, text="Gõ không dấu cũng tìm được (\"nguyen van\" ra "
                            "\"Nguyễn Văn\").",
                  style="Muted.TLabel").grid(row=1, column=0, columnspan=4,
                                             sticky="w", pady=(6, 0))

    def _build_table(self):
        self.summary = ttk.Label(self, style="Section.TLabel")
        self.summary.pack(anchor="w", pady=(0, 8))

        table = ttk.Frame(self)
        table.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table, columns=[c[0] for c in COLUMNS],
                                 show="headings")
        for key, title, width in COLUMNS:
            self.tree.heading(key, text=title)
            anchor = "e" if key in ("visits", "total_spent") else "w"
            self.tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.tree, stretch_column="name")

        theme.configure_stripes(self.tree)
        self.empty_hint = widgets.EmptyHint(
            self.tree, "Chưa có khách hàng nào.\nKhách được ghi nhận tự động "
                       "khi thanh toán có nhập số điện thoại.")
        self.tree.bind("<Double-1>", lambda e: self.show_history())

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Thêm khách hàng", style="Accent.TButton",
                   command=self.add_customer).pack(side="left")
        ttk.Button(actions, text="Xem lịch sử mua",
                   command=self.show_history).pack(side="left", padx=6)
        ttk.Button(actions, text="Sửa thông tin",
                   command=self.edit_info).pack(side="left")
        ttk.Button(actions, text="Tải lại",
                   command=self.reload).pack(side="left", padx=6)

    # ---------- du lieu ----------

    def on_show(self):
        self.reload()

    def reload(self):
        customers = customer_model.search(self.keyword.get().strip())

        self.tree.delete(*self.tree.get_children())
        for customer in customers:
            name = customer["name"]
            if customer.get("vip"):
                name = "★ " + name
            self.tree.insert(
                "", "end", iid=customer["phone"],
                values=(
                    name,
                    customer["phone"],
                    customer.get("visits", 0),
                    money(customer.get("total_spent", 0)),
                    dt(customer.get("last_order_at")),
                ),
            )

        theme.stripe_rows(self.tree)
        self.empty_hint.refresh()
        self.summary.config(text=f"Tìm thấy {len(customers)} khách hàng.")

    def clear_filters(self):
        self.keyword.delete(0, "end")
        self.reload()

    def add_customer(self):
        dialog = CustomerCreateDialog(self)
        self.wait_window(dialog)
        if dialog.created_phone:
            audit_service.log("Thêm khách hàng", dialog.created_name)
            widgets.toast(self, f"Đã thêm khách hàng \"{dialog.created_name}\"")
            self.reload()

    def show_history(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một khách hàng.")
            return
        phone = selection[0]
        customer = customer_model.get_by_phone(phone)
        if not customer:
            self.reload()
            return
        CustomerHistoryDialog(self, customer)

    def edit_info(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một khách hàng.")
            return
        customer = customer_model.get_by_phone(selection[0])
        if not customer:
            self.reload()
            return

        dialog = CustomerEditDialog(self, customer)
        self.wait_window(dialog)
        if dialog.saved:
            audit_service.log("Cập nhật khách hàng", customer["name"])
            widgets.toast(self, f"Đã cập nhật \"{customer['name']}\"")
            self.reload()


class CustomerCreateDialog(tk.Toplevel):
    """Them khach hang bang tay (khac voi tu dong ghi nhan khi thanh toan) —
    dung khi da co so dien thoai khach truoc (vd hoi qua dien thoai) va
    muon luu san ho so, chua can cho lan mua dau tien."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Thêm khách hàng")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.configure(background=theme.BG)
        self.created_phone = None
        self.created_name = None

        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)

        self.fields = {}
        for key, label in [("phone", "Số điện thoại"), ("name", "Họ tên"),
                           ("email", "Email"), ("address", "Địa chỉ")]:
            ttk.Label(body, text=label).pack(anchor="w", pady=(4, 0))
            entry = ttk.Entry(body, width=32)
            entry.pack(fill="x")
            self.fields[key] = entry

        ttk.Label(body, text="Ghi chú").pack(anchor="w", pady=(4, 0))
        self.note = tk.Text(body, width=32, height=3)
        self.note.pack(fill="x", pady=(0, 6))

        self.vip = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="★ Khách VIP", variable=self.vip).pack(
            anchor="w", pady=(4, 10))

        buttons = ttk.Frame(body)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Thêm", style="Accent.TButton",
                   command=self._save).pack(side="left", expand=True,
                                            fill="x", padx=(0, 4))
        ttk.Button(buttons, text="Hủy", command=self.destroy).pack(
            side="left", expand=True, fill="x")

        self.bind("<Escape>", lambda e: self.destroy())
        self.fields["phone"].focus_set()
        self.grab_set()

    def _save(self):
        try:
            phone = parse_phone(self.fields["phone"].get())
            if not phone:
                raise ValidationError("Số điện thoại không được để trống.")
            name = require_text(self.fields["name"].get(), "Họ tên")
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc), parent=self)
            return

        if customer_model.phone_exists(phone):
            messagebox.showwarning(
                "Đã tồn tại",
                f"Số điện thoại {phone} đã có khách hàng khác.", parent=self)
            return

        customer_model.create_manual(
            phone, name,
            email=self.fields["email"].get().strip(),
            address=self.fields["address"].get().strip(),
            note=self.note.get("1.0", "end").strip(),
            vip=self.vip.get(),
        )
        self.created_phone = phone
        self.created_name = name
        self.destroy()


class CustomerEditDialog(tk.Toplevel):
    """Sua thong tin lien he va co VIP. Ten/SDT khong sua duoc o day: so
    dien thoai la khoa nhan dien khach, doi no se tach thanh khach khac."""

    def __init__(self, parent, customer: dict):
        super().__init__(parent)
        self.title(f"Sửa thông tin — {customer['name']}")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.configure(background=theme.BG)
        self.customer = customer
        self.saved = False

        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text=f"{customer['name']} · {customer['phone']}",
                  style="Section.TLabel").pack(anchor="w", pady=(0, 10))

        self.fields = {}
        for key, label in [("name", "Họ tên"), ("email", "Email"),
                           ("address", "Địa chỉ")]:
            ttk.Label(body, text=label).pack(anchor="w", pady=(4, 0))
            entry = ttk.Entry(body, width=32)
            entry.insert(0, customer.get(key, ""))
            entry.pack(fill="x")
            self.fields[key] = entry

        ttk.Label(body, text="Ghi chú").pack(anchor="w", pady=(4, 0))
        self.note = tk.Text(body, width=32, height=3)
        self.note.insert("1.0", customer.get("note", ""))
        self.note.pack(fill="x", pady=(0, 6))

        self.vip = tk.BooleanVar(value=bool(customer.get("vip")))
        ttk.Checkbutton(body, text="★ Khách VIP", variable=self.vip).pack(
            anchor="w", pady=(4, 10))

        buttons = ttk.Frame(body)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Lưu", style="Accent.TButton",
                   command=self._save).pack(side="left", expand=True,
                                            fill="x", padx=(0, 4))
        ttk.Button(buttons, text="Hủy", command=self.destroy).pack(
            side="left", expand=True, fill="x")

        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()

    def _save(self):
        try:
            name = require_text(self.fields["name"].get(), "Họ tên")
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc), parent=self)
            return

        customer_model.update_info(self.customer["phone"], {
            "name": name,
            "email": self.fields["email"].get().strip(),
            "address": self.fields["address"].get().strip(),
            "note": self.note.get("1.0", "end").strip(),
            "vip": self.vip.get(),
        })
        self.saved = True
        self.destroy()


class CustomerHistoryDialog(tk.Toplevel):
    """Lich su mua cua mot khach. Double-click mot don de mo chi tiet."""

    def __init__(self, parent, customer: dict):
        super().__init__(parent)
        self.title(f"Lịch sử mua — {customer['name']}")
        self.geometry("640x460")
        self.transient(parent.winfo_toplevel())
        self.configure(background=theme.BG)

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text=customer["name"],
                  style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            body,
            text=f"{customer['phone']} · {customer.get('visits', 0)} lần mua · "
                 f"tổng chi tiêu {money(customer.get('total_spent', 0))}",
            style="Muted.TLabel").pack(anchor="w", pady=(0, 12))

        table = ttk.Frame(body)
        table.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table, columns=[c[0] for c in HISTORY_COLUMNS], show="headings")
        for key, title, width in HISTORY_COLUMNS:
            self.tree.heading(key, text=title)
            anchor = "e" if key in ("quantity", "total") else "w"
            self.tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.tree)

        self.tree.tag_configure("cancelled", foreground=theme.MUTED)

        self.orders = {str(o["_id"]): o for o in order_model.by_phone(
            customer["phone"])}
        for order in self.orders.values():
            cancelled = order.get("status") == "cancelled"
            self.tree.insert(
                "", "end", iid=str(order["_id"]),
                tags=("cancelled",) if cancelled else (),
                values=(
                    order["order_code"],
                    dt(order["created_at"]),
                    sum(item["quantity"] for item in order["items"]),
                    money(order["total"]),
                    order_status_label(order),
                ),
            )

        self.tree.bind("<Double-1>", self._open_detail)
        ttk.Button(body, text="Đóng", command=self.destroy).pack(pady=(12, 0))

        self.grab_set()

    def _open_detail(self, _event):
        selection = self.tree.selection()
        if selection and selection[0] in self.orders:
            OrderDetailDialog(self, self.orders[selection[0]])
