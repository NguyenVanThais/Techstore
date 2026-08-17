"""Man hinh thong ke: 4 the so lieu va 3 bieu do.

Moi lan ve lai phai HUY canvas cu truoc (_clear_chart), neu khong cac
FigureCanvasTkAgg se chong len nhau va ro ri bo nho.
"""
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.services import excel_service, report_service
from app.utils.formatters import money, money_short
from app.utils.validators import ValidationError, parse_date
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title
from app.views.widgets import OptionalDateEntry

# Font Unicode: khong co dong nay thi chu tieng Viet co dau thanh o vuong.
matplotlib.rcParams["font.family"] = "DejaVu Sans"

PERIODS = [("Theo ngày", "day"), ("Theo tháng", "month"), ("Theo năm", "year")]

CARDS = [
    ("revenue", "Doanh thu", "#d64545"),
    ("profit", "Lợi nhuận", "#1f9d6b"),
    ("orders", "Số hóa đơn", "#2f6fed"),
    ("products_sold", "Sản phẩm đã bán", "#d98b1f"),
    ("avg_order", "Trung bình mỗi đơn", "#8b5cf6"),
]

# Mau cho bieu do tron: khac biet ro ca khi in den trang, du cho 5 danh muc
# va van con du neu sau nay them danh muc moi.
PIE_COLORS = ["#2f6fed", "#1f9d6b", "#d98b1f", "#8b5cf6", "#d64545",
              "#0e9aa7", "#c2185b", "#5d6d7e"]


class DashboardView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.canvases: dict[str, FigureCanvasTkAgg] = {}

        make_title(self, "Thống kê doanh thu",
                   "Số liệu tính trực tiếp trên MongoDB bằng aggregation pipeline")
        self._build_filters()
        self._build_cards()
        self._build_charts()

    # ---------- giao dien ----------

    def _build_filters(self):
        bar = ttk.LabelFrame(self, text="Khoảng thời gian", padding=10)
        bar.pack(fill="x", pady=(0, 10))

        ttk.Label(bar, text="Từ ngày").grid(row=0, column=0, padx=4)
        self.date_from = OptionalDateEntry(bar, width=11)
        self.date_from.grid(row=0, column=1, padx=4)

        ttk.Label(bar, text="đến ngày").grid(row=0, column=2, padx=4)
        self.date_to = OptionalDateEntry(bar, width=11)
        self.date_to.grid(row=0, column=3, padx=4)

        ttk.Label(bar, text="Nhóm").grid(row=0, column=4, padx=(12, 4))
        self.period = ttk.Combobox(bar, width=12, state="readonly",
                                   values=[p[0] for p in PERIODS])
        self.period.set("Theo tháng")
        self.period.grid(row=0, column=5, padx=4)
        self.period.bind("<<ComboboxSelected>>", lambda e: self.reload())

        ttk.Button(bar, text="Xem", command=self.reload).grid(row=0, column=6, padx=6)
        ttk.Button(bar, text="Xóa lọc", command=self.clear_filters).grid(row=0, column=7)
        ttk.Button(bar, text="Xuất Excel",
                   command=self.export_excel).grid(row=0, column=8, padx=(12, 0))

        widgets.date_presets(bar, self.date_from, self.date_to, self.reload).grid(
            row=1, column=0, columnspan=9, sticky="w", pady=(8, 0))
        ttk.Label(bar, text="Bấm mũi tên để chọn ngày từ lịch. Để trống để xem toàn bộ. "
                            "Thống kê không tính các đơn đã hủy.",
                  style="Muted.TLabel").grid(row=2, column=0, columnspan=9,
                                             sticky="w", pady=(6, 0))

    def _build_cards(self):
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 14))

        self.card_values: dict[str, ttk.Label] = {}
        for index, (key, label, color) in enumerate(CARDS):
            row.columnconfigure(index, weight=1, uniform="card")

            outer = ttk.Frame(row, style="Card.TFrame")
            outer.grid(row=0, column=index, sticky="ew",
                       padx=(0 if index == 0 else 6, 0))

            # vach mau ben trai de phan biet tung the
            tk.Frame(outer, background=color, width=4).pack(side="left", fill="y")

            inner = ttk.Frame(outer, style="Card.TFrame", padding=(14, 12))
            inner.pack(side="left", fill="both", expand=True)

            ttk.Label(inner, text=label.upper(), style="CardTitle.TLabel").pack(
                anchor="w")
            value = ttk.Label(inner, text="—", style="CardValue.TLabel",
                              foreground=color)
            value.pack(anchor="w", pady=(4, 0))
            self.card_values[key] = value

    def _build_charts(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)

        self.chart_frames = {}
        for key, title in [("period", "Doanh thu theo thời gian"),
                           ("category", "Tỷ trọng theo danh mục"),
                           ("products", "Top sản phẩm bán chạy"),
                           ("customers", "Top khách hàng")]:
            frame = ttk.Frame(self.tabs)
            self.tabs.add(frame, text=title)
            self.chart_frames[key] = frame

    # ---------- du lieu ----------

    def on_show(self):
        self.reload()

    def _read_range(self):
        date_from = parse_date(self.date_from.get(), "Từ ngày")
        date_to = parse_date(self.date_to.get(), "Đến ngày")
        if date_from and date_to and date_from > date_to:
            raise ValidationError("'Từ ngày' phải trước 'đến ngày'.")
        return date_from, date_to

    def _group_by(self) -> str:
        label = self.period.get()
        return next((v for l, v in PERIODS if l == label), "month")

    def reload(self):
        try:
            date_from, date_to = self._read_range()
        except ValidationError as exc:
            messagebox.showwarning("Bộ lọc không hợp lệ", str(exc))
            return

        stats = report_service.summary(date_from, date_to)
        self.card_values["revenue"].config(text=money(stats["revenue"]))
        self.card_values["profit"].config(text=money(stats["profit"]))
        self.card_values["orders"].config(text=str(stats["orders"]))
        self.card_values["products_sold"].config(text=str(stats["products_sold"]))
        self.card_values["avg_order"].config(text=money(stats["avg_order"]))

        self._draw_period(date_from, date_to)
        self._draw_category(date_from, date_to)
        self._draw_products(date_from, date_to)
        self._draw_customers(date_from, date_to)

    def clear_filters(self):
        self.date_from.delete(0, "end")
        self.date_to.delete(0, "end")
        self.period.set("Theo tháng")
        self.reload()

    def export_excel(self):
        """Bao cao 4 sheet theo dung bo loc dang chon."""
        try:
            date_from, date_to = self._read_range()
        except ValidationError as exc:
            messagebox.showwarning("Bộ lọc không hợp lệ", str(exc))
            return
        try:
            path = excel_service.export_report(date_from, date_to,
                                               self._group_by())
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không xuất được Excel:\n{exc}")
            return

        from app.views.order_view import _offer_open
        _offer_open(self, "Đã xuất báo cáo thống kê vào:", path)

    # ---------- bieu do ----------

    def _clear_chart(self, key: str):
        """Huy canvas cu. Thieu buoc nay thi bieu do cu van nam do."""
        canvas = self.canvases.pop(key, None)
        if canvas:
            canvas.get_tk_widget().destroy()
            canvas.figure.clf()

    def _figure(self):
        """Nen bieu do trung mau voi nen tab, khong co vien thua."""
        figure = Figure(figsize=(8, 4.2), dpi=96, facecolor=theme.SURFACE)
        axes = figure.add_subplot(111)
        axes.set_facecolor(theme.SURFACE)
        for side in ("top", "right"):
            axes.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            axes.spines[side].set_color(theme.BORDER)
        axes.tick_params(colors=theme.MUTED, labelsize=9)
        axes.yaxis.label.set_color(theme.MUTED)
        axes.xaxis.label.set_color(theme.MUTED)
        return figure, axes

    def _attach(self, key: str, figure: Figure):
        canvas = FigureCanvasTkAgg(figure, master=self.chart_frames[key])
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvases[key] = canvas

    def _empty(self, key: str, message: str):
        figure, axes = self._figure()
        axes.text(0.5, 0.5, message, ha="center", va="center",
                  color=theme.MUTED, fontsize=11)
        axes.axis("off")
        self._attach(key, figure)

    def _draw_period(self, date_from, date_to):
        self._clear_chart("period")
        rows = report_service.revenue_by_period(self._group_by(), date_from, date_to)
        if not rows:
            self._empty("period", "Không có dữ liệu trong khoảng này.")
            return

        labels = [r["_id"] for r in rows]
        values = [r["revenue"] for r in rows]

        figure, axes = self._figure()
        axes.plot(labels, values, marker="o", markersize=4,
                  color=theme.PRIMARY, linewidth=2)
        axes.fill_between(labels, values, alpha=0.08, color=theme.PRIMARY)
        axes.set_ylabel("Doanh thu (VNĐ)")
        axes.grid(axis="y", alpha=0.25, color=theme.BORDER)
        axes.set_axisbelow(True)
        axes.yaxis.set_major_formatter(lambda v, _: money_short(v))

        # nhieu moc thi xoay nhan cho khoi de len nhau
        if len(labels) > 8:
            axes.tick_params(axis="x", rotation=45, labelsize=8)
        figure.tight_layout()
        self._attach("period", figure)

    def _draw_category(self, date_from, date_to):
        self._clear_chart("category")
        rows = report_service.revenue_by_category(date_from, date_to)
        if not rows:
            self._empty("category", "Không có dữ liệu trong khoảng này.")
            return

        figure, axes = self._figure()
        for side in axes.spines.values():
            side.set_visible(False)
        axes.tick_params(left=False, bottom=False, labelleft=False,
                         labelbottom=False)

        values = [r["revenue"] for r in rows]

        def percent(pct):
            """Lat qua nho thi khong ve so: chu se tran ra ngoai va de len nhau."""
            return f"{pct:.1f}%" if pct >= 5 else ""

        wedges, _texts, autotexts = axes.pie(
            values,
            autopct=percent,
            pctdistance=0.72,
            startangle=90,
            colors=PIE_COLORS,
            wedgeprops={"edgecolor": theme.SURFACE, "linewidth": 2},
        )
        for label in autotexts:
            label.set_color("#ffffff")
            label.set_fontweight("bold")
            label.set_fontsize(9)

        total = sum(values)
        # Chu giai ben phai thay cho nhan quanh vanh: ten danh muc dai se
        # de len nhau khi hai lat nam sat canh.
        axes.legend(
            wedges,
            [f"{r['_id']}  ·  {money_short(r['revenue'])}  ({r['revenue'] / total:.1%})"
             for r in rows],
            loc="center left", bbox_to_anchor=(1.02, 0.5),
            frameon=False, fontsize=9, labelcolor=theme.TEXT,
        )
        axes.axis("equal")
        figure.subplots_adjust(left=0.02, right=0.62)
        self._attach("category", figure)

    def _draw_products(self, date_from, date_to):
        self._clear_chart("products")
        rows = report_service.top_products(10, date_from, date_to)
        if not rows:
            self._empty("products", "Không có dữ liệu trong khoảng này.")
            return

        rows = list(reversed(rows))   # barh ve tu duoi len
        figure, axes = self._figure()
        bars = axes.barh([r["_id"] for r in rows], [r["quantity"] for r in rows],
                         color=theme.SUCCESS, height=0.65)
        axes.bar_label(bars, padding=3, fontsize=8, color=theme.MUTED)
        axes.set_xlabel("Số lượng đã bán")
        axes.tick_params(axis="y", labelsize=8)
        axes.grid(axis="x", alpha=0.25, color=theme.BORDER)
        axes.set_axisbelow(True)
        axes.margins(x=0.12)
        figure.tight_layout()
        self._attach("products", figure)

    def _draw_customers(self, date_from, date_to):
        self._clear_chart("customers")
        rows = report_service.top_customers(10, date_from, date_to)
        if not rows:
            self._empty("customers", "Không có khách hàng nào trong khoảng này.\n"
                                     "(Chỉ tính các đơn có số điện thoại.)")
            return

        rows = list(reversed(rows))   # barh ve tu duoi len
        figure, axes = self._figure()
        labels = [f"{r['name']} · {r['_id']}" for r in rows]
        bars = axes.barh(labels, [r["revenue"] for r in rows],
                         color="#8b5cf6", height=0.65)
        axes.bar_label(bars, padding=3, fontsize=8, color=theme.MUTED,
                       labels=[money_short(r["revenue"]) for r in rows])
        axes.set_xlabel("Tổng chi tiêu (đã trừ hoàn trả)")
        axes.tick_params(axis="y", labelsize=8)
        axes.grid(axis="x", alpha=0.25, color=theme.BORDER)
        axes.set_axisbelow(True)
        axes.margins(x=0.14)
        axes.xaxis.set_major_formatter(lambda v, _: money_short(v))
        figure.tight_layout()
        self._attach("customers", figure)
