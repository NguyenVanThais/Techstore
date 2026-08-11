"""Sao luu va khoi phuc database ra file JSON.

Dung bson.json_util thay cho json thuong: ObjectId va datetime khong tu
serialize duoc bang json.dumps, json_util giu nguyen duoc ca hai (dang
Extended JSON) nen khoi phuc lai la du lieu y het ban dau.
"""
from datetime import datetime
from pathlib import Path

from bson import json_util

from app.config import EXPORTS_DIR
from app.database.connection import ensure_indexes, get_db
from app.services import audit_service

# users nam trong danh sach: khoi phuc xong phai dang nhap lai duoc ngay.
COLLECTIONS = [
    "products", "categories", "orders", "customers", "users",
    "counters", "suppliers", "purchases", "audit_logs",
]


def backup(target_dir: Path | None = None) -> Path:
    """Ghi toan bo du lieu ra mot file JSON. Tra ve duong dan file."""
    target_dir = target_dir or EXPORTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"backup_{datetime.now():%Y%m%d_%H%M%S}.json"

    db = get_db()
    data = {name: list(db[name].find()) for name in COLLECTIONS}
    path.write_text(json_util.dumps(data, ensure_ascii=False, indent=1),
                    encoding="utf-8")

    total = sum(len(docs) for docs in data.values())
    audit_service.log("Sao lưu", f"{path.name} · {total} bản ghi")
    return path


def restore(path: Path | str) -> dict[str, int]:
    """Khoi phuc tu file backup. Tra ve {ten_collection: so_ban_ghi}.

    TU SAO LUU truoc khi ghi de: neu file khoi phuc hong giua chung hoac
    chon nham file, van con ban chup cua du lieu ngay truoc do de quay lai.
    """
    path = Path(path)
    data = json_util.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict) or not any(k in COLLECTIONS for k in data):
        raise ValueError("File không đúng định dạng backup của TechStore.")
    unknown = [k for k in data if k not in COLLECTIONS]
    if unknown:
        raise ValueError(f"File chứa collection lạ: {', '.join(unknown)}.")

    safety = backup()   # luoi an toan truoc khi dong den du lieu that

    db = get_db()
    counts: dict[str, int] = {}
    for name in COLLECTIONS:
        docs = data.get(name, [])
        db[name].drop()
        if docs:
            db[name].insert_many(docs)
        counts[name] = len(docs)

    ensure_indexes()   # drop() lam mat index, phai dung lai
    audit_service.log(
        "Khôi phục dữ liệu",
        f"Từ {path.name} · {sum(counts.values())} bản ghi "
        f"(đã tự sao lưu trước vào {safety.name})")
    return counts
