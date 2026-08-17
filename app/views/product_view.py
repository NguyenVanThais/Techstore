"""Man hinh quan ly san pham: them, sua, xoa, phan loai, tim kiem."""
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from app.config import BASE_DIR, IMAGES_DIR
from app.models import category as category_model
from app.models import product as product_model
from app.services import audit_service
from app.utils.formatters import money
from app.utils.validators import (
    ValidationError, parse_price, parse_quantity, require_text,
)
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title

COLUMNS = [
    ("sku", "Mã SP", 70),
    ("name", "Tên sản phẩm", 210),
    ("category", "Danh mục", 100),
    ("price", "Giá bán", 100),
    ("cost", "Giá vốn", 95),
    ("stock", "Tồn kho", 60),
    ("min_stock", "Tồn tối thiểu", 80),
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
        widgets.debounce_search(self.keyword, self.reload)

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
        # minsize BAT BUOC cho cot form: Treeview co stretch=True nen tu
        # dan cot ra chiem het phan duoc chia theo weight, neu khong ep
        # minsize thi cot form co the bi ep con gan 0px tren man hinh hep.
        body.columnconfigure(0, weight=3, minsize=520)
        body.columnconfigure(1, weight=1, minsize=290)
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
            anchor = "e" if key in ("price", "cost", "stock", "min_stock") else "w"
            self.tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table_frame, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.tree, stretch_column="name")

        self.tree.tag_configure("out", background=theme.OUT_OF_STOCK)
        self.tree.tag_configure("low", background=theme.LOW_STOCK)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.empty_hint = widgets.EmptyHint(
            self.tree, "Không tìm thấy sản phẩm nào.\nThử từ khóa khác hoặc "
                       "bấm \"Xóa lọc\".")

        # form: khung ngoai co vien + tieu de, nut Them/Sua/Xoa GHIM DAY
        # truoc (khong bao gio bi che), phan truong nhap cuon duoc o giua
        # — man hinh thap hay them truong sau nay khong lam mat nut nua.
        form_container = ttk.LabelFrame(body, text="Thông tin sản phẩm",
                                        padding=(12, 8))
        form_container.grid(row=0, column=1, sticky="nsew")

        buttons = ttk.Frame(form_container)
        buttons.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Thêm mới", style="Accent.TButton",
                   command=self.create).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Cập nhật", command=self.update).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Xóa", style="Danger.TButton",
                   command=self.delete).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Làm mới form", command=self.clear_form).pack(
            fill="x", pady=2)

        scroller = widgets.ScrollableFrame(form_container, width=260)
        scroller.pack(side="top", fill="both", expand=True)
        form = scroller.body

        self.fields = {}
        rows = [
            ("sku", "Mã sản phẩm"),
            ("name", "Tên sản phẩm"),
            ("price", "Giá bán"),
            ("cost", "Giá vốn"),
            ("stock", "Tồn kho"),
            ("min_stock", "Tồn tối thiểu"),
        ]
        for index, (key, label) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=index, column=0, sticky="w", pady=4)
            entry = ttk.Entry(form, width=19)
            entry.grid(row=index, column=1, pady=4)
            self.fields[key] = entry

        ttk.Label(form, text="Danh mục").grid(row=6, column=0, sticky="w", pady=4)
        self.category_box = ttk.Combobox(form, width=16, state="readonly")
        self.category_box.grid(row=6, column=1, pady=4)

        ttk.Label(form, text="Mô tả").grid(row=7, column=0, sticky="nw", pady=4)
        self.description = tk.Text(form, width=19, height=4)
        self.description.grid(row=7, column=1, pady=4)

        # yeu thich: noi len dau danh sach o man Ban hang
        self.favorite = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="★ Yêu thích (hiện đầu màn Bán hàng)",
                        variable=self.favorite).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=4)

        # anh xem truoc: giu tham chieu PhotoImage trong self._photo,
        # khong thi Tk hien o trang vi anh bi garbage-collect ngay
        self._photo = None
        self.image_preview = ttk.Label(form, anchor="center")
        self.image_preview.grid(row=9, column=0, columnspan=2, pady=(8, 2))

        self.image_label = ttk.Label(form, text="Chưa chọn ảnh",
                                     style="Muted.TLabel")
        self.image_label.grid(row=10, column=0, columnspan=2, pady=2)
        ttk.Button(form, text="Chọn ảnh...", command=self._pick_image).grid(
            row=11, column=0, columnspan=2, pady=4, sticky="ew")

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

            name = product["name"]
            if product.get("favorite"):
                name = "★ " + name
            self.tree.insert(
                "", "end", iid=str(product["_id"]), tags=tags,
                values=(
                    product.get("sku", ""),
                    name,
                    product["category"],
                    money(product["price"]),
                    money(product.get("cost", 0) or 0),
                    product["stock"],
                    product.get("min_stock", 0),
                ),
            )
        self.empty_hint.refresh()

    def _sort_key(self, key: str, value: str):
        """Gia ban hien thi la '29.990.000 đ' -- so sanh chuoi se cho ra
        '29 trieu' < '3.9 trieu'. Phai doi nguoc ve so truoc khi sap xep.
        Chi giu chu so nen khong phu thuoc vao ky hieu tien te."""
        if key in ("price", "cost"):
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
        self.fields["cost"].delete(0, "end")
        self.fields["cost"].insert(0, int(product.get("cost", 0) or 0))
        self.favorite.set(bool(product.get("favorite")))
        self.fields["stock"].delete(0, "end")
        self.fields["stock"].insert(0, product["stock"])
        self.fields["min_stock"].delete(0, "end")
        self.fields["min_stock"].insert(0, product.get("min_stock", 0))
        self.category_box.set(product["category"])
        self.description.delete("1.0", "end")
        self.description.insert("1.0", product.get("description", ""))

        self.image_path = product.get("image_path", "")
        self._show_image()

    def _show_image(self):
        """Ve anh thu nho cua self.image_path len form (hoac xoa neu khong co)."""
        name = Path(self.image_path).name if self.image_path else ""
        full = BASE_DIR / self.image_path if self.image_path else None

        if full and full.is_file():
            try:
                image = Image.open(full)
                image.thumbnail((150, 110))
                self._photo = ImageTk.PhotoImage(image)
                self.image_preview.config(image=self._photo)
                self.image_label.config(text=name)
                return
            except Exception:
                pass   # file hong -> roi xuong nhanh "khong doc duoc"

        self._photo = None
        self.image_preview.config(image="")
        self.image_label.config(
            text=f"{name} (không đọc được ảnh)" if name else "Chưa chọn ảnh")

    def clear_form(self):
        self.selected_id = None
        self.image_path = ""
        for entry in self.fields.values():
            entry.delete(0, "end")
        self.category_box.set("")
        self.description.delete("1.0", "end")
        self.favorite.set(False)
        self._show_image()
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
        self._show_image()

    def _read_form(self) -> dict:
        return {
            "sku": self.fields["sku"].get().strip().upper(),
            "name": require_text(self.fields["name"].get(), "Tên sản phẩm"),
            "category": require_text(self.category_box.get(), "Danh mục"),
            "price": parse_price(self.fields["price"].get(), "Giá bán"),
            "cost": parse_price(self.fields["cost"].get() or "0", "Giá vốn"),
            "favorite": self.favorite.get(),
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
            if data["sku"] and product_model.sku_exists(data["sku"]):
                raise ValidationError(f"Mã sản phẩm '{data['sku']}' đã tồn tại.")
            product_model.create(data)
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thêm được sản phẩm:\n{exc}")
            return

        audit_service.log("Thêm sản phẩm", data["name"])
        widgets.toast(self, f"Đã thêm sản phẩm \"{data['name']}\"")
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
            if data["sku"] and product_model.sku_exists(
                    data["sku"], exclude_id=self.selected_id):
                raise ValidationError(f"Mã sản phẩm '{data['sku']}' đã tồn tại.")
            product_model.update(self.selected_id, data)
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không cập nhật được:\n{exc}")
            return

        audit_service.log("Cập nhật sản phẩm", data["name"])
        widgets.toast(self, f"Đã cập nhật \"{data['name']}\"")
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
        audit_service.log("Xóa sản phẩm", product["name"])
        widgets.toast(self, f"Đã xóa \"{product['name']}\"")
        self.clear_form()
        self.reload()
        self.app.refresh_stock_badge()
