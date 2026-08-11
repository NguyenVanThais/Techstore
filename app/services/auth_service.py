"""Dang nhap va phan quyen.

Mat khau KHONG luu dang chu ro ma luu PBKDF2-SHA256 kem salt ngau nhien
rieng cho tung tai khoan: lo database cung khong lo mat khau, va hai nguoi
dat trung mat khau van ra hash khac nhau.
"""
import hashlib
import hmac
import secrets

from app.models import user as user_model

# vai tro -> ten hien thi
ROLES = {"admin": "Quản lý", "staff": "Nhân viên"}

_ITERATIONS = 100_000


def _hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"),
        bytes.fromhex(salt_hex), _ITERATIONS).hex()


def create_user(username: str, password: str,
                display_name: str, role: str = "staff"):
    username = username.strip().lower()
    if role not in ROLES:
        raise ValueError(f"Vai trò không hợp lệ: {role}")
    if user_model.get_by_username(username):
        raise ValueError(f"Tên đăng nhập '{username}' đã tồn tại.")

    salt = secrets.token_hex(16)
    return user_model.create({
        "username": username,
        "display_name": display_name,
        "role": role,
        "salt": salt,
        "password_hash": _hash(password, salt),
    })


def login(username: str, password: str) -> dict | None:
    """Tra ve document user neu dung, None neu sai.

    Co tinh khong phan biet 'sai ten' voi 'sai mat khau' trong thong bao:
    noi ro giup ke do mat khau biet ten nao ton tai.
    """
    user = user_model.get_by_username((username or "").strip().lower())
    if not user:
        return None
    expected = user["password_hash"]
    actual = _hash(password or "", user["salt"])
    # compare_digest: so sanh het chuoi du sai som, chong do thoi gian phan hoi
    if hmac.compare_digest(expected, actual):
        return user
    return None


def ensure_default_users() -> None:
    """Tao 2 tai khoan mau khi database chua co tai khoan nao.

    admin / admin123 (Quan ly — thay het menu)
    nhanvien / 123456 (Nhan vien — chi ban hang, hoa don, khach hang, tro ly)
    """
    if user_model.count() > 0:
        return
    create_user("admin", "admin123", "Quản trị viên", "admin")
    create_user("nhanvien", "123456", "Nhân viên bán hàng", "staff")
