"""Man hinh nha cung cap: them, sua, xoa, xem thong ke nhap hang.

Phieu nhap nhung TEN nha cung cap tai thoi diem nhap nen sua / xoa o day
khong lam sai lich su nhap cu (giong quan he hoa don - san pham).
"""
import tkinter as tk
from tkinter import messagebox, ttk

from app.models import supplier as supplier_model
from app.services import audit_service
from app.utils.formatters import money
from app.utils.validators import ValidationError, parse_phone, require_text
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title

COLUMNS = [
    ("name", "Nhà cung cấp", 220),
    ("phone", "Điện thoại", 110),
    ("email", "Email", 170),
    ("address", "Địa chỉ", 220),
    ("count", "Số phiếu nhập", 100),
    ("total", "Tổng tiền nhập", 130),
]


class SupplierView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.selected_id = None

        make_title(self, "Nhà cung cấp",
                   "Chọn nhà cung cấp khi lập phiếu nhập — lịch sử nhập cũ "
                   "giữ nguyên tên tại thời điểm nhập")
        self._build_filters()

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_table(body)
        self._build_form(body)

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

    def _build_table(self, parent):
        table = ttk.Frame(parent)
        table.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.tree = ttk.Treeview(table, columns=[c[0] for c in COLUMNS],
                                 show="headings")
        for key, title, width in COLUMNS:
            self.tree.heading(key, text=title)
            anchor = "e" if key in ("count", "total") else "w"
            self.tree.column(key, width=width, anchor=anchor)

        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.tree, stretch_column="address")

        theme.configure_stripes(self.tree)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.empty_hint = widgets.EmptyHint(
            self.tree, "Chưa có nhà cung cấp nào.\nThêm bằng form bên phải.")

    def _build_form(self, parent):
        form = ttk.LabelFrame(parent, text="Thông tin nhà cung cấp", padding=12)
        form.grid(row=0, column=1, sticky="nsew")
        form.columnconfigure(0, weight=1)

        self.fields = {}
        for key, label in [("name", "Tên nhà cung cấp"), ("phone", "Điện thoại"),
                           ("email", "Email"), ("address", "Địa chỉ")]:
            ttk.Label(form, text=label).pack(anchor="w", pady=(4, 0))
            entry = ttk.Entry(form, width=26)
            entry.pack(fill="x", pady=(0, 4))
            self.fields[key] = entry

        ttk.Label(form, text="Ghi chú").pack(anchor="w", pady=(4, 0))
        self.note = tk.Text(form, width=26, height=4)
        self.note.pack(fill="x", pady=(0, 8))

        buttons = ttk.Frame(form)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Thêm mới", style="Accent.TButton",
                   command=self.create).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Cập nhật", command=self.update).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Xóa", style="Danger.TButton",
                   command=self.delete).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Làm mới form",
                   command=self.clear_form).pack(fill="x", pady=2)

    # ---------- du lieu ----------

    def on_show(self):
        self.reload()

    def reload(self):
        self.tree.delete(*self.tree.get_children())
        for supplier in supplier_model.list_all(self.keyword.get().strip()):
            stats = supplier_model.purchase_stats(supplier["name"])
            self.tree.insert(
                "", "end", iid=str(supplier["_id"]),
                values=(
                    supplier["name"],
                    supplier.get("phone", ""),
                    supplier.get("email", ""),
                    supplier.get("address", ""),
                    stats["count"],
                    money(stats["total"]),
                ),
            )
        theme.stripe_rows(self.tree)
        self.empty_hint.refresh()

    def clear_filters(self):
        self.keyword.delete(0, "end")
        self.reload()

    # ---------- form ----------

    def _on_select(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = selection[0]
        supplier = supplier_model.get(self.selected_id)
        if not supplier:
            return
        for key, entry in self.fields.items():
            entry.delete(0, "end")
            entry.insert(0, supplier.get(key, ""))
        self.note.delete("1.0", "end")
        self.note.insert("1.0", supplier.get("note", ""))

    def clear_form(self):
        self.selected_id = None
        for entry in self.fields.values():
            entry.delete(0, "end")
        self.note.delete("1.0", "end")
        self.tree.selection_remove(*self.tree.selection())

    def _read_form(self) -> dict:
        return {
            "name": require_text(self.fields["name"].get(),
                                 "Tên nhà cung cấp", max_len=100),
            "phone": parse_phone(self.fields["phone"].get()),
            "email": self.fields["email"].get().strip(),
            "address": self.fields["address"].get().strip(),
            "note": self.note.get("1.0", "end").strip(),
        }

    # ---------- thao tac ----------

    def create(self):
        try:
            data = self._read_form()
            if supplier_model.name_exists(data["name"]):
                raise ValidationError("Tên nhà cung cấp đã tồn tại.")
            supplier_model.create(data)
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thêm được nhà cung cấp:\n{exc}")
            return

        audit_service.log("Thêm nhà cung cấp", data["name"])
        widgets.toast(self, f"Đã thêm nhà cung cấp \"{data['name']}\"")
        self.clear_form()
        self.reload()

    def update(self):
        if not self.selected_id:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một nhà cung cấp trong bảng.")
            return
        try:
            data = self._read_form()
            if supplier_model.name_exists(data["name"], exclude_id=self.selected_id):
                raise ValidationError("Tên nhà cung cấp đã tồn tại.")
            supplier_model.update(self.selected_id, data)
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không cập nhật được:\n{exc}")
            return

        audit_service.log("Cập nhật nhà cung cấp", data["name"])
        widgets.toast(self, f"Đã cập nhật \"{data['name']}\"")
        self.reload()

    def delete(self):
        if not self.selected_id:
            messagebox.showinfo("Chưa chọn", "Hãy chọn một nhà cung cấp trong bảng.")
            return

        supplier = supplier_model.get(self.selected_id)
        stats = supplier_model.purchase_stats(supplier["name"])
        note = (f"\n\nĐã có {stats['count']} phiếu nhập từ nhà cung cấp này — "
                "các phiếu đó vẫn giữ nguyên tên cũ." if stats["count"] else "")
        if not messagebox.askyesno("Xác nhận xóa",
                                   f"Xóa nhà cung cấp '{supplier['name']}'?{note}"):
            return

        supplier_model.delete(self.selected_id)
        audit_service.log("Xóa nhà cung cấp", supplier["name"])
        widgets.toast(self, f"Đã xóa \"{supplier['name']}\"")
        self.clear_form()
        self.reload()
