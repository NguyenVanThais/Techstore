"""Nhat ky hoat dong (audit log).

Ai lam gi, luc nao — de admin tra lai duoc khi so lieu bat thuong.
Nguoi dang dang nhap duoc dang ky mot lan bang set_user() sau khi login,
cac noi ghi log chi can goi log(action, detail) ma khong phai chuyen user
qua tung tang.

log() KHONG BAO GIO nem loi: ghi nhat ky that bai (mat mang trong tich tac)
khong duoc phep lam hong thao tac chinh vua thanh cong.
"""
from app.models import audit as audit_model

_current_user: dict = {}


def set_user(user: dict | None) -> None:
    global _current_user
    _current_user = user or {}


def current_username() -> str:
    return _current_user.get("username", "")


def log(action: str, detail: str = "") -> None:
    try:
        audit_model.add(
            user=_current_user.get("username", "(chưa đăng nhập)"),
            role=_current_user.get("role", ""),
            action=action,
            detail=detail,
        )
    except Exception:
        pass


def recent(keyword: str = "", limit: int = 500) -> list[dict]:
    return audit_model.recent(keyword, limit)
