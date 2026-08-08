"""Man cai dat: sao luu / khoi phuc du lieu, quan ly tai khoan dang nhap.

Chi danh cho Quan ly (menu da loc theo vai tro o main_window). Restore la
thao tac PHA HUY: ghi de toan bo du lieu hien tai, nen doi hoi go dung chu
"XAC NHAN" thay vi mot cai click Yes/No de tranh bam nham.
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from app.config import EXPORTS_DIR
from app.models import user as user_model
from app.services import audit_service, auth_service, backup_service
from app.services.auth_service import ROLES
from app.utils.validators import ValidationError, require_text
from app.views import theme, widgets
from app.views.base_frame import BaseFrame, make_title

USER_COLUMNS = [
    ("username", "Tên đăng nhập", 160),
    ("display_name", "Họ tên hiển thị", 220),
    ("role", "Vai trò", 120),
]


class SettingsView(BaseFrame):
    def __init__(self, parent, app):
        super().__init__(parent, app)

        make_title(self, "Cài đặt",
                   "Sao lưu định kỳ để không mất dữ liệu khi máy chủ gặp sự cố")

        section = ttk.LabelFrame(self, text="Sao lưu & khôi phục dữ liệu",
                                 padding=16)
        section.pack(fill="x", pady=(0, 12))

        ttk.Label(section,
                  text="Sao lưu xuất toàn bộ dữ liệu (sản phẩm, hóa đơn, khách "
                       "hàng, tài khoản...) ra một file JSON trong thư mục "
                       "exports/. Khôi phục sẽ GHI ĐÈ toàn bộ dữ liệu hiện tại "
                       "bằng nội dung file đã chọn — nhớ chọn đúng file.",
                  style="Muted.TLabel", wraplength=640, justify="left").pack(
            anchor="w", pady=(0, 12))

        buttons = ttk.Frame(section)
        buttons.pack(anchor="w")
        ttk.Button(buttons, text="Sao lưu ngay", style="Accent.TButton",
                   command=self.do_backup).pack(side="left")
        ttk.Button(buttons, text="Khôi phục từ file...", style="Danger.TButton",
                   command=self.do_restore).pack(side="left", padx=8)

        self.last_label = ttk.Label(section, text="", style="Muted.TLabel")
        self.last_label.pack(anchor="w", pady=(10, 0))

        self._build_users_section()

    def _build_users_section(self):
        section = ttk.LabelFrame(self, text="Tài khoản đăng nhập", padding=16)
        section.pack(fill="both", expand=True)

        ttk.Label(section,
                  text="Tạo tài khoản mới cho nhân viên hoặc quản lý khác. "
                       "Mật khẩu được băm PBKDF2, không ai xem lại được kể "
                       "cả admin.",
                  style="Muted.TLabel", wraplength=640, justify="left").pack(
            anchor="w", pady=(0, 10))

        table = ttk.Frame(section)
        table.pack(fill="both", expand=True)

        self.user_tree = ttk.Treeview(
            table, columns=[c[0] for c in USER_COLUMNS], show="headings",
            height=6)
        for key, title, width in USER_COLUMNS:
            self.user_tree.heading(key, text=title)
            self.user_tree.column(key, width=width, anchor="w")

        scroll = ttk.Scrollbar(table, orient="vertical",
                               command=self.user_tree.yview)
        self.user_tree.configure(yscrollcommand=scroll.set)
        self.user_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        widgets.add_grid_lines(self.user_tree, stretch_column="display_name")

        theme.configure_stripes(self.user_tree)

        ttk.Button(section, text="Tạo tài khoản mới", style="Accent.TButton",
                   command=self.create_user).pack(anchor="w", pady=(10, 0))

    def on_show(self):
        self._refresh_last_backup()
        self._reload_users()

    def _reload_users(self):
        self.user_tree.delete(*self.user_tree.get_children())
        for user in user_model.list_all():
            self.user_tree.insert(
                "", "end", iid=user["username"],
                values=(user["username"], user.get("display_name", ""),
                        ROLES.get(user.get("role"), user.get("role", ""))),
            )
        theme.stripe_rows(self.user_tree)

    def create_user(self):
        dialog = CreateUserDialog(self)
        self.wait_window(dialog)
        if dialog.created_username:
            audit_service.log("Tạo tài khoản",
                              f"{dialog.created_username} "
                              f"({ROLES.get(dialog.created_role, '')})")
            widgets.toast(self, f"Đã tạo tài khoản \"{dialog.created_username}\"")
            self._reload_users()

    def _refresh_last_backup(self):
        files = sorted(EXPORTS_DIR.glob("backup_*.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True) \
                if EXPORTS_DIR.exists() else []
        self.last_label.config(
            text=f"Lần sao lưu gần nhất: {files[0].name}" if files
                 else "Chưa có bản sao lưu nào.")

    def do_backup(self):
        try:
            path = backup_service.backup()
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không sao lưu được:\n{exc}")
            return

        self._refresh_last_backup()
        open_it = messagebox.askyesno(
            "Đã sao lưu", f"Đã lưu vào:\n{path}\n\nMở thư mục chứa file?")
        if open_it:
            try:
                os.startfile(path.parent)
            except OSError as exc:
                messagebox.showwarning("Không mở được", str(exc))

    def do_restore(self):
        path = filedialog.askopenfilename(
            title="Chọn file backup",
            initialdir=str(EXPORTS_DIR),
            filetypes=[("Backup JSON", "*.json")],
        )
        if not path:
            return

        warn = messagebox.askyesno(
            "CẢNH BÁO — Ghi đè dữ liệu",
            "Khôi phục sẽ XÓA TOÀN BỘ dữ liệu hiện tại và thay bằng nội dung "
            f"file:\n{path}\n\n"
            "Ứng dụng sẽ tự sao lưu dữ liệu hiện tại trước khi ghi đè, "
            "nhưng thao tác này vẫn nên cân nhắc kỹ.\n\nTiếp tục?",
            icon="warning",
        )
        if not warn:
            return

        confirm = simpledialog.askstring(
            "Xác nhận lần cuối",
            "Gõ chính xác XAC NHAN (không dấu, chữ hoa) để khôi phục:",
            parent=self)
        if confirm != "XAC NHAN":
            messagebox.showinfo("Đã hủy", "Không khớp — đã hủy khôi phục.")
            return

        try:
            counts = backup_service.restore(path)
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không khôi phục được:\n{exc}")
            return

        self._refresh_last_backup()
        detail = "\n".join(f"  {name}: {n}" for name, n in counts.items() if n)
        messagebox.showinfo(
            "Đã khôi phục",
            f"Khôi phục thành công.\n\n{detail}\n\n"
            "Hãy khởi động lại ứng dụng để tải lại toàn bộ giao diện.")


class CreateUserDialog(tk.Toplevel):
    """Tao tai khoan dang nhap moi (nhan vien hoac quan ly). Chi Quan ly moi
    mo duoc man Cai dat nen khong can kiem tra quyen lai o day."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Tạo tài khoản mới")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.configure(background=theme.BG)
        self.created_username = None
        self.created_role = None

        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)

        self.fields = {}
        for key, label in [("username", "Tên đăng nhập"),
                           ("display_name", "Họ tên hiển thị"),
                           ("password", "Mật khẩu")]:
            ttk.Label(body, text=label).pack(anchor="w", pady=(4, 0))
            entry = ttk.Entry(body, width=32,
                              show="*" if key == "password" else "")
            entry.pack(fill="x")
            self.fields[key] = entry

        ttk.Label(body, text="Vai trò").pack(anchor="w", pady=(4, 0))
        self.role_box = ttk.Combobox(body, width=29, state="readonly",
                                     values=list(ROLES.values()))
        self.role_box.set(ROLES["staff"])
        self.role_box.pack(fill="x", pady=(0, 10))

        buttons = ttk.Frame(body)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Tạo tài khoản", style="Accent.TButton",
                   command=self._save).pack(side="left", expand=True,
                                            fill="x", padx=(0, 4))
        ttk.Button(buttons, text="Hủy", command=self.destroy).pack(
            side="left", expand=True, fill="x")

        self.bind("<Escape>", lambda e: self.destroy())
        self.fields["username"].focus_set()
        self.grab_set()

    def _save(self):
        try:
            username = require_text(self.fields["username"].get(),
                                    "Tên đăng nhập", max_len=40)
            display_name = require_text(self.fields["display_name"].get(),
                                        "Họ tên hiển thị")
            password = self.fields["password"].get()
            if len(password) < 4:
                raise ValidationError("Mật khẩu phải có ít nhất 4 ký tự.")
        except ValidationError as exc:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(exc), parent=self)
            return

        role = next((k for k, v in ROLES.items() if v == self.role_box.get()),
                   "staff")

        try:
            auth_service.create_user(username, password, display_name, role)
        except ValueError as exc:
            messagebox.showwarning("Không tạo được", str(exc), parent=self)
            return

        self.created_username = username.strip().lower()
        self.created_role = role
        self.destroy()
