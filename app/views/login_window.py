"""Hop thoai dang nhap, hien truoc khi vao cua so chinh.

Ket qua nam o self.result: document user neu dang nhap dung,
None neu nguoi dung dong cua so.
"""
import tkinter as tk
from tkinter import ttk

from app.services import auth_service
from app.views import theme


class LoginDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.result: dict | None = None

        self.title("Đăng nhập — TechStore")
        self.resizable(False, False)
        self.configure(background=theme.SIDEBAR)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        body = tk.Frame(self, bg=theme.SIDEBAR, padx=46, pady=34)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="TechStore", bg=theme.SIDEBAR, fg="#ffffff",
                 font=(theme.FAMILY, 22, "bold")).pack()
        tk.Label(body, text="Quản lý bán hàng công nghệ", bg=theme.SIDEBAR,
                 fg=theme.SIDEBAR_TEXT, font=theme.FONT_BASE).pack(pady=(2, 22))

        form = tk.Frame(body, bg=theme.SIDEBAR)
        form.pack()

        tk.Label(form, text="Tên đăng nhập", bg=theme.SIDEBAR,
                 fg=theme.SIDEBAR_TEXT, font=theme.FONT_SMALL,
                 anchor="w").pack(fill="x")
        self.username = ttk.Entry(form, width=28, font=(theme.FAMILY, 11))
        self.username.pack(pady=(2, 10), ipady=3)

        tk.Label(form, text="Mật khẩu", bg=theme.SIDEBAR,
                 fg=theme.SIDEBAR_TEXT, font=theme.FONT_SMALL,
                 anchor="w").pack(fill="x")
        self.password = ttk.Entry(form, width=28, show="●",
                                  font=(theme.FAMILY, 11))
        self.password.pack(pady=(2, 4), ipady=3)

        self.error = tk.Label(body, text="", bg=theme.SIDEBAR,
                              fg="#ff8f8f", font=theme.FONT_SMALL)
        self.error.pack(pady=(4, 2))

        ttk.Button(body, text="Đăng nhập", style="Big.Accent.TButton",
                   command=self._submit).pack(fill="x", pady=(6, 0))

        tk.Label(body, text="Mặc định: admin / admin123 · nhanvien / 123456",
                 bg=theme.SIDEBAR, fg=theme.SIDEBAR_TEXT,
                 font=theme.FONT_SMALL).pack(pady=(14, 0))

        self.bind("<Return>", lambda e: self._submit())
        self.bind("<Escape>", lambda e: self._cancel())

        # canh giua man hinh (cua so cha dang withdraw nen khong dua theo no)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 3
        self.geometry(f"+{x}+{y}")

        self.username.focus_set()
        self.grab_set()

    def _submit(self):
        user = auth_service.login(self.username.get(), self.password.get())
        if user:
            self.result = user
            self.destroy()
            return
        # khong noi ro sai ten hay sai mat khau (xem auth_service)
        self.error.config(text="Sai tên đăng nhập hoặc mật khẩu.")
        self.password.delete(0, "end")
        self.password.focus_set()

    def _cancel(self):
        self.result = None
        self.destroy()
