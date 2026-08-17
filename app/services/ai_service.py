"""Tro ly AI cua man hinh "Tro ly AI".

Hai che do, tu chon theo cau hinh:

1. Co ANTHROPIC_API_KEY trong .env  ->  goi Claude API. Truoc khi goi, app
   dong goi san mot ban chup so lieu that (doanh thu, ton kho, ban chay...)
   vao system prompt, nen model tra loi dua tren du lieu cua CHINH cua hang
   chu khong bia so.
2. Khong co key  ->  bo tra loi theo tu khoa (rule-based) chay hoan toan
   offline, van doc so lieu that tu MongoDB. Cau hoi duoc bo dau truoc khi
   so khop nen go "doanh thu hom nay" hay "doanh thu hôm nay" deu hieu.

Moi truy van so lieu deu di qua report_service / cac model nen tu dong
loai don da huy, khop voi man hinh Thong ke.
"""
import os
from datetime import date, datetime, timedelta

from app.models import customer as customer_model
from app.models import order as order_model
from app.models import product as product_model
from app.services import report_service
from app.utils.formatters import money
from app.utils.text import search_key

CLAUDE_MODEL = "claude-haiku-4-5"

APP_GUIDE = """Bạn là trợ lý của TechStore — phần mềm quản lý bán hàng công nghệ.
Trả lời NGẮN GỌN bằng tiếng Việt, thân thiện, đúng số liệu được cung cấp.
Nếu câu hỏi nằm ngoài dữ liệu và cách dùng phần mềm, nói rõ là không có thông tin.

Cách dùng các màn hình:
- Bán hàng: tìm sản phẩm (gõ là lọc ngay), double-click hoặc "Thêm vào giỏ";
  gõ đúng mã SKU rồi Enter là thêm thẳng vào giỏ (dùng được với máy quét mã vạch);
  nhập giảm giá, tên + số điện thoại khách rồi bấm THANH TOÁN.
- Sản phẩm (chỉ Quản lý): thêm/sửa/xóa, chọn ảnh, đặt tồn tối thiểu.
- Danh mục (chỉ Quản lý): thêm/sửa/xóa; đổi tên tự cập nhật mọi sản phẩm.
- Tồn kho (chỉ Quản lý): xem sản phẩm sắp hết, nhập thêm hàng.
- Hóa đơn: lọc theo mã/khách/khoảng ngày, xem chi tiết, xuất PDF, xuất Excel,
  HỦY ĐƠN (tồn kho được cộng trả lại, thống kê bỏ qua đơn hủy).
- Khách hàng: tự ghi nhận từ đơn có số điện thoại; double-click xem lịch sử mua.
- Thống kê (chỉ Quản lý): 4 thẻ số liệu + 3 biểu đồ, xuất Excel.
- Đăng nhập: admin/admin123 (Quản lý), nhanvien/123456 (Nhân viên).
- Nút 🌙 dưới thanh bên để đổi giao diện sáng/tối."""


def has_api() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


# ---------- ban chup so lieu ----------

def _data_snapshot() -> str:
    """Tom tat so lieu hien tai thanh van ban, dung cho ca hai che do."""
    today = datetime.now()
    first_of_month = today.replace(day=1)
    lines = [f"Số liệu tính đến {today:%H:%M %d/%m/%Y}:"]

    day_stats = report_service.summary(today, today)
    lines.append(
        f"- Hôm nay: {money(day_stats['revenue'])}, {day_stats['orders']} đơn, "
        f"{day_stats['products_sold']} sản phẩm.")

    month_stats = report_service.summary(first_of_month, today)
    lines.append(
        f"- Tháng này: {money(month_stats['revenue'])}, {month_stats['orders']} đơn, "
        f"trung bình {money(month_stats['avg_order'])}/đơn.")

    top = report_service.top_products(5, today - timedelta(days=30), today)
    if top:
        lines.append("- Bán chạy 30 ngày qua: " + "; ".join(
            f"{row['_id']} ({row['quantity']} cái)" for row in top))

    low = product_model.low_stock()
    if low:
        lines.append("- Sắp hết hàng: " + "; ".join(
            f"{p['name']} (còn {p['stock']}, tối thiểu {p.get('min_stock', 0)})"
            for p in low[:10]))
    else:
        lines.append("- Tồn kho ổn định, không sản phẩm nào dưới mức tối thiểu.")

    spenders = customer_model.top_spenders(3)
    if spenders:
        lines.append("- Khách chi tiêu nhiều nhất: " + "; ".join(
            f"{c['name']} ({money(c['total_spent'])}, {c['visits']} lần)"
            for c in spenders))
    return "\n".join(lines)


# ---------- che do offline: so khop tu khoa ----------

def _period_from(q: str):
    """Doan khoang thoi gian trong cau hoi (da bo dau)."""
    today = date.today()
    to_dt = lambda d: datetime(d.year, d.month, d.day)  # noqa: E731
    if "hom nay" in q:
        return to_dt(today), to_dt(today), "hôm nay"
    if "hom qua" in q:
        d = today - timedelta(days=1)
        return to_dt(d), to_dt(d), "hôm qua"
    if "tuan" in q:
        return to_dt(today - timedelta(days=6)), to_dt(today), "7 ngày qua"
    if "thang truoc" in q:
        last = today.replace(day=1) - timedelta(days=1)
        return to_dt(last.replace(day=1)), to_dt(last), "tháng trước"
    if "thang" in q:
        return to_dt(today.replace(day=1)), to_dt(today), "tháng này"
    if "nam" in q:
        return to_dt(today.replace(month=1, day=1)), to_dt(today), "năm nay"
    return None, None, "toàn bộ thời gian"


def _answer_revenue(q: str) -> str:
    date_from, date_to, label = _period_from(q)
    stats = report_service.summary(date_from, date_to)
    if stats["orders"] == 0:
        return f"Chưa có đơn hàng nào trong {label}."
    return (f"Doanh thu {label}: {money(stats['revenue'])} từ "
            f"{stats['orders']} hóa đơn ({stats['products_sold']} sản phẩm, "
            f"trung bình {money(stats['avg_order'])}/đơn). "
            f"Số liệu không tính các đơn đã hủy.")


def _answer_low_stock() -> str:
    low = product_model.low_stock()
    if not low:
        return "Tồn kho đang ổn định — không sản phẩm nào dưới mức tối thiểu."
    lines = [f"Có {len(low)} sản phẩm sắp hết hàng:"]
    lines += [f"• {p['name']}: còn {p['stock']} (tối thiểu {p.get('min_stock', 0)})"
              for p in low[:10]]
    if len(low) > 10:
        lines.append(f"... và {len(low) - 10} sản phẩm khác (xem màn Tồn kho).")
    return "\n".join(lines)


def _answer_top_products(q: str) -> str:
    date_from, date_to, label = _period_from(q)
    top = report_service.top_products(5, date_from, date_to)
    if not top:
        return f"Chưa có dữ liệu bán hàng trong {label}."
    lines = [f"Top sản phẩm bán chạy {label}:"]
    lines += [f"{i}. {row['_id']} — {row['quantity']} cái, {money(row['revenue'])}"
              for i, row in enumerate(top, start=1)]
    return "\n".join(lines)


def _answer_customers() -> str:
    spenders = customer_model.top_spenders(5)
    if not spenders:
        return ("Chưa có hồ sơ khách hàng nào. Khách được ghi nhận tự động "
                "khi thanh toán có nhập số điện thoại.")
    lines = ["Khách hàng chi tiêu nhiều nhất:"]
    lines += [f"{i}. {c['name']} ({c['phone']}) — {money(c['total_spent'])}, "
              f"{c['visits']} lần mua"
              for i, c in enumerate(spenders, start=1)]
    return "\n".join(lines)


def _answer_recent_orders() -> str:
    orders = order_model.recent(5)
    if not orders:
        return "Chưa có hóa đơn nào."
    lines = ["5 hóa đơn gần nhất:"]
    for o in orders:
        status = " (đã hủy)" if o.get("status") == "cancelled" else ""
        lines.append(f"• {o['order_code']} — {o['customer']['name']}, "
                     f"{money(o['total'])}, {o['created_at']:%d/%m %H:%M}{status}")
    return "\n".join(lines)


HELP_TEXT = """Mình có thể trả lời các câu như:
• "Doanh thu hôm nay / tuần này / tháng này?"
• "Sản phẩm nào sắp hết hàng?"
• "Top bán chạy tháng này?"
• "Khách nào mua nhiều nhất?"
• "Các hóa đơn gần đây?"
• "Cách hủy hóa đơn / xuất Excel / thêm sản phẩm?"
(Thêm ANTHROPIC_API_KEY vào file .env để mình trả lời tự nhiên hơn bằng Claude.)"""

USAGE = {
    ("huy", "hoan"): "Hủy hóa đơn: mở màn Hóa đơn, chọn đơn rồi bấm nút \"Hủy đơn\" "
                     "(hoặc mở chi tiết để xem trước). Tồn kho được cộng trả lại và "
                     "thống kê sẽ bỏ qua đơn đã hủy.",
    ("excel",): "Xuất Excel: màn Hóa đơn có nút \"Xuất Excel\" (xuất danh sách đang "
                "lọc), màn Thống kê có nút \"Xuất Excel\" (báo cáo 4 sheet). File nằm "
                "trong thư mục exports/.",
    ("pdf",): "Xuất PDF: màn Hóa đơn → chọn đơn → \"Xuất PDF\", hoặc bấm trong cửa "
              "sổ chi tiết. File nằm trong thư mục exports/.",
    ("them san pham", "tao san pham"): "Thêm sản phẩm: màn Sản phẩm (cần tài khoản "
                                       "Quản lý) → điền form bên phải → \"Thêm mới\". "
                                       "Mã SKU không được trùng.",
    ("ban hang", "thanh toan", "gio hang"): "Bán hàng: tìm sản phẩm (gõ là lọc ngay), "
                                            "double-click để thêm vào giỏ. Gõ đúng mã SKU "
                                            "rồi Enter là thêm thẳng vào giỏ — dùng được với "
                                            "máy quét mã vạch. Điền khách + giảm giá rồi bấm "
                                            "THANH TOÁN.",
    ("khach",): "Màn Khách hàng: khách được tạo tự động khi thanh toán có số điện "
                "thoại. Double-click một khách để xem toàn bộ lịch sử mua.",
    ("dang nhap", "mat khau", "tai khoan"): "Tài khoản mặc định: admin/admin123 "
                                            "(Quản lý — thấy hết menu), nhanvien/123456 "
                                            "(Nhân viên — chỉ bán hàng, hóa đơn, khách hàng).",
    # "toi"/"sang" tran lan trong cau thuong ("tôi muốn...") nen phai dung
    # cum du dai moi khong khop nham
    ("giao dien", "che do toi", "che do sang", "dark mode"):
        "Đổi giao diện sáng/tối: bấm nút 🌙 ở góc dưới thanh bên trái. "
        "Lựa chọn được nhớ cho lần mở sau.",
    ("nhap hang", "ton kho"): "Nhập thêm hàng: màn Tồn kho (tài khoản Quản lý) → chọn "
                              "sản phẩm → \"Nhập thêm hàng\". Sản phẩm dưới mức tối "
                              "thiểu được tô màu cảnh báo.",
}


def _ask_rules(question: str) -> str:
    q = search_key(question)

    if any(w in q for w in ("chao", "hello", "hi ", "xin chao")) and len(q) < 25:
        return ("Chào bạn! Mình là trợ lý của TechStore. Hỏi mình về doanh thu, "
                "tồn kho, sản phẩm bán chạy, khách hàng hoặc cách dùng phần mềm nhé.")

    # cau hoi "cach ...": tra cuu bang huong dan truoc
    if any(w in q for w in ("cach", "lam sao", "lam the nao", "huong dan",
                            "o dau", "the nao")):
        for keywords, answer in USAGE.items():
            if any(k in q for k in keywords):
                return answer

    if "doanh thu" in q or "ban duoc bao nhieu" in q:
        return _answer_revenue(q)
    if "sap het" in q or "het hang" in q or "ton kho" in q:
        return _answer_low_stock()
    if "ban chay" in q or "top" in q or "ban nhieu" in q:
        return _answer_top_products(q)
    if "khach" in q:
        return _answer_customers()
    if "hoa don" in q or "don hang" in q or "gan day" in q:
        return _answer_recent_orders()

    # van la cau hoi cach dung nhung khong mo dau bang "cach..."
    for keywords, answer in USAGE.items():
        if any(k in q for k in keywords):
            return answer

    return HELP_TEXT


# ---------- che do Claude API ----------

def _ask_claude(question: str, history: list[dict]) -> str:
    from anthropic import Anthropic   # import muon: khong co key thi khoi can cai

    client = Anthropic()   # tu doc ANTHROPIC_API_KEY tu bien moi truong
    system = APP_GUIDE + "\n\n" + _data_snapshot()
    messages = list(history) + [{"role": "user", "content": question}]

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def ask(question: str, history: list[dict] | None = None) -> str:
    """Diem goi duy nhat cho giao dien chat.

    history: cac luot truoc dang [{"role": "user"/"assistant", "content": str}],
    chi dung o che do Claude (che do offline tra loi tung cau doc lap).
    """
    question = (question or "").strip()
    if not question:
        return HELP_TEXT

    if has_api():
        try:
            return _ask_claude(question, history or [])
        except Exception as exc:
            offline = _ask_rules(question)
            return (f"{offline}\n\n(Không gọi được Claude API — {exc}. "
                    "Đã trả lời bằng chế độ offline.)")
    return _ask_rules(question)
