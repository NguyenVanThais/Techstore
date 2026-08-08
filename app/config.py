"""Cau hinh ung dung, doc tu file .env."""
import json
from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "techstore")

ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
FONTS_DIR = ASSETS_DIR / "fonts"
EXPORTS_DIR = BASE_DIR / "exports"

APP_TITLE = "TechStore — Quản lý bán hàng công nghệ"
WINDOW_SIZE = "1280x760"

# Font Unicode dung cho reportlab va matplotlib (tieng Viet co dau)
FONT_REGULAR = FONTS_DIR / "DejaVuSans.ttf"
FONT_BOLD = FONTS_DIR / "DejaVuSans-Bold.ttf"

# Lua chon cua nguoi dung (che do sang/toi...) — khac voi .env,
# file nay do chinh app ghi ra nen khong nam trong .env.example.
SETTINGS_FILE = BASE_DIR / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_setting(key: str, value) -> None:
    data = load_settings()
    data[key] = value
    try:
        SETTINGS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass   # khong luu duoc thi lan sau mo lai dung mac dinh, khong dang crash
