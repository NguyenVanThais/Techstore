"""Man hinh quan ly san pham: them, sua, xoa, phan loai, tim kiem."""
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.config import IMAGES_DIR
from app.models import category as category_model
from app.models import product as product_model
from app.utils.formatters import money
from app.utils.validators import (
    ValidationError, parse_price, parse_quantity, require_text,
)
from app.views import theme
from app.views.base_frame import BaseFrame, make_title

COLUMNS = [
    ("sku", "Mã SP", 90),
    ("name", "Tên sản phẩm", 300),
    ("category", "Danh mục", 130),
    ("price", "Giá bán", 130),
    ("stock", "Tồn kho", 80),
    ("min_stock", "Tồn tối thiểu", 100),
]


class ProductView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.selected_id = None
        self.image_path = ""

        make_title(self, "Quản lý sản phẩm",
                   "Xóa sản phẩm là xóa mềm — hóa đơn cũ vẫn giữ nguyên")
        self._build_filters()
        self._build_body()

    # ---------- giao dien ----------

    def _build_filters(self):
        bar = ttk.LabelFrame(self, text="Tìm kiếm và lọc", padding=10)
        bar.pack(fill="x", pady=(0, 10))

        ttk.Label(bar, text="Từ khóa").grid(row=0, column=0, padx=4)
        self.keyword = ttk.Entry(bar, width=28)
        self.keyword.grid(row=0, column=1, padx=4)
        self.keyword.bind("<Return>", lambda e: self.reload())

        ttk.Label(bar, text="Danh mục").grid(row=0, column=2, padx=4)
        self.category_filter = ttk.Combobox(bar, width=18, state="readonly")
        self.category_filter.grid(row=0, column=3, padx=4)

        ttk.Label(bar, text="Giá từ").grid(row=0, column=4, padx=4)
        self.min_price = ttk.Entry(bar, width=12)
        self.min_price.grid(row=0, column=5, padx=4)

        ttk.Label(bar, text="đến").grid(row=0, column=6, padx=4)
        self.max_price = ttk.Entry(bar, width=12)
        self.max_price.grid(row=0, column=7, padx=4)

        ttk.Button(bar, text="Lọc", style="Accent.TButton",
                   command=self.reload).grid(row=0, column=8, padx=6)
        ttk.Button(bar, text="Xóa lọc", command=self.clear_filters).grid(row=0, column=9)

    def _build_body(self):
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # bang san pham
        table_frame = ttk.Frame(body)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.tree = ttk.Treeview(
            table_frame, columns=[c[0] for c in COLUMNS], show="headings",
        )
        for key, title, width in COLUMNS:
            self.tree.heading(key, text=title,
                              command=lambda k=key: self._sort_by(k))
            anchor = "e" if key in ("price", "stock", "min_stock") else "w"
            self.tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table_frame, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.tag_configure("out", background=theme.OUT_OF_STOCK)
        self.tree.tag_configure("low", background=theme.LOW_STOCK)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # form
        form = ttk.LabelFrame(body, text="Thông tin sản phẩm", padding=12)
        form.grid(row=0, column=1, sticky="nsew")

        self.fields = {}
        rows = [
            ("sku", "Mã sản phẩm"),
            ("name", "Tên sản phẩm"),
            ("price", "Giá bán"),
            ("stock", "Tồn kho"),
            ("min_stock", "Tồn tối thiểu"),
        ]
        for index, (key, label) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=index, column=0, sticky="w", pady=4)
            entry = ttk.Entry(form, width=24)
            entry.grid(row=index, column=1, pady=4)
            self.fields[key] = entry

        ttk.Label(form, text="Danh mục").grid(row=5, column=0, sticky="w", pady=4)
        self.category_box = ttk.Combobox(form, width=21, state="readonly")
        self.category_box.grid(row=5, column=1, pady=4)

        ttk.Label(form, text="Mô tả").grid(row=6, column=0, sticky="nw", pady=4)
        self.description = tk.Text(form, width=24, height=4)
        self.description.grid(row=6, column=1, pady=4)

        self.image_label = ttk.Label(form, text="Chưa chọn ảnh", foreground="gray")
        self.image_label.grid(row=7, column=0, columnspan=2, pady=4)
        ttk.Button(form, text="Chọn ảnh...", command=self._pick_image).grid(
            row=8, column=0, columnspan=2, pady=4, sticky="ew")

        buttons = ttk.Frame(form)
        buttons.grid(row=9, column=0, columnspan=2, pady=(14, 0), sticky="ew")
        ttk.Button(buttons, text="Thêm mới", style="Accent.TButton",
                   command=self.create).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Cập nhật", command=self.update).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Xóa", style="Danger.TButton",
                   command=self.delete).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Làm mới form", command=self.clear_form).pack(
            fill="x", pady=2)

    # ---------- du lieu ----------

    def on_show(self):
        self.reload_categories()
        self.reload()

    def reload_categories(self):
        names = category_model.list_names()
        self.category_box["values"] = names
        self.category_filter["values"] = ["Tất cả"] + names
        if not self.category_filter.get():
            self.category_filter.set("Tất cả")

    def reload(self):
        try:
            min_price = parse_price(self.min_price.get()) if self.min_price.get() else None
            max_price = parse_price(self.max_price.get()) if self.max_price.get() else None
        except ValidationError as exc:
            messagebox.showwarning("Lọc không hợp lệ", str(exc))
            return

        category = self.category_filter.get()
        if category == "Tất cả":
            category = ""

        products = product_model.search(
            keyword=self.keyword.get().strip(),
            category=category,
            min_price=min_price,
            max_price=max_price,
        )

        self.tree.delete(*self.tree.get_children())
        for product in products:
            if product["stock"] == 0:
                tags = ("out",)
            elif product["stock"] <= product.get("min_stock", 0):
                tags = ("low",)
            else:
                tags = ()

            self.tree.insert(
                "", "end", iid=str(product["_id"]), tags=tags,
                values=(
                    product.get("sku", ""),
                    product["name"],
                    product["category"],
                    money(product["price"]),
                    product["stock"],
                    product.get("min_stock", 0),
                ),
            )

    def _sort_key(self, key: str, value: str):
        """Gia ban hien thi la '29.990.000 đ' -- so sanh chuoi se cho ra
        '29 trieu' < '3.9 trieu'. Phai doi nguoc ve so truoc khi sap xep.
        Chi giu chu so nen khong phu thuoc vao ky hieu tien te."""
        if key == "price":
            return float("".join(c for c in value if c.isdigit()) or 0)
        if key in ("stock", "min_stock"):
            return int(value)
        return value.lower()

    def _sort_by(self, key: str):
        rows = [(self.tree.set(iid, key), iid) for iid in self.tree.get_children("")]
        rows.sort(key=lambda r: self._sort_key(key, r[0]))
        for index, (_, iid) in enumerate(rows):
            self.tree.move(iid, "", index)

    def clear_filters(self):
        self.keyword.delete(0, "end")
        self.min_price.delete(0, "end")
        self.max_price.delete(0, "end")
        self.category_filter.set("Tất cả")
        self.reload()

    # ---------- form ----------

    def _on_select(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = selection[0]
        product = product_model.get(self.selected_id)
        if not product:
            return

        self.fields["sku"].delete(0, "end")
        self.fields["sku"].insert(0, product.get("sku", ""))
        self.fields["name"].delete(0, "end")
        self.fields["name"].insert(0, product["name"])
        self.fields["price"].delete(0, "end")
        self.fields["price"].insert(0, int(product["price"]))
        self.fields["stock"].delete(0, "end")
        self.fields["stock"].insert(0, product["stock"])
        self.fields["min_stock"].delete(0, "end")
        self.fields["min_stock"].insert(0, product.get("min_stock", 0))
        self.category_box.set(product["category"])
        self.description.delete("1.0", "end")
        self.description.insert("1.0", product.get("description", ""))

        self.image_path = product.get("image_path", "")
        self.image_label.config(
            text=Path(self.image_path).name if self.image_path else "Chưa chọn ảnh")

    def clear_form(self):
        self.selected_id = None
        self.image_path = ""
        for entry in self.fields.values():
            entry.delete(0, "end")
        self.category_box.set("")
        self.description.delete("1.0", "end")
        self.image_label.config(text="Chưa chọn ảnh")
        self.tree.selection_remove(*self.tree.selection())

    def _pick_image(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh sản phẩm",
            filetypes=[("Ảnh", "*.png *.jpg *.jpeg *.webp")],
        )
        if not path:
            return
        # copy vao assets/images, chi luu duong dan tuong doi xuong Mongo
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        target = IMAGES_DIR / Path(path).name
        shutil.copy(path, target)
        self.image_path = f"assets/images/{target.name}"
        self.image_label.config(text=target.name)

    def _read_form(self) -> dict:
        return {
            "sku": self.fields["sku"].get().strip().upper(),
            "name": require_text(self.fields["name"].get(), "Tên sản phẩm"),
            "category": require_text(self.category_box.get(), "Danh mục"),
            "price": parse_price(self.fields["price"].get(), "Giá bán"),
            "stock": parse_quantity(self.fields["stock"].get(), "Tồn kho"),
            "min_stock": parse_quantity(
                self.fields["min_stock"].get() or "0", "Tồn tối thiểu"),
            "description": self.description.get("1.0", "end").strip(),
            "image_path": self.image_path,
        }

    # ---------- thao tac ----------

    def create(self):
        try:
            data = self._read_form()
            if product_model.name_exists(data["name"]):
                raise ValidationError("Tên sản phẩm đã tồn tại.")
            product_model.create(data)
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thêm được sản phẩm:\n{exc}")
            return

        messagebox.showinfo("Thành công", "Đã thêm sản phẩm.")
        self.clear_form()
        self.reload()
        self.app.refresh_stock_badge()

    def update(self):
        if not self.selected_id:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một sản phẩm trong bảng.")
            return
        try:
            data = self._read_form()
            if product_model.name_exists(data["name"], exclude_id=self.selected_id):
                raise ValidationError("Tên sản phẩm đã tồn tại.")
            product_model.update(self.selected_id, data)
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không cập nhật được:\n{exc}")
            return

        messagebox.showinfo("Thành công", "Đã cập nhật sản phẩm.")
        self.reload()
        self.app.refresh_stock_badge()

    def delete(self):
        if not self.selected_id:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một sản phẩm trong bảng.")
            return

        product = product_model.get(self.selected_id)
        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            f"Xóa sản phẩm '{product['name']}'?\n\n"
            "Sản phẩm sẽ được ẩn đi nhưng vẫn giữ trong các hóa đơn cũ.",
        )
        if not confirm:
            return

        product_model.soft_delete(self.selected_id)
        messagebox.showinfo("Đã xóa", "Sản phẩm đã được xóa.")
        self.clear_form()
        self.reload()
        self.app.refresh_stock_badge()
