"""Lop cha cho moi man hinh."""
from tkinter import ttk

from app.views import theme


class BaseFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(22, 18))
        self.app = app

    def on_show(self) -> None:
        """Duoc goi moi lan man hinh nay duoc dua len truoc.

        Ghi de de nap lai du lieu -- neu chi nap trong __init__ thi
        so lieu se cu ngay khi nguoi dung chuyen qua lai giua cac man hinh.
        """


def make_title(parent, text: str, subtitle: str = "") -> ttk.Frame:
    header = ttk.Frame(parent)
    header.pack(fill="x", pady=(0, 14))

    ttk.Label(header, text=text, style="Title.TLabel").pack(anchor="w")
    if subtitle:
        ttk.Label(header, text=subtitle, style="Muted.TLabel").pack(
            anchor="w", pady=(2, 0))
    return header


def card(parent, **kwargs) -> ttk.Frame:
    """Khung trang co vien mong, dung thay cho LabelFrame khi khong can tieu de."""
    return ttk.Frame(parent, style="Card.TFrame", padding=12, **kwargs)


__all__ = ["BaseFrame", "make_title", "card", "theme"]
