"""Man hinh ton kho: canh bao san pham duoi muc toi thieu."""
from tkinter import messagebox, ttk

from app.models import product as product_model
from app.services import audit_service
from app.utils.formatters import money
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title

COLUMNS = [
    ("sku", "Mã SP", 75),
    ("name", "Tên sản phẩm", 260),
    ("category", "Danh mục", 110),
    ("price", "Giá bán", 105),
    ("stock", "Tồn kho", 70),
    ("min_stock", "Tồn tối thiểu", 90),
    ("status", "Trạng thái", 100),
]


class InventoryView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        make_title(self, "Quản lý tồn kho",
                   "Sản phẩm có tồn kho thấp hơn hoặc bằng mức tối thiểu")

        self.summary = ttk.Label(self, style="Section.TLabel")
        self.summary.pack(anchor="w", pady=(0, 10))

        table = ttk.Frame(self)
        table.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table, columns=[c[0] for c in COLUMNS],
                                 show="headings")
        for key, title, width in COLUMNS:
            self.tree.heading(key, text=title)
            anchor = "e" if key in ("price", "stock", "min_stock") else "w"
            self.tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.tree, stretch_column="name")

        # to mau theo muc do
        self.tree.tag_configure("out", background=theme.OUT_OF_STOCK)
        self.tree.tag_configure("low", background=theme.LOW_STOCK)
        self.empty_hint = widgets.EmptyHint(
            self.tree, "Không có sản phẩm nào dưới mức tối thiểu.\n"
                       "Tồn kho đang ổn định 🎉")

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Nhập nhanh (không ghi phiếu)",
                   command=self.restock).pack(side="left")
        ttk.Button(actions, text="Lập phiếu nhập", style="Accent.TButton",
                   command=self.go_purchase).pack(side="left", padx=6)
        ttk.Button(actions, text="Tải lại",
                   command=self.reload).pack(side="left")

    def on_show(self):
        self.reload()

    def reload(self):
        products = product_model.low_stock()

        self.tree.delete(*self.tree.get_children())
        out_of_stock = 0
        for product in products:
            if product["stock"] == 0:
                tags, status = ("out",), "HẾT HÀNG"
                out_of_stock += 1
            else:
                tags, status = ("low",), "Sắp hết"

            self.tree.insert(
                "", "end", iid=str(product["_id"]), tags=tags,
                values=(
                    product.get("sku", ""),
                    product["name"],
                    product["category"],
                    money(product["price"]),
                    product["stock"],
                    product.get("min_stock", 0),
                    status,
                ),
            )

        self.empty_hint.refresh()
        self.summary.config(
            text=f"Có {len(products)} sản phẩm cần nhập thêm, "
                 f"trong đó {out_of_stock} sản phẩm đã hết hàng."
        )

    def restock(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một sản phẩm.")
            return

        product_id = selection[0]
        product = product_model.get(product_id)

        quantity = widgets.ask_quantity(
            self, "Nhập thêm hàng",
            f"Nhập số lượng thêm cho '{product['name']}'\n"
            f"(tồn kho hiện tại: {product['stock']})",
            initial=10, minvalue=1, maxvalue=10000,
        )
        if not quantity:
            return

        product_model.restock(product_id, quantity)
        audit_service.log("Nhập nhanh tồn kho",
                          f"{product['name']} +{quantity}")
        widgets.toast(self, f"Đã nhập thêm {quantity} — tồn kho mới: "
                            f"{product['stock'] + quantity}")
        self.reload()
        self.app.refresh_stock_badge()

    def go_purchase(self):
        """Nhay sang man Nhap hang, dien san san pham dang chon (neu co)
        — lap phieu co ghi nha cung cap va gia nhap, khac voi nut nhanh o tren."""
        selection = self.tree.selection()
        product = product_model.get(selection[0]) if selection else None
        self.app.show("purchases")
        if product:
            self.app.frames["purchases"].preselect(product)
