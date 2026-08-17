"""Màn hình quản lý danh mục: thêm, sửa, xóa.

Sản phẩm lưu danh mục bằng TÊN, nên đổi tên danh mục sẽ kéo theo việc cập nhật
mọi sản phẩm đang dùng tên cũ (xử lý trong category_model.update).
"""
import tkinter as tk
from tkinter import messagebox, ttk

from app.models import category as category_model
from app.utils.validators import ValidationError, require_text
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title

COLUMNS = [
    ("name", "Tên danh mục", 220),
    ("description", "Mô tả", 380),
    ("products", "Số sản phẩm", 110),
]


class CategoryView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.selected_id = None

        make_title(self, "Quản lý danh mục",
                   "Đổi tên danh mục sẽ cập nhật luôn các sản phẩm đang dùng tên đó")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_table(body)
        self._build_form(body)

    def _build_table(self, parent):
        table = ttk.Frame(parent)
        table.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.tree = ttk.Treeview(table, columns=[c[0] for c in COLUMNS],
                                 show="headings")
        for key, title, width in COLUMNS:
            self.tree.heading(key, text=title)
            anchor = "e" if key == "products" else "w"
            self.tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.tree, stretch_column="description")

        # khong ke soc o day: dong da co tag 'empty' rieng
        self.tree.tag_configure("empty", foreground=theme.MUTED)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_form(self, parent):
        form = ttk.LabelFrame(parent, text="Thông tin danh mục", padding=12)
        form.grid(row=0, column=1, sticky="nsew")

        ttk.Label(form, text="Tên danh mục").grid(row=0, column=0, sticky="w", pady=4)
        self.name = ttk.Entry(form, width=24)
        self.name.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(form, text="Mô tả").grid(row=2, column=0, sticky="w", pady=4)
        self.description = tk.Text(form, width=24, height=5)
        self.description.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        self.hint = ttk.Label(form, text="", style="Muted.TLabel", wraplength=200,
                              justify="left")
        self.hint.grid(row=4, column=0, sticky="w", pady=(0, 8))

        buttons = ttk.Frame(form)
        buttons.grid(row=5, column=0, sticky="ew")
        ttk.Button(buttons, text="Thêm mới", style="Accent.TButton",
                   command=self.create).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Cập nhật", command=self.update).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Xóa", style="Danger.TButton",
                   command=self.delete).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Làm mới form",
                   command=self.clear_form).pack(fill="x", pady=2)

    # ---------- dữ liệu ----------

    def on_show(self):
        self.reload()

    def reload(self):
        self.tree.delete(*self.tree.get_children())
        for category in category_model.list_all():
            count = category_model.product_count(category["name"])
            self.tree.insert(
                "", "end", iid=str(category["_id"]),
                tags=() if count else ("empty",),
                values=(category["name"],
                        category.get("description", ""),
                        count),
            )

    def _on_select(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = selection[0]
        category = category_model.get(self.selected_id)
        if not category:
            return

        self.name.delete(0, "end")
        self.name.insert(0, category["name"])
        self.description.delete("1.0", "end")
        self.description.insert("1.0", category.get("description", ""))

        count = category_model.product_count(category["name"])
        self.hint.config(
            text=f"Đang có {count} sản phẩm thuộc danh mục này. "
                 "Đổi tên sẽ cập nhật luôn các sản phẩm đó."
            if count else "Chưa có sản phẩm nào dùng danh mục này."
        )

    def clear_form(self):
        self.selected_id = None
        self.name.delete(0, "end")
        self.description.delete("1.0", "end")
        self.hint.config(text="")
        self.tree.selection_remove(*self.tree.selection())

    def _read_form(self) -> tuple[str, str]:
        name = require_text(self.name.get(), "Tên danh mục", max_len=60)
        return name, self.description.get("1.0", "end").strip()

    # ---------- thao tác ----------

    def create(self):
        try:
            name, description = self._read_form()
            if category_model.name_exists(name):
                raise ValidationError("Tên danh mục đã tồn tại.")
            category_model.create(name, description)
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thêm được danh mục:\n{exc}")
            return

        widgets.toast(self, f"Đã thêm danh mục \"{name}\"")
        self.clear_form()
        self.reload()

    def update(self):
        if not self.selected_id:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một danh mục trong bảng.")
            return

        old = category_model.get(self.selected_id)
        try:
            name, description = self._read_form()
            if category_model.name_exists(name, exclude_id=self.selected_id):
                raise ValidationError("Tên danh mục đã tồn tại.")
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return

        count = category_model.product_count(old["name"])
        if old["name"] != name and count:
            confirm = messagebox.askyesno(
                "Xác nhận đổi tên",
                f"Đổi '{old['name']}' thành '{name}'?\n\n"
                f"{count} sản phẩm sẽ được chuyển sang tên mới.\n"
                "Hóa đơn cũ giữ nguyên tên danh mục tại thời điểm bán.",
            )
            if not confirm:
                return

        try:
            category_model.update(self.selected_id, name, description)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không cập nhật được:\n{exc}")
            return

        widgets.toast(self, f"Đã cập nhật danh mục \"{name}\"")
        self.reload()

    def delete(self):
        if not self.selected_id:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một danh mục trong bảng.")
            return

        category = category_model.get(self.selected_id)
        count = category_model.product_count(category["name"])
        if count:
            messagebox.showwarning(
                "Không xóa được",
                f"Còn {count} sản phẩm thuộc danh mục '{category['name']}'.\n"
                "Hãy chuyển các sản phẩm đó sang danh mục khác trước.",
            )
            return

        if not messagebox.askyesno("Xác nhận xóa",
                                   f"Xóa danh mục '{category['name']}'?"):
            return

        category_model.delete(self.selected_id)
        widgets.toast(self, f"Đã xóa danh mục \"{category['name']}\"")
        self.clear_form()
        self.reload()
