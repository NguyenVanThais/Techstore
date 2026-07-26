"""Man hinh ban hang: chon san pham ben trai, gio hang ben phai.

Gio hang chi nam trong bo nho (sales_service.Cart) cho toi khi bam Thanh toan.
Luc do checkout() moi tru ton kho va ghi don xuong Mongo.
"""
from tkinter import messagebox, ttk

from app.models import category as category_model
from app.models import customer as customer_model
from app.models import product as product_model
from app.services.sales_service import Cart, OutOfStockError, checkout
from app.utils.formatters import money
from app.utils.validators import ValidationError, parse_phone, parse_price
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title

PRODUCT_COLUMNS = [
    ("sku", "Mã SP", 80),
    ("name", "Tên sản phẩm", 240),
    ("price", "Giá bán", 120),
    ("stock", "Còn lại", 70),
]

CART_COLUMNS = [
    ("name", "Sản phẩm", 165),
    ("price", "Đơn giá", 100),
    ("quantity", "SL", 40),
    ("subtotal", "Thành tiền", 110),
]


class SalesView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.cart = Cart()

        make_title(self, "Bán hàng",
                   "Giỏ hàng chỉ ghi xuống database khi bấm Thanh toán")

        panes = ttk.PanedWindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True)

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=3)
        panes.add(right, weight=2)

        self._build_products(left)
        self._build_cart(right)

    # ---------- ben trai: danh sach san pham ----------

    def _build_products(self, parent):
        bar = ttk.LabelFrame(parent, text="Tìm sản phẩm", padding=8)
        bar.pack(fill="x", pady=(0, 8))

        ttk.Label(bar, text="Từ khóa").grid(row=0, column=0, padx=4)
        self.keyword = ttk.Entry(bar, width=18)
        self.keyword.grid(row=0, column=1, padx=4)
        # go den dau loc den do; Enter = quet ma: khop dung SKU thi them
        # thang vao gio (may quet ma vach gui chuoi + Enter y het go phim)
        widgets.debounce_search(self.keyword, self.reload_products)
        self.keyword.bind("<Return>", lambda e: self._on_keyword_enter())

        ttk.Label(bar, text="Danh mục").grid(row=0, column=2, padx=4)
        self.category_filter = ttk.Combobox(bar, width=13, state="readonly")
        self.category_filter.grid(row=0, column=3, padx=4)
        self.category_filter.bind("<<ComboboxSelected>>",
                                  lambda e: self.reload_products())

        ttk.Button(bar, text="Tìm", style="Accent.TButton",
                   command=self.reload_products).grid(row=0, column=4, padx=6)
        ttk.Button(bar, text="Xóa lọc", command=self.clear_filters).grid(
            row=0, column=5)

        table = ttk.Frame(parent)
        table.pack(fill="both", expand=True)

        self.products = ttk.Treeview(
            table, columns=[c[0] for c in PRODUCT_COLUMNS], show="headings")
        for key, title, width in PRODUCT_COLUMNS:
            self.products.heading(key, text=title)
            anchor = "e" if key in ("price", "stock") else "w"
            self.products.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical",
                               command=self.products.yview)
        self.products.configure(yscrollcommand=scroll.set)
        self.products.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.products, stretch_column="name")

        self.products.tag_configure("out", background=theme.OUT_OF_STOCK)
        self.products.bind("<Double-1>", lambda e: self.add_to_cart())
        self.products_hint = widgets.EmptyHint(
            self.products, "Không tìm thấy sản phẩm nào.\nThử từ khóa khác "
                           "hoặc bấm \"Xóa lọc\".")

        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Thêm vào giỏ", style="Accent.TButton",
                   command=self.add_to_cart).pack(side="left")
        ttk.Label(actions, text="double-click sản phẩm, hoặc gõ mã SKU + Enter",
                  style="Muted.TLabel").pack(side="left", padx=10)

    # ---------- ben phai: gio hang ----------

    def _build_cart(self, parent):
        ttk.Label(parent, text="Giỏ hàng",
                  style="Section.TLabel").pack(anchor="w", pady=(0, 6))

        # Neo khoi thanh toan vao DAY truoc, roi moi cho bang gio hang an het
        # cho con lai. Neu pack bang truoc, no se an het chieu cao va day nut
        # THANH TOAN ra ngoai man hinh khi cua so thap.
        totals = ttk.LabelFrame(parent, text="Thanh toán", padding=8)
        totals.pack(side="bottom", fill="x")
        totals.columnconfigure(1, weight=1)

        customer = ttk.LabelFrame(parent, text="Khách hàng", padding=8)
        customer.pack(side="bottom", fill="x", pady=(6, 8))
        customer.columnconfigure(1, weight=1)

        buttons = ttk.Frame(parent)
        buttons.pack(side="bottom", fill="x", pady=8)
        ttk.Button(buttons, text="＋", width=3, style="Icon.TButton",
                   command=lambda: self._change_quantity(1)).pack(side="left")
        ttk.Button(buttons, text="－", width=3, style="Icon.TButton",
                   command=lambda: self._change_quantity(-1)).pack(side="left", padx=4)
        ttk.Button(buttons, text="Sửa số lượng",
                   command=self.edit_quantity).pack(side="left", padx=4)
        ttk.Button(buttons, text="Bỏ khỏi giỏ",
                   command=self.remove_from_cart).pack(side="left", padx=4)
        ttk.Button(buttons, text="Xóa hết", style="Danger.TButton",
                   command=self.clear_cart).pack(side="right")

        table = ttk.Frame(parent)
        table.pack(fill="both", expand=True)

        self.cart_tree = ttk.Treeview(
            table, columns=[c[0] for c in CART_COLUMNS], show="headings")
        for key, title, width in CART_COLUMNS:
            self.cart_tree.heading(key, text=title)
            anchor = "e" if key in ("price", "quantity", "subtotal") else "w"
            self.cart_tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical",
                               command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=scroll.set)
        self.cart_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.cart_tree, stretch_column="name")

        self.cart_tree.bind("<Double-1>", lambda e: self.edit_quantity())

        ttk.Label(customer, text="Họ tên").grid(row=0, column=0, sticky="w", pady=3)
        self.customer_name = ttk.Entry(customer)
        self.customer_name.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=3)

        ttk.Label(customer, text="Điện thoại").grid(row=1, column=0, sticky="w", pady=3)
        self.customer_phone = ttk.Entry(customer)
        self.customer_phone.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=3)
        self.customer_phone.bind("<KeyRelease>", self._lookup_customer)

        # nhan dien khach quen theo so dien thoai, tu dien ten
        self.customer_hint = ttk.Label(customer, text="", style="Muted.TLabel")
        self.customer_hint.grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Label(totals, text="Tạm tính").grid(row=0, column=0, sticky="w", pady=3)
        self.subtotal_label = ttk.Label(totals, text=money(0))
        self.subtotal_label.grid(row=0, column=1, sticky="e", pady=3)

        ttk.Label(totals, text="Giảm giá").grid(row=1, column=0, sticky="w", pady=3)
        self.discount = ttk.Entry(totals, width=14, justify="right")
        self.discount.grid(row=1, column=1, sticky="e", pady=3)
        self.discount.bind("<KeyRelease>", lambda e: self._refresh_totals())

        ttk.Separator(totals).grid(row=2, column=0, columnspan=2,
                                   sticky="ew", pady=6)

        ttk.Label(totals, text="Tổng cộng",
                  font=theme.FONT_SECTION).grid(row=3, column=0, sticky="w")
        self.total_label = ttk.Label(totals, text=money(0),
                                     font=(theme.FAMILY, 15, "bold"),
                                     foreground=theme.DANGER)
        self.total_label.grid(row=3, column=1, sticky="e")

        ttk.Button(totals, text="THANH TOÁN", style="Big.Accent.TButton",
                   command=self.do_checkout).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))

    # ---------- du lieu ----------

    def on_show(self):
        self.reload_categories()
        self.reload_products()
        self.refresh_cart()

    def reload_categories(self):
        names = category_model.list_names()
        self.category_filter["values"] = ["Tất cả"] + names
        if not self.category_filter.get():
            self.category_filter.set("Tất cả")

    def reload_products(self):
        category = self.category_filter.get()
        if category == "Tất cả":
            category = ""

        products = product_model.search(
            keyword=self.keyword.get().strip(), category=category)

        self.products.delete(*self.products.get_children())
        for product in products:
            name = product["name"]
            if product.get("favorite"):
                name = "★ " + name
            self.products.insert(
                "", "end", iid=str(product["_id"]),
                tags=("out",) if product["stock"] == 0 else (),
                values=(
                    product.get("sku", ""),
                    name,
                    money(product["price"]),
                    product["stock"],
                ),
            )
        self.products_hint.refresh()

    def _on_keyword_enter(self):
        """Enter o o tim kiem: neu chuoi khop DUNG mot ma SKU thi them thang
        vao gio va xoa o tim de quet ma tiep theo; khong thi chi loc bang."""
        code = self.keyword.get().strip().upper()
        if code:
            products = product_model.search(keyword=code)
            hits = [p for p in products if p.get("sku", "").upper() == code]
            if len(hits) == 1:
                if self._add_product(hits[0]):
                    self.keyword.delete(0, "end")
                self.reload_products()
                return
        self.reload_products()

    def _lookup_customer(self, _event=None):
        """Nhap du so dien thoai cua khach cu -> tu dien ten, bao khach quen."""
        phone = self.customer_phone.get().strip()
        if len(phone) < 9:
            self.customer_hint.config(text="")
            return
        customer = customer_model.get_by_phone(phone)
        if not customer:
            self.customer_hint.config(text="")
            return
        if not self.customer_name.get().strip():
            self.customer_name.insert(0, customer["name"])
        vip = "★ KHÁCH VIP · " if customer.get("vip") else ""
        self.customer_hint.config(
            text=f"{vip}Khách quen: đã mua {customer.get('visits', 0)} lần, "
                 f"tổng {money(customer.get('total_spent', 0))}")

    def clear_filters(self):
        self.keyword.delete(0, "end")
        self.category_filter.set("Tất cả")
        self.reload_products()

    # ---------- thao tac tren gio ----------

    def add_to_cart(self):
        selection = self.products.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một sản phẩm.")
            return

        # doc lai tu DB de lay ton kho moi nhat, tranh cong don theo so cu
        product = product_model.get(selection[0])
        if not product:
            messagebox.showwarning("Không tìm thấy", "Sản phẩm đã bị xóa.")
            self.reload_products()
            return

        self._add_product(product)

    def _add_product(self, product: dict) -> bool:
        """Them mot san pham vao gio, bao bang toast. Dung chung cho nut
        'Them vao gio' va duong quet ma SKU."""
        try:
            self.cart.add(product)
        except OutOfStockError as exc:
            messagebox.showwarning("Không đủ hàng", str(exc))
            return False

        self.refresh_cart()
        widgets.toast(self, f"Đã thêm \"{product['name']}\" vào giỏ")
        return True

    def _selected_cart_id(self) -> str | None:
        selection = self.cart_tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một dòng trong giỏ hàng.")
            return None
        return selection[0]

    def _quantity_of(self, product_id: str) -> int:
        for item in self.cart.items():
            if str(item["product_id"]) == product_id:
                return item["quantity"]
        return 0

    def _change_quantity(self, delta: int):
        product_id = self._selected_cart_id()
        if not product_id:
            return
        self._set_quantity(product_id, self._quantity_of(product_id) + delta)

    def edit_quantity(self):
        product_id = self._selected_cart_id()
        if not product_id:
            return
        quantity = widgets.ask_quantity(
            self, "Sửa số lượng", "Số lượng mới (0 để bỏ khỏi giỏ):",
            initial=self._quantity_of(product_id),
            minvalue=0, maxvalue=10000,
        )
        if quantity is None:
            return
        self._set_quantity(product_id, quantity)

    def _set_quantity(self, product_id: str, quantity: int):
        try:
            self.cart.set_quantity(product_id, quantity)
        except OutOfStockError as exc:
            messagebox.showwarning("Không đủ hàng", str(exc))
            return
        self.refresh_cart()

    def remove_from_cart(self):
        product_id = self._selected_cart_id()
        if not product_id:
            return
        self.cart.remove(product_id)
        self.refresh_cart()

    def clear_cart(self):
        if self.cart.is_empty():
            return
        if messagebox.askyesno("Xác nhận", "Bỏ toàn bộ sản phẩm trong giỏ?"):
            self.cart.clear()
            self.refresh_cart()

    # ---------- hien thi ----------

    def refresh_cart(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        for item in self.cart.items():
            self.cart_tree.insert(
                "", "end", iid=str(item["product_id"]),
                values=(
                    item["name"],
                    money(item["price"]),
                    item["quantity"],
                    money(item["subtotal"]),
                ),
            )
        self._refresh_totals()

    def _read_discount(self) -> float:
        """Doc o giam gia, tra ve 0 neu dang go do dang."""
        try:
            return parse_price(self.discount.get() or "0", "Giảm giá")
        except ValidationError:
            return 0.0

    def _refresh_totals(self):
        subtotal = self.cart.subtotal()
        total = max(subtotal - self._read_discount(), 0)
        self.subtotal_label.config(
            text=f"{money(subtotal)}  ({self.cart.total_quantity()} sản phẩm)")
        self.total_label.config(text=money(total))

    def _clear_customer(self):
        self.customer_name.delete(0, "end")
        self.customer_phone.delete(0, "end")
        self.discount.delete(0, "end")
        self.customer_hint.config(text="")

    # ---------- thanh toan ----------

    def do_checkout(self):
        if self.cart.is_empty():
            messagebox.showinfo("Giỏ trống", "Hãy thêm sản phẩm vào giỏ hàng.")
            return

        try:
            discount = parse_price(self.discount.get() or "0", "Giảm giá")
            phone = parse_phone(self.customer_phone.get())
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return

        subtotal = self.cart.subtotal()
        if discount > subtotal:
            messagebox.showwarning(
                "Giảm giá không hợp lệ",
                f"Giảm giá ({money(discount)}) lớn hơn tạm tính ({money(subtotal)}).")
            return

        name = self.customer_name.get().strip() or "Khách lẻ"
        total = subtotal - discount

        confirm = messagebox.askyesno(
            "Xác nhận thanh toán",
            f"Khách hàng: {name}\n"
            f"Số sản phẩm: {self.cart.total_quantity()}\n"
            f"Tổng cộng: {money(total)}\n\nTạo đơn hàng?",
        )
        if not confirm:
            return

        try:
            code = checkout(self.cart, {"name": name, "phone": phone}, discount)
        except OutOfStockError as exc:
            # checkout() da hoan tac phan ton kho da tru, chi can nap lai bang
            messagebox.showwarning("Không đủ hàng", str(exc))
            self.reload_products()
            return
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không tạo được đơn hàng:\n{exc}")
            return

        # thanh cong thi bao bang toast: ban 20 don khong phai bam OK 20 lan
        widgets.toast(self, f"Đã tạo đơn {code} · {money(total)}")

        self.cart.clear()
        self._clear_customer()
        self.refresh_cart()
        self.reload_products()
        self.app.refresh_stock_badge()
