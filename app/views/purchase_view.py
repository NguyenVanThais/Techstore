"""Man hinh nhap hang: lap phieu nhap va tra cuu lich su nhap.

Phieu dang go nam trong bo nho (purchase_service.PurchaseCart), chi ghi
xuong database khi bam TAO PHIEU NHAP — luc do moi cong ton kho va tinh
lai gia von binh quan cho tung san pham.
"""
import tkinter as tk
from tkinter import messagebox, ttk

from app.models import product as product_model
from app.models import purchase as purchase_model
from app.models import supplier as supplier_model
from app.services.purchase_service import PurchaseCart, create_receipt
from app.utils.formatters import dt, money
from app.utils.validators import ValidationError, parse_date, parse_price
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title
from app.views.widgets import OptionalDateEntry

PRODUCT_COLUMNS = [
    ("sku", "Mã SP", 80),
    ("name", "Tên sản phẩm", 230),
    ("stock", "Tồn kho", 70),
    ("cost", "Giá vốn hiện tại", 120),
]

RECEIPT_COLUMNS = [
    ("name", "Sản phẩm", 190),
    ("quantity", "SL", 45),
    ("cost", "Giá nhập", 100),
    ("subtotal", "Thành tiền", 110),
]

HISTORY_COLUMNS = [
    ("receipt_code", "Mã phiếu", 130),
    ("created_at", "Thời gian", 130),
    ("supplier", "Nhà cung cấp", 180),
    ("user", "Người lập", 130),
    ("quantity", "SL", 60),
    ("total", "Tổng tiền", 140),
]

DETAIL_COLUMNS = [
    ("sku", "Mã SP", 80),
    ("name", "Sản phẩm", 240),
    ("quantity", "SL", 50),
    ("cost", "Giá nhập", 110),
    ("subtotal", "Thành tiền", 120),
]


class PurchaseView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.cart = PurchaseCart()
        self._purchases: list[dict] = []

        make_title(self, "Nhập hàng",
                   "Phiếu nhập cộng tồn kho và cập nhật giá vốn "
                   "(bình quân gia quyền)")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        create_tab = ttk.Frame(self.tabs, padding=(0, 10, 0, 0))
        history_tab = ttk.Frame(self.tabs, padding=(0, 10, 0, 0))
        self.tabs.add(create_tab, text="Lập phiếu nhập")
        self.tabs.add(history_tab, text="Lịch sử nhập hàng")

        self._build_create_tab(create_tab)
        self._build_history_tab(history_tab)

    # ---------- tab 1: lap phieu ----------

    def _build_create_tab(self, parent):
        panes = ttk.PanedWindow(parent, orient="horizontal")
        panes.pack(fill="both", expand=True)

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=3)
        panes.add(right, weight=2)

        # ---- trai: tim san pham ----
        bar = ttk.LabelFrame(left, text="Tìm sản phẩm", padding=8)
        bar.pack(fill="x", pady=(0, 8))

        ttk.Label(bar, text="Từ khóa").grid(row=0, column=0, padx=4)
        self.keyword = ttk.Entry(bar, width=24)
        self.keyword.grid(row=0, column=1, padx=4)
        widgets.debounce_search(self.keyword, self.reload_products)
        self.keyword.bind("<Return>", lambda e: self.reload_products())

        ttk.Button(bar, text="Tìm", style="Accent.TButton",
                   command=self.reload_products).grid(row=0, column=2, padx=6)

        table = ttk.Frame(left)
        table.pack(fill="both", expand=True)

        self.products = ttk.Treeview(
            table, columns=[c[0] for c in PRODUCT_COLUMNS], show="headings")
        for key, title, width in PRODUCT_COLUMNS:
            self.products.heading(key, text=title)
            anchor = "e" if key in ("stock", "cost") else "w"
            self.products.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical",
                               command=self.products.yview)
        self.products.configure(yscrollcommand=scroll.set)
        self.products.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.products, stretch_column="name")

        self.products.bind("<Double-1>", lambda e: self.add_to_receipt())
        self.products_hint = widgets.EmptyHint(
            self.products, "Không tìm thấy sản phẩm nào.")

        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Thêm vào phiếu", style="Accent.TButton",
                   command=self.add_to_receipt).pack(side="left")
        ttk.Label(actions, text="double-click sản phẩm để thêm nhanh",
                  style="Muted.TLabel").pack(side="left", padx=10)

        # ---- phai: phieu nhap ----
        ttk.Label(right, text="Phiếu nhập",
                  style="Section.TLabel").pack(anchor="w", pady=(0, 6))

        # khoi tao phieu neo duoi cung truoc (giong man Ban hang):
        # bang chiem het phan con lai, khong day nut Tao phieu ra ngoai
        totals = ttk.LabelFrame(right, text="Thông tin phiếu", padding=8)
        totals.pack(side="bottom", fill="x")
        totals.columnconfigure(1, weight=1)

        buttons = ttk.Frame(right)
        buttons.pack(side="bottom", fill="x", pady=8)
        ttk.Button(buttons, text="Bỏ khỏi phiếu",
                   command=self.remove_from_receipt).pack(side="left")
        ttk.Button(buttons, text="Xóa hết", style="Danger.TButton",
                   command=self.clear_receipt).pack(side="right")

        table = ttk.Frame(right)
        table.pack(fill="both", expand=True)

        self.receipt_tree = ttk.Treeview(
            table, columns=[c[0] for c in RECEIPT_COLUMNS], show="headings")
        for key, title, width in RECEIPT_COLUMNS:
            self.receipt_tree.heading(key, text=title)
            anchor = "e" if key in ("quantity", "cost", "subtotal") else "w"
            self.receipt_tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical",
                               command=self.receipt_tree.yview)
        self.receipt_tree.configure(yscrollcommand=scroll.set)
        self.receipt_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.receipt_tree, stretch_column="name")

        ttk.Label(totals, text="Nhà cung cấp").grid(row=0, column=0,
                                                    sticky="w", pady=3)
        self.supplier_box = ttk.Combobox(totals, state="readonly")
        self.supplier_box.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=3)

        ttk.Label(totals, text="Ghi chú").grid(row=1, column=0, sticky="w", pady=3)
        self.note = ttk.Entry(totals)
        self.note.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=3)

        ttk.Separator(totals).grid(row=2, column=0, columnspan=2,
                                   sticky="ew", pady=6)
        ttk.Label(totals, text="Tổng tiền nhập",
                  font=theme.FONT_SECTION).grid(row=3, column=0, sticky="w")
        self.total_label = ttk.Label(totals, text=money(0),
                                     font=(theme.FAMILY, 15, "bold"),
                                     foreground=theme.PRIMARY)
        self.total_label.grid(row=3, column=1, sticky="e")

        ttk.Button(totals, text="TẠO PHIẾU NHẬP", style="Big.Accent.TButton",
                   command=self.do_create_receipt).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))

    # ---------- tab 2: lich su ----------

    def _build_history_tab(self, parent):
        bar = ttk.LabelFrame(parent, text="Bộ lọc", padding=10)
        bar.pack(fill="x", pady=(0, 10))

        ttk.Label(bar, text="Mã phiếu").grid(row=0, column=0, padx=4)
        self.filter_code = ttk.Entry(bar, width=16)
        self.filter_code.grid(row=0, column=1, padx=4)

        ttk.Label(bar, text="Nhà cung cấp").grid(row=0, column=2, padx=4)
        self.filter_supplier = ttk.Entry(bar, width=18)
        self.filter_supplier.grid(row=0, column=3, padx=4)

        ttk.Label(bar, text="Từ ngày").grid(row=0, column=4, padx=4)
        self.date_from = OptionalDateEntry(bar, width=11)
        self.date_from.grid(row=0, column=5, padx=4)

        ttk.Label(bar, text="đến ngày").grid(row=0, column=6, padx=4)
        self.date_to = OptionalDateEntry(bar, width=11)
        self.date_to.grid(row=0, column=7, padx=4)

        for entry in (self.filter_code, self.filter_supplier):
            entry.bind("<Return>", lambda e: self.reload_history())
            widgets.debounce_search(entry, self.reload_history)

        ttk.Button(bar, text="Tìm", style="Accent.TButton",
                   command=self.reload_history).grid(row=0, column=8, padx=6)
        ttk.Button(bar, text="Xóa lọc",
                   command=self.clear_history_filters).grid(row=0, column=9)

        widgets.date_presets(bar, self.date_from, self.date_to,
                             self.reload_history).grid(
            row=1, column=0, columnspan=10, sticky="w", pady=(8, 0))

        self.history_summary = ttk.Label(parent, style="Section.TLabel")
        self.history_summary.pack(anchor="w", pady=(0, 8))

        table = ttk.Frame(parent)
        table.pack(fill="both", expand=True)

        self.history_tree = ttk.Treeview(
            table, columns=[c[0] for c in HISTORY_COLUMNS], show="headings")
        for key, title, width in HISTORY_COLUMNS:
            self.history_tree.heading(key, text=title)
            anchor = "e" if key in ("quantity", "total") else "w"
            self.history_tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical",
                               command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.history_tree, stretch_column="supplier")

        theme.configure_stripes(self.history_tree)
        self.history_hint = widgets.EmptyHint(
            self.history_tree, "Chưa có phiếu nhập nào khớp bộ lọc.\n"
                               "Lập phiếu ở tab \"Lập phiếu nhập\".")
        self.history_tree.bind("<Double-1>", lambda e: self.show_detail())

        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Xem chi tiết", style="Accent.TButton",
                   command=self.show_detail).pack(side="left")
        ttk.Button(actions, text="Tải lại",
                   command=self.reload_history).pack(side="left", padx=6)

    # ---------- du lieu ----------

    def on_show(self):
        self.reload_products()
        self.reload_suppliers()
        self.reload_history()
        self.refresh_receipt()

    def reload_products(self):
        products = product_model.search(keyword=self.keyword.get().strip())
        self.products.delete(*self.products.get_children())
        for product in products:
            self.products.insert(
                "", "end", iid=str(product["_id"]),
                values=(
                    product.get("sku", ""),
                    product["name"],
                    product["stock"],
                    money(product.get("cost", 0) or 0),
                ),
            )
        self.products_hint.refresh()

    def reload_suppliers(self):
        names = supplier_model.list_names()
        self.supplier_box["values"] = names
        if names and not self.supplier_box.get():
            self.supplier_box.set(names[0])

    # ---------- thao tac tren phieu ----------

    def preselect(self, product: dict):
        """Duoc man Ton kho goi: nhay sang tab lap phieu voi san pham da chon."""
        self.tabs.select(0)
        self._ask_and_add(product)

    def add_to_receipt(self):
        selection = self.products.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một sản phẩm.")
            return
        product = product_model.get(selection[0])
        if not product:
            messagebox.showwarning("Không tìm thấy", "Sản phẩm đã bị xóa.")
            self.reload_products()
            return
        self._ask_and_add(product)

    def _ask_and_add(self, product: dict):
        result = AskQuantityCostDialog(
            self, product["name"],
            initial_cost=int(product.get("cost", 0) or 0),
            stock=product["stock"],
        ).result
        if not result:
            return
        quantity, cost = result
        try:
            self.cart.add(product, quantity, cost)
        except ValueError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return
        self.refresh_receipt()
        widgets.toast(self, f"Đã thêm \"{product['name']}\" x{quantity} vào phiếu")

    def remove_from_receipt(self):
        selection = self.receipt_tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một dòng trong phiếu.")
            return
        self.cart.remove(selection[0])
        self.refresh_receipt()

    def clear_receipt(self):
        if self.cart.is_empty():
            return
        if messagebox.askyesno("Xác nhận", "Bỏ toàn bộ sản phẩm trong phiếu?"):
            self.cart.clear()
            self.refresh_receipt()

    def refresh_receipt(self):
        self.receipt_tree.delete(*self.receipt_tree.get_children())
        for item in self.cart.items():
            self.receipt_tree.insert(
                "", "end", iid=str(item["product_id"]),
                values=(
                    item["name"],
                    item["quantity"],
                    money(item["cost"]),
                    money(item["subtotal"]),
                ),
            )
        self.total_label.config(text=money(self.cart.total()))

    def do_create_receipt(self):
        if self.cart.is_empty():
            messagebox.showinfo("Phiếu trống",
                                "Hãy thêm sản phẩm vào phiếu nhập.")
            return
        supplier = self.supplier_box.get().strip()
        if not supplier:
            messagebox.showwarning(
                "Thiếu nhà cung cấp",
                "Hãy chọn nhà cung cấp (thêm mới ở màn Nhà cung cấp).")
            return

        confirm = messagebox.askyesno(
            "Xác nhận nhập hàng",
            f"Nhà cung cấp: {supplier}\n"
            f"Số dòng sản phẩm: {len(self.cart.items())}\n"
            f"Tổng tiền: {money(self.cart.total())}\n\n"
            "Tồn kho sẽ được cộng và giá vốn sẽ được tính lại. Tạo phiếu?",
        )
        if not confirm:
            return

        try:
            code = create_receipt(self.cart, supplier, self.app.user,
                                  self.note.get())
        except ValueError as exc:
            messagebox.showwarning("Không tạo được phiếu", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không tạo được phiếu nhập:\n{exc}")
            return

        widgets.toast(self, f"Đã tạo phiếu nhập {code}")
        self.cart.clear()
        self.note.delete(0, "end")
        self.refresh_receipt()
        self.reload_products()
        self.reload_history()
        self.app.refresh_stock_badge()

    # ---------- lich su ----------

    def clear_history_filters(self):
        for entry in (self.filter_code, self.filter_supplier,
                      self.date_from, self.date_to):
            entry.delete(0, "end")
        self.reload_history()

    def reload_history(self):
        try:
            date_from = parse_date(self.date_from.get(), "Từ ngày")
            date_to = parse_date(self.date_to.get(), "Đến ngày")
        except ValidationError as exc:
            messagebox.showwarning("Bộ lọc không hợp lệ", str(exc))
            return

        purchases = purchase_model.search(
            code=self.filter_code.get().strip(),
            supplier=self.filter_supplier.get().strip(),
            date_from=date_from,
            date_to=date_to,
        )
        self._purchases = purchases

        self.history_tree.delete(*self.history_tree.get_children())
        total = 0.0
        for purchase in purchases:
            total += purchase["total"]
            self.history_tree.insert(
                "", "end", iid=str(purchase["_id"]),
                values=(
                    purchase["receipt_code"],
                    dt(purchase["created_at"]),
                    purchase["supplier"]["name"],
                    purchase["user"].get("display_name", ""),
                    sum(item["quantity"] for item in purchase["items"]),
                    money(purchase["total"]),
                ),
            )
        theme.stripe_rows(self.history_tree)
        self.history_hint.refresh()
        self.history_summary.config(
            text=f"Tìm thấy {len(purchases)} phiếu nhập, "
                 f"tổng tiền nhập {money(total)}.")

    def show_detail(self):
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một phiếu nhập.")
            return
        purchase = purchase_model.get(selection[0])
        if not purchase:
            messagebox.showwarning("Không tìm thấy", "Phiếu nhập đã bị xóa.")
            self.reload_history()
            return
        PurchaseDetailDialog(self, purchase)


class AskQuantityCostDialog(tk.Toplevel):
    """Hoi so luong + gia nhap khi them san pham vao phieu
    (mot hop thoai cho ca hai, khoi bam hai lan)."""

    def __init__(self, parent, product_name: str, initial_cost: int = 0,
                 stock: int = 0):
        super().__init__(parent)
        self.title("Thêm vào phiếu nhập")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.configure(background=theme.BG)
        self.result: tuple[int, float] | None = None

        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=product_name, style="Section.TLabel").pack(anchor="w")
        ttk.Label(body, text=f"Tồn kho hiện tại: {stock}",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 8))

        grid = ttk.Frame(body)
        grid.pack(fill="x", pady=(0, 6))
        ttk.Label(grid, text="Số lượng nhập").grid(row=0, column=0,
                                                   sticky="w", pady=3)
        self.quantity = ttk.Spinbox(grid, from_=1, to=100000, width=12,
                                    justify="right")
        self.quantity.grid(row=0, column=1, padx=(10, 0), pady=3)
        self.quantity.set(10)

        ttk.Label(grid, text="Giá nhập / cái").grid(row=1, column=0,
                                                    sticky="w", pady=3)
        self.cost = ttk.Entry(grid, width=14, justify="right")
        self.cost.grid(row=1, column=1, padx=(10, 0), pady=3)
        if initial_cost:
            self.cost.insert(0, initial_cost)

        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Thêm", style="Accent.TButton",
                   command=self._ok).pack(side="left", expand=True,
                                          fill="x", padx=(0, 4))
        ttk.Button(buttons, text="Hủy", command=self.destroy).pack(
            side="left", expand=True, fill="x")

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        top = parent.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_width()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self.cost.focus_set()
        self.grab_set()
        self.wait_window()

    def _ok(self):
        try:
            quantity = int(self.quantity.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Không hợp lệ",
                                   "Số lượng phải là số nguyên dương.",
                                   parent=self)
            return
        try:
            cost = parse_price(self.cost.get(), "Giá nhập")
        except ValidationError as exc:
            messagebox.showwarning("Không hợp lệ", str(exc), parent=self)
            return
        self.result = (quantity, cost)
        self.destroy()


class PurchaseDetailDialog(tk.Toplevel):
    def __init__(self, parent, purchase: dict):
        super().__init__(parent)
        self.title(f"Phiếu nhập {purchase['receipt_code']}")
        self.geometry("720x440")
        self.transient(parent.winfo_toplevel())
        self.configure(background=theme.BG)

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text=f"Phiếu nhập {purchase['receipt_code']}",
                  style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text=dt(purchase["created_at"]),
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

        info = ttk.LabelFrame(body, text="Thông tin phiếu", padding=8)
        info.pack(fill="x", pady=(0, 10))
        ttk.Label(info, text=f"Nhà cung cấp:  {purchase['supplier']['name']}"
                  ).pack(anchor="w")
        ttk.Label(info, text="Người lập:  "
                  f"{purchase['user'].get('display_name', '')}").pack(anchor="w")
        if purchase.get("note"):
            ttk.Label(info, text=f"Ghi chú:  {purchase['note']}").pack(anchor="w")

        table = ttk.Frame(body)
        table.pack(fill="both", expand=True)

        tree = ttk.Treeview(table, columns=[c[0] for c in DETAIL_COLUMNS],
                            show="headings", height=8)
        for key, title, width in DETAIL_COLUMNS:
            tree.heading(key, text=title)
            anchor = "e" if key in ("quantity", "cost", "subtotal") else "w"
            tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(tree, stretch_column="name")

        for item in purchase["items"]:
            tree.insert("", "end", values=(
                item.get("sku", ""),
                item["name"],
                item["quantity"],
                money(item["cost"]),
                money(item["subtotal"]),
            ))

        totals = ttk.Frame(body)
        totals.pack(fill="x", pady=(10, 0))
        totals.columnconfigure(0, weight=1)
        ttk.Label(totals, text="Tổng tiền nhập",
                  font=(theme.FAMILY, 13, "bold")).grid(row=0, column=0,
                                                        sticky="e", padx=8)
        ttk.Label(totals, text=money(purchase["total"]),
                  font=(theme.FAMILY, 13, "bold"),
                  foreground=theme.PRIMARY).grid(row=0, column=1, sticky="e")

        ttk.Button(body, text="Đóng", command=self.destroy).pack(pady=(14, 0))
        self.grab_set()
