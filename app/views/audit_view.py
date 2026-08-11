"""Man nhat ky hoat dong: chi doc, khong sua/xoa duoc tu giao dien."""
from tkinter import ttk

from app.services import audit_service
from app.utils.formatters import dt
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title

COLUMNS = [
    ("created_at", "Thời gian", 130),
    ("user", "Người thực hiện", 120),
    ("role", "Vai trò", 80),
    ("action", "Hành động", 140),
    ("detail", "Nội dung", 300),
]

ROLE_LABELS = {"admin": "Quản lý", "staff": "Nhân viên"}


class AuditView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        make_title(self, "Nhật ký hoạt động",
                   "500 hoạt động gần nhất — ai làm gì, lúc nào")
        self._build_filters()
        self._build_table()

    def _build_filters(self):
        bar = ttk.LabelFrame(self, text="Tìm kiếm", padding=10)
        bar.pack(fill="x", pady=(0, 10))

        ttk.Label(bar, text="Người dùng / hành động / nội dung").grid(
            row=0, column=0, padx=4)
        self.keyword = ttk.Entry(bar, width=34)
        self.keyword.grid(row=0, column=1, padx=4)
        self.keyword.bind("<Return>", lambda e: self.reload())
        widgets.debounce_search(self.keyword, self.reload)

        ttk.Button(bar, text="Tìm", style="Accent.TButton",
                   command=self.reload).grid(row=0, column=2, padx=6)
        ttk.Button(bar, text="Xóa lọc", command=self.clear_filters).grid(
            row=0, column=3)

    def _build_table(self):
        self.summary = ttk.Label(self, style="Section.TLabel")
        self.summary.pack(anchor="w", pady=(0, 8))

        table = ttk.Frame(self)
        table.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table, columns=[c[0] for c in COLUMNS],
                                 show="headings")
        for key, title, width in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w")

        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.tree, stretch_column="detail")

        theme.configure_stripes(self.tree)
        self.empty_hint = widgets.EmptyHint(
            self.tree, "Chưa có hoạt động nào được ghi nhận.")

    def on_show(self):
        self.reload()

    def reload(self):
        rows = audit_service.recent(self.keyword.get().strip())

        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert(
                "", "end",
                values=(
                    dt(row["created_at"]),
                    row.get("user", ""),
                    ROLE_LABELS.get(row.get("role"), row.get("role", "")),
                    row.get("action", ""),
                    row.get("detail", ""),
                ),
            )
        theme.stripe_rows(self.tree)
        self.empty_hint.refresh()
        self.summary.config(text=f"Hiện {len(rows)} hoạt động.")

    def clear_filters(self):
        self.keyword.delete(0, "end")
        self.reload()
