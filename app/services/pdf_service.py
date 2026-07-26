"""Xuat hoa don ra PDF bang reportlab.

Tieng Viet co dau chi hien dung khi font DejaVu duoc dang ky VA moi style
deu chi dinh fontName='DejaVu'. Quen mot trong hai buoc thi chu co dau se
thanh o vuong.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.config import EXPORTS_DIR, FONT_BOLD, FONT_REGULAR
from app.utils.formatters import dt, money

FONT = "DejaVu"
FONT_B = "DejaVu-Bold"

_fonts_ready = False


def _register_fonts() -> None:
    """Chi dang ky mot lan cho ca vong doi tien trinh."""
    global _fonts_ready
    if _fonts_ready:
        return
    pdfmetrics.registerFont(TTFont(FONT, str(FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont(FONT_B, str(FONT_BOLD)))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_B)
    _fonts_ready = True


def _styles() -> dict:
    base = ParagraphStyle("base", fontName=FONT, fontSize=10, leading=14)
    return {
        "base": base,
        "title": ParagraphStyle("title", parent=base, fontName=FONT_B,
                                fontSize=18, alignment=TA_CENTER, leading=24),
        "sub": ParagraphStyle("sub", parent=base, alignment=TA_CENTER,
                              textColor=colors.grey),
        "right": ParagraphStyle("right", parent=base, alignment=TA_RIGHT),
        "right_bold": ParagraphStyle("right_bold", parent=base,
                                     fontName=FONT_B, alignment=TA_RIGHT,
                                     fontSize=12),
    }


def export_invoice(order: dict, target: Path | None = None) -> Path:
    """Ghi hoa don ra PDF, tra ve duong dan file."""
    _register_fonts()
    style = _styles()

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(target) if target else EXPORTS_DIR / f"{order['order_code']}.pdf"

    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Hóa đơn {order['order_code']}",
    )

    flow = [
        Paragraph("TECHSTORE", style["title"]),
        Paragraph("Cửa hàng thiết bị công nghệ", style["sub"]),
        Spacer(1, 10 * mm),
        Paragraph(f"<b>HÓA ĐƠN {order['order_code']}</b>", style["base"]),
        Paragraph(f"Thời gian: {dt(order['created_at'])}", style["base"]),
        Paragraph(f"Khách hàng: {order['customer']['name']}", style["base"]),
    ]
    phone = order["customer"].get("phone")
    if phone:
        flow.append(Paragraph(f"Điện thoại: {phone}", style["base"]))
    flow.append(Spacer(1, 6 * mm))

    header = ["STT", "Sản phẩm", "Danh mục", "Đơn giá", "SL", "Thành tiền"]
    data = [[Paragraph(f"<b>{c}</b>", style["base"]) for c in header]]

    for index, item in enumerate(order["items"], start=1):
        data.append([
            str(index),
            Paragraph(item["name"], style["base"]),
            Paragraph(item["category"], style["base"]),
            Paragraph(money(item["price"]), style["right"]),
            str(item["quantity"]),
            Paragraph(money(item["subtotal"]), style["right"]),
        ])

    table = Table(data, colWidths=[12 * mm, 52 * mm, 30 * mm, 30 * mm,
                                   12 * mm, 32 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecf0f1")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bdc3c7")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    flow.append(table)
    flow.append(Spacer(1, 6 * mm))

    refunded = order.get("refunded", 0)
    totals = [
        ("Tạm tính", money(order["subtotal"]), "right"),
        ("Giảm giá", money(order["discount"]), "right"),
        ("TỔNG CỘNG", money(order["total"]),
         "right" if refunded else "right_bold"),
    ]
    if refunded:
        # don da hoan tra mot phan: chung tu phai the hien so tien thuc thu
        totals.append(("Đã hoàn trả", "-" + money(refunded), "right"))
        totals.append(("THỰC THU", money(order["total"] - refunded),
                       "right_bold"))
    for label, value, key in totals:
        flow.append(Paragraph(f"{label}: {value}", style[key]))

    flow.append(Spacer(1, 12 * mm))
    flow.append(Paragraph("Cảm ơn quý khách đã mua hàng!", style["sub"]))

    doc.build(flow)
    return path
