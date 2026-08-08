"""Xu ly chuoi tieng Viet."""
import unicodedata


def strip_diacritics(text: str) -> str:
    """'Điện thoại' -> 'Dien thoai'.

    NFD tach chu co dau thanh chu goc + dau roi (Mn), bo phan dau di la xong.
    Rieng d/D khong phai to hop dau nen phai thay thu cong.
    """
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def search_key(text: str) -> str:
    """Chuoi dung de so khop tim kiem: khong dau, chu thuong.

    Luu san vao truong name_search cua document de go 'dien thoai'
    van tim ra 'Điện thoại' ma khong can regex phuc tap luc truy van.
    """
    return strip_diacritics(text).lower().strip()
