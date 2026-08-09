"""Kiem tra du lieu nhap truoc khi cham toi database."""
import re
from datetime import datetime


class ValidationError(Exception):
    pass


def require_text(value: str, field: str, max_len: int = 200) -> str:
    value = (value or "").strip()
    if not value:
        raise ValidationError(f"{field} không được để trống.")
    if len(value) > max_len:
        raise ValidationError(f"{field} quá dài (tối đa {max_len} ký tự).")
    return value


def parse_price(value: str, field: str = "Giá") -> float:
    text = str(value).replace(",", "").strip()
    # Chinh app hien thi gia dang '1.500.000' nen phai nhan lai dung dinh dang
    # do: cac cum 3 chu so ngan bang dau cham la phan cach hang nghin.
    # '1.5' khong khop mau nay va van duoc hieu la so thap phan.
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "")
    try:
        number = float(text)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} phải là một số.")
    if number < 0:
        raise ValidationError(f"{field} không được âm.")
    return number


def parse_quantity(value: str, field: str = "Số lượng") -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field} phải là số nguyên.")
    if number < 0:
        raise ValidationError(f"{field} không được âm.")
    return number


def parse_date(value: str, field: str = "Ngày") -> datetime | None:
    """'09/07/2026' -> datetime. Chuoi rong -> None (nghia la khong loc)."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        raise ValidationError(f"{field} phải có dạng ngày/tháng/năm, ví dụ 09/07/2026.")


def parse_phone(value: str) -> str:
    value = (value or "").strip()
    if value and not value.isdigit():
        raise ValidationError("Số điện thoại chỉ được chứa chữ số.")
    return value
