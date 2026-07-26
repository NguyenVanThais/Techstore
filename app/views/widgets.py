"""Widget va tien ich giao dien dung chung cho cac man hinh."""
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

from tkcalendar import DateEntry

from app.views import theme


class OptionalDateEntry(DateEntry):
    """O chon ngay CHO PHEP DE TRONG.

    DateEntry goc coi o trong la khong hop le: mat focus la no tu dien lai
    ngay gan nhat (_validate_date goi _set_text). Voi bo loc cua app thi
    trong nghia la "khong loc theo ngay", nen phai cho qua truong hop nay.
    """

    def __init__(self, master=None, **kw):
        kw.setdefault("date_pattern", "dd/mm/yyyy")
        kw.setdefault("showweeknumbers", False)
        super().__init__(master, **kw)
        self.delete(0, "end")   # khoi dau rong, khong phai hom nay

    def _validate_date(self):
        if not self.get().strip():
            return True
        return super()._validate_date()

    def clear(self) -> None:
        self.delete(0, "end")


def toast(widget, message: str, kind: str = "success", ms: int = 2600) -> None:
    """Thong bao nho goc duoi phai, tu bien mat — thay cho messagebox
    voi cac thao tac THANH CONG, de nguoi dung khong phai bam OK lien tuc.
    Loi van dung messagebox vi loi thi can nguoi dung doc va xac nhan.
    """
    root = widget.winfo_toplevel()
    old = getattr(root, "_toast", None)
    if old is not None and old.winfo_exists():
        old.destroy()

    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    color = {"success": theme.SUCCESS, "danger": theme.DANGER,
             "info": theme.PRIMARY}.get(kind, theme.SUCCESS)
    tk.Label(win, text=message, bg=color, fg="#ffffff",
             font=theme.FONT_BOLD, padx=18, pady=10).pack()

    win.update_idletasks()
    x = root.winfo_rootx() + root.winfo_width() - win.winfo_width() - 28
    y = root.winfo_rooty() + root.winfo_height() - win.winfo_height() - 28
    win.geometry(f"+{x}+{y}")
    root._toast = win
    win.after(ms, win.destroy)


def debounce_search(entry, callback, delay_ms: int = 300):
    """Go den dau loc den do: doi nguoi dung ngung go delay_ms roi moi goi
    callback, de khong truy van MongoDB tren TUNG phim bam.

    Tra ve handler de kiem thu goi truc tiep duoc (cua so an khong nhan
    duoc su kien phim that).
    """
    def run():
        entry._debounce_id = None
        callback()

    def on_key(event):
        # Enter da co xu ly rieng (tim ngay / quet ma), khong can debounce
        if event.keysym in ("Return", "Tab", "Escape"):
            return
        pending = getattr(entry, "_debounce_id", None)
        if pending:
            entry.after_cancel(pending)
        entry._debounce_id = entry.after(delay_ms, run)

    entry.bind("<KeyRelease>", on_key, add="+")
    return on_key


class EmptyHint:
    """Dong chu huong dan hien giua bang khi bang khong co dong nao,
    de nguoi moi khong tuong app bi loi."""

    def __init__(self, tree, text: str):
        self.tree = tree
        self.label = ttk.Label(tree, text=text, style="Empty.TLabel",
                               justify="center")

    def refresh(self) -> None:
        if self.tree.get_children(""):
            self.label.place_forget()
        else:
            self.label.place(relx=0.5, rely=0.35, anchor="center")


def date_presets(parent, date_from: OptionalDateEntry,
                 date_to: OptionalDateEntry, on_change) -> ttk.Frame:
    """Day nut chon nhanh khoang ngay: 90% nhu cau la may khoang co dinh nay,
    mot cu click thay vi mo lich hai lan."""

    def _today():
        d = date.today()
        return d, d

    def _last7():
        d = date.today()
        return d - timedelta(days=6), d

    def _this_month():
        d = date.today()
        return d.replace(day=1), d

    def _all():
        return None, None

    def apply(bounds):
        start, end = bounds
        date_from.clear()
        date_to.clear()
        if start:
            date_from.set_date(start)
        if end:
            date_to.set_date(end)
        on_change()

    frame = ttk.Frame(parent)
    for label, fn in [("Hôm nay", _today), ("7 ngày qua", _last7),
                      ("Tháng này", _this_month), ("Tất cả", _all)]:
        ttk.Button(frame, text=label, style="Chip.TButton",
                   command=lambda fn=fn: apply(fn())).pack(side="left", padx=(0, 4))
    return frame


def add_grid_lines(tree: ttk.Treeview, stretch_column: str | None = None) -> None:
    """Ve duong ke DOC mong giua cac cot, kieu bang tinh, va TAT stretch tren
    cac cot con lai — ttk.Treeview mac dinh moi cot tu gian ra chia het
    khoang trong thua, khien bang trong lung lung va khoang cach giua cac
    cot khong deu.

    `stretch_column`: ten cot (thuong la cot chu dai nhat — ten san pham,
    ten khach...) duoc GIU stretch=True de hut het khoang trong con lai;
    khong truyen thi moi cot deu co dinh, phan thua ben phai de trong (hop
    voi dialog nho co kich thuoc co dinh, khong hop voi bang chiem het man
    hinh vi se de lai khoang trong xau).

    ttk.Treeview khong co tuy chon ke o noi bo nhu Excel qua style, nen
    duong ke phai chong tk.Frame 1px len tren, tinh lai vi tri moi khi bang
    doi kich thuoc hoac nguoi dung keo dan cot.
    """
    for col in tree["columns"]:
        tree.column(col, stretch=(col == stretch_column))

    parent = tree.master
    lines: list[tk.Frame] = []

    def redraw(_event=None):
        if not tree.winfo_exists():
            return
        for line in lines:
            line.destroy()
        lines.clear()

        columns = tree["columns"]
        if not columns:
            return
        x = tree.winfo_x()
        for col in columns[:-1]:   # khong ke sau cot cuoi cung
            x += tree.column(col, "width")
            line = tk.Frame(parent, background=theme.BORDER)
            line.place(x=x, y=tree.winfo_y(), width=1, height=tree.winfo_height())
            lines.append(line)

    # <Configure> bat duoc khi bang doi kich thuoc (resize cua so, doi man
    # hinh); <ButtonRelease-1> bat khi nguoi dung keo dan bien cot bang tay.
    tree.bind("<Configure>", redraw, add="+")
    tree.bind("<ButtonRelease-1>", redraw, add="+")
    tree.after(30, redraw)   # lan render dau tien, cho layout on dinh


class ScrollableFrame(ttk.Frame):
    """Khung cuon doc: dung khi noi dung ben trong (form nhieu truong...)
    co the cao hon khong gian hien thi tren man hinh thap. Widget con dat
    vao `.body`, dung y het mot ttk.Frame binh thuong.

    LUU Y ve be rong: noi dung that (self.body) nam trong mot canvas thong
    qua create_window, nen kich thuoc no KHONG lan truyen len canvas theo
    co che grid/pack binh thuong. Neu khong khai bao `width`, canvas se lay
    kich thuoc mac dinh rat nho (~200) lam co so tinh toan cho grid/pack cua
    widget CHA — cha se cap cho khung nay it hon nhieu so voi noi dung that
    can, khien moi thu ben trong bien mat. Vi vay BAT BUOC truyen `width`
    xap xi be rong noi dung can, tru khi cha da ep kich thuoc bang cach khac
    (vd body.columnconfigure(.., minsize=...))."""

    def __init__(self, parent, width: int = 260, **kwargs):
        super().__init__(parent, **kwargs)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        canvas = tk.Canvas(self, background=theme.BG, highlightthickness=0,
                           width=width)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        self.body = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=self.body, anchor="nw")

        # noi dung cao hon canvas -> scrollregion phai theo kich thuoc that
        # cua noi dung, khong phai kich thuoc canvas
        self.body.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        # canvas rong ra (vd resize cua so) thi khung ben trong dan theo be
        # rong moi, khong de trang mot khoang canh phai
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(window, width=e.width))

        # chuot cuon chi hoat dong khi tro dang o TREN khung nay, tranh
        # gianh scroll voi Treeview/Text khac dang mo cung luc
        def on_wheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")

        def bind_wheel(_event):
            canvas.bind_all("<MouseWheel>", on_wheel)

        def unbind_wheel(_event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", bind_wheel)
        canvas.bind("<Leave>", unbind_wheel)


def ask_quantity(parent, title: str, prompt: str, initial: int = 1,
                 minvalue: int = 0, maxvalue: int = 10000) -> int | None:
    """Hop thoai hoi so luong, dong bo voi theme cua app
    (simpledialog cua Tk dung giao dien mac dinh, lac tong)."""
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.transient(parent.winfo_toplevel())
    dialog.configure(background=theme.BG)

    result: list[int | None] = [None]

    body = ttk.Frame(dialog, padding=18)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=prompt).pack(anchor="w")

    box = ttk.Spinbox(body, from_=minvalue, to=maxvalue, width=10,
                      justify="center", font=(theme.FAMILY, 12))
    box.pack(pady=10)
    box.set(initial)
    box.select_range(0, "end")

    def ok(_event=None):
        try:
            value = int(box.get())
        except ValueError:
            box.set(initial)
            return
        result[0] = max(minvalue, min(maxvalue, value))
        dialog.destroy()

    def cancel(_event=None):
        dialog.destroy()

    buttons = ttk.Frame(body)
    buttons.pack(fill="x", pady=(6, 0))
    ttk.Button(buttons, text="OK", style="Accent.TButton",
               command=ok).pack(side="left", expand=True, fill="x", padx=(0, 4))
    ttk.Button(buttons, text="Hủy", command=cancel).pack(
        side="left", expand=True, fill="x")

    dialog.bind("<Return>", ok)
    dialog.bind("<Escape>", cancel)

    # canh giua cua so cha
    dialog.update_idletasks()
    top = parent.winfo_toplevel()
    x = top.winfo_rootx() + (top.winfo_width() - dialog.winfo_width()) // 2
    y = top.winfo_rooty() + (top.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    box.focus_set()
    dialog.grab_set()
    dialog.wait_window()
    return result[0]
