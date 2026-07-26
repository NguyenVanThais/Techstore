"""Kiem tra du lieu nhap truoc khi cham toi database."""
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
    try:
        number = float(str(value).replace(",", "").strip())
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
