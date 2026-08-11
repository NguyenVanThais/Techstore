"""Bang mau, font va cac style ttk dung chung cho toan bo ung dung.

Co HAI bang mau (sang / toi). Cac view chi tham chieu theme.BG, theme.TEXT...
nen doi che do chi la thay gia tri cac ten do (set_mode) roi dung lai giao
dien; goi apply_theme(root) sau moi lan doi.

Dung theme 'clam' chu khong dung 'vista' mac dinh cua Windows: 'vista' ve
widget bang anh bitmap cua he dieu hanh nen khong doi duoc mau nen, con
'clam' ve bang code nen tuy bien duoc hoan toan.
"""
from tkinter import ttk

# ---------- hai bang mau ----------

LIGHT = dict(
    BG="#f1f4f8",           # nen chung
    SURFACE="#ffffff",      # nen the / bang
    BORDER="#dfe3e8",

    SIDEBAR="#16202f",      # xanh than
    SIDEBAR_HOVER="#243447",
    SIDEBAR_TEXT="#a7b4c4",
    SIDEBAR_ACTIVE_TEXT="#ffffff",

    TEXT="#1a2230",
    MUTED="#7b8794",

    PRIMARY="#2f6fed",
    PRIMARY_DARK="#1f57c8",
    DANGER="#d64545",
    DANGER_DARK="#b23434",
    SUCCESS="#1f9d6b",
    WARNING="#d98b1f",

    ROW_ALT="#f7f9fb",
    SELECT="#dbe7fb",

    # to mau canh bao ton kho (product_view / inventory_view)
    OUT_OF_STOCK="#fbdcdc",
    LOW_STOCK="#fdeecd",

    BTN_BG="#e6eaf0",
    BTN_HOVER="#d9dfe7",
    BTN_PRESSED="#cdd5df",
    HEAD_BG="#eaeef3",
    HEAD_HOVER="#dfe5ec",
    TAB_BG="#e3e8ee",
)

DARK = dict(
    BG="#141a24",
    SURFACE="#1e2634",
    BORDER="#2c3648",

    SIDEBAR="#0e141d",
    SIDEBAR_HOVER="#1b2534",
    SIDEBAR_TEXT="#8b99ac",
    SIDEBAR_ACTIVE_TEXT="#ffffff",

    TEXT="#e6ebf2",
    MUTED="#8b99ac",

    # xanh sang hon ban goc mot chut de noi tren nen toi
    PRIMARY="#4d86f7",
    PRIMARY_DARK="#2f6fed",
    DANGER="#e05b5b",
    DANGER_DARK="#c74a4a",
    SUCCESS="#2eb57f",
    WARNING="#e09a33",

    ROW_ALT="#232c3c",
    SELECT="#2f4368",

    OUT_OF_STOCK="#4a2626",
    LOW_STOCK="#4a3a1e",

    BTN_BG="#2a3446",
    BTN_HOVER="#334056",
    BTN_PRESSED="#3c4a63",
    HEAD_BG="#232c3c",
    HEAD_HOVER="#2a3446",
    TAB_BG="#232c3c",
)

MODE = "light"


def set_mode(mode: str) -> None:
    """Nap bang mau vao cac ten module (theme.BG, theme.TEXT...).

    Cac view doc theme.X tai thoi diem DUNG, nen sau khi goi ham nay chi can
    dung lai giao dien la toan bo mau moi co hieu luc.
    """
    global MODE
    MODE = "dark" if mode == "dark" else "light"
    globals().update(DARK if MODE == "dark" else LIGHT)


set_mode("light")   # nap gia tri mac dinh de import xong la dung duoc ngay

# ---------- font ----------

FAMILY = "Segoe UI"
FONT_BASE = (FAMILY, 10)
FONT_BOLD = (FAMILY, 10, "bold")
FONT_TITLE = (FAMILY, 17, "bold")
FONT_SECTION = (FAMILY, 11, "bold")
FONT_BRAND = (FAMILY, 16, "bold")
FONT_CARD_VALUE = (FAMILY, 17, "bold")
FONT_SMALL = (FAMILY, 9)


def apply_theme(root) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(background=BG)

    style.configure(".", font=FONT_BASE, background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Title.TLabel", font=FONT_TITLE)
    style.configure("Section.TLabel", font=FONT_SECTION)

    # chu gon giua bang trong (EmptyHint): nen phai trung voi nen Treeview
    style.configure("Empty.TLabel", background=SURFACE, foreground=MUTED)

    # ---------- the / khung ----------
    style.configure("Card.TFrame", background=SURFACE,
                    relief="solid", borderwidth=1, bordercolor=BORDER)
    style.configure("Card.TLabel", background=SURFACE)
    style.configure("CardValue.TLabel", background=SURFACE, font=FONT_CARD_VALUE)
    style.configure("CardTitle.TLabel", background=SURFACE, foreground=MUTED,
                    font=FONT_SMALL)

    # Nen LabelFrame trung voi nen chung: neu de trang thi moi ttk.Label ben
    # trong (mac dinh nen xam) se lo ra thanh mang mau lech.
    style.configure("TLabelframe", background=BG, relief="solid",
                    borderwidth=1, bordercolor=BORDER)
    style.configure("TLabelframe.Label", background=BG,
                    foreground=MUTED, font=FONT_BOLD)

    # ---------- nut ----------
    style.configure("TButton", padding=(12, 7), relief="flat",
                    background=BTN_BG, foreground=TEXT, borderwidth=0)
    style.map("TButton",
              background=[("pressed", BTN_PRESSED), ("active", BTN_HOVER)])

    style.configure("Accent.TButton", background=PRIMARY, foreground="#ffffff")
    style.map("Accent.TButton",
              background=[("pressed", PRIMARY_DARK), ("active", PRIMARY_DARK)],
              foreground=[("disabled", "#dfe3e8")])

    style.configure("Danger.TButton", background=DANGER, foreground="#ffffff")
    style.map("Danger.TButton",
              background=[("pressed", DANGER_DARK), ("active", DANGER_DARK)])

    style.configure("Big.Accent.TButton", padding=(12, 12),
                    font=(FAMILY, 11, "bold"),
                    background=PRIMARY, foreground="#ffffff")
    style.map("Big.Accent.TButton",
              background=[("pressed", PRIMARY_DARK), ("active", PRIMARY_DARK)])

    # nut nho +/- trong gio hang
    style.configure("Icon.TButton", padding=(4, 2), font=(FAMILY, 11, "bold"))

    # nut "chip" nho cho cac lua chon nhanh (Hom nay / 7 ngay / Thang nay)
    style.configure("Chip.TButton", padding=(9, 3), font=FONT_SMALL)

    # ---------- o nhap ----------
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, padding=5, fieldbackground=SURFACE,
                        foreground=TEXT, bordercolor=BORDER, lightcolor=BORDER,
                        darkcolor=BORDER, insertcolor=TEXT,
                        arrowcolor=MUTED, background=BTN_BG)
        style.map(name, bordercolor=[("focus", PRIMARY)],
                  lightcolor=[("focus", PRIMARY)],
                  darkcolor=[("focus", PRIMARY)],
                  fieldbackground=[("readonly", SURFACE)])

    # ---------- bang ----------
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE,
                    foreground=TEXT, rowheight=28, borderwidth=0,
                    bordercolor=BORDER)
    style.map("Treeview", background=[("selected", SELECT)],
              foreground=[("selected", TEXT)])
    style.configure("Treeview.Heading", font=FONT_BOLD, padding=(6, 8),
                    background=HEAD_BG, foreground=MUTED, relief="flat",
                    borderwidth=0)
    style.map("Treeview.Heading", background=[("active", HEAD_HOVER)])

    # ---------- tab bieu do ----------
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 4, 0, 0))
    style.configure("TNotebook.Tab", padding=(16, 8), background=TAB_BG,
                    foreground=MUTED, borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", SURFACE)],
              foreground=[("selected", TEXT)],
              expand=[("selected", (0, 0, 0, 1))])

    style.configure("TScrollbar", background=TAB_BG, troughcolor=BG,
                    borderwidth=0, arrowcolor=MUTED)

    style.configure("TSeparator", background=BORDER)

    return style


def configure_stripes(tree) -> None:
    """Ke soc xen ke cho de doc.

    Chi dung o bang KHONG to mau NEN theo trang thai (hoa don, danh muc).
    Tag chi dat mau CHU (vi du 'cancelled' o bang hoa don) thi dung chung
    duoc: moi thuoc tinh lay tu tag dau tien co dinh nghia no, nen chu lay
    tu 'cancelled' con nen van lay tu 'odd'.
    """
    tree.tag_configure("odd", background=ROW_ALT)


def stripe_rows(tree) -> None:
    """Goi sau khi da chen xong toan bo dong. Giu nguyen cac tag khac cua dong."""
    for index, iid in enumerate(tree.get_children("")):
        tags = tuple(t for t in tree.item(iid, "tags") if t != "odd")
        if index % 2:
            tags = tags + ("odd",)
        tree.item(iid, tags=tags)
