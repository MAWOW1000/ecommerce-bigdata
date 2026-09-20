"""Sinh so do thuc the - lien ket (ERD) duoi dang SVG va PNG.

Ve thang bang SVG thay vi dung Graphviz de kiem soat bo cuc va mau sac,
va de khong phai cai them cong cu he thong.

Chay:  uv run python scripts/generate_erd.py
"""

from __future__ import annotations

import subprocess
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets"

WIDTH, HEIGHT = 1980, 1215
HEADER_H, ROW_H = 34, 25
PAD = 10

BRAND = "#ee4d2d"
INK = "#1f2937"
MUTED = "#6b7280"
LINE = "#c7ccd6"
BG = "#ffffff"

# Toa do x cua 4 cot va tam "hanh lang" giua chung.
# Moi duong quan he chi chay trong hanh lang, khong bao gio cat qua hop.
COL = [40, 430, 900, 1380]
LANE = [375, 845, 1340]        # tam hanh lang giua cot 0-1, 1-2, 2-3
LANE_GAP = 20                  # khoang cach giua hai lan trong cung hanh lang

# Mau nen theo nhom nghiep vu
GROUPS = {
    "catalog": "#fff4f0",   # danh muc / san pham
    "order":   "#eef4ff",   # don hang
    "fulfil":  "#eefaf2",   # thanh toan / van chuyen
    "people":  "#fdf6e9",   # nguoi dung
}

# (x, y, rong, nhom, [(loai_khoa, ten_cot, kieu_du_lieu)])
ENTITIES: dict[str, dict] = {
    # --- Cot 1: goc danh muc
    "Seller": dict(x=COL[0], y=110, w=280, group="people", rows=[
        ("PK", "SellerID", "INT IDENTITY"),
        ("UQ", "ShopName", "NVARCHAR(150)"),
        ("UQ", "ContactEmail", "VARCHAR(255)"),
        ("", "Province", "NVARCHAR(100)"),
        ("", "JoinedAt", "DATETIME2"),
        ("", "RatingAvg", "DECIMAL(3,2)"),
    ]),
    "Category": dict(x=COL[0], y=420, w=280, group="catalog", rows=[
        ("PK", "CategoryID", "INT IDENTITY"),
        ("UQ", "CategoryName", "NVARCHAR(120)"),
        ("FK", "ParentID", "INT NULL"),
    ]),

    # --- Cot 2: san pham
    "Product": dict(x=COL[1], y=110, w=300, group="catalog", rows=[
        ("PK", "ProductID", "INT IDENTITY"),
        ("FK", "SellerID", "INT"),
        ("FK", "CategoryID", "INT"),
        ("", "ProductName", "NVARCHAR(250)"),
        ("", "BasePrice", "DECIMAL(18,2)"),
        ("", "IsApproved", "BIT"),
        ("", "CreatedAt", "DATETIME2"),
    ]),
    "ProductVariant": dict(x=COL[1], y=430, w=300, group="catalog", rows=[
        ("PK", "VariantID", "INT IDENTITY"),
        ("FK", "ProductID", "INT"),
        ("UQ", "SKU", "VARCHAR(64)"),
        ("", "Color", "NVARCHAR(50)"),
        ("", "Size", "NVARCHAR(30)"),
        ("", "PriceAdjust", "DECIMAL(18,2)"),
    ]),
    "Inventory": dict(x=COL[1], y=700, w=300, group="catalog", rows=[
        ("PK,FK", "VariantID", "INT"),
        ("", "QuantityOnHand", "INT"),
        ("", "SafetyStock", "INT"),
        ("", "UpdatedAt", "DATETIME2"),
    ]),

    # --- Cot 3: giao dich
    "Customer": dict(x=COL[2], y=110, w=300, group="people", rows=[
        ("PK", "CustomerID", "INT IDENTITY"),
        ("", "FullName", "NVARCHAR(150)"),
        ("UQ", "Email", "VARCHAR(255)"),
        ("", "Phone", "VARCHAR(20)"),
        ("", "Province", "NVARCHAR(100)"),
        ("", "Address", "NVARCHAR(300)"),
        ("", "RegisteredAt", "DATETIME2"),
    ]),
    "Orders": dict(x=COL[2], y=430, w=300, group="order", rows=[
        ("PK", "OrderID", "INT IDENTITY"),
        ("FK", "CustomerID", "INT"),
        ("FK", "PromotionID", "INT NULL"),
        ("", "OrderDate", "DATETIME2"),
        ("", "Status", "VARCHAR(12)"),
        ("", "ShipProvince", "NVARCHAR(100)"),
        ("", "CancelReason", "NVARCHAR(200)"),
        ("", "DiscountAmount", "DECIMAL(18,2)"),
    ]),
    "OrderDetail": dict(x=COL[2], y=790, w=300, group="order", rows=[
        ("PK,FK", "OrderID", "INT"),
        ("PK,FK", "VariantID", "INT"),
        ("", "Quantity", "INT"),
        ("", "UnitPrice", "DECIMAL(18,2)"),
    ]),

    # --- Cot 4: he qua cua don hang
    "Promotion": dict(x=COL[3], y=110, w=290, group="order", rows=[
        ("PK", "PromotionID", "INT IDENTITY"),
        ("UQ", "PromoCode", "VARCHAR(40)"),
        ("", "DiscountPct", "DECIMAL(5,2)"),
        ("", "MaxDiscount", "DECIMAL(18,2)"),
        ("", "StartDate", "DATE"),
        ("", "EndDate", "DATE"),
    ]),
    "Payment": dict(x=COL[3], y=370, w=290, group="fulfil", rows=[
        ("PK", "PaymentID", "INT IDENTITY"),
        ("UQ,FK", "OrderID", "INT"),
        ("", "Method", "VARCHAR(15)"),
        ("", "Status", "VARCHAR(10)"),
        ("", "Amount", "DECIMAL(18,2)"),
        ("", "PaidAt", "DATETIME2"),
    ]),
    "Shipment": dict(x=COL[3], y=620, w=290, group="fulfil", rows=[
        ("PK", "ShipmentID", "INT IDENTITY"),
        ("UQ,FK", "OrderID", "INT"),
        ("", "Carrier", "NVARCHAR(80)"),
        ("UQ", "TrackingNo", "VARCHAR(64)"),
        ("", "Status", "VARCHAR(12)"),
        ("", "ShippedAt", "DATETIME2"),
        ("", "DeliveredAt", "DATETIME2"),
    ]),
    "Review": dict(x=COL[3], y=890, w=290, group="fulfil", rows=[
        ("PK", "ReviewID", "INT IDENTITY"),
        ("FK", "ProductID", "INT"),
        ("FK", "CustomerID", "INT"),
        ("FK", "OrderID", "INT"),
        ("", "Rating", "TINYINT"),
        ("", "Comment", "NVARCHAR(1000)"),
    ]),
}

# (bang_nguon, canh_nguon, bang_dich, canh_dich, ban_so, ghi_chu)
RELATIONS = [
    # (cha, con, ban_so, ghi_chu) - luon noi canh phai cua cha sang canh trai cua con,
    # tru khi hai bang cung mot cot thi noi doc.
    ("Seller",         "Product",        "1 : N",    "dang ban"),
    ("Category",       "Product",        "1 : N",    "phan loai"),
    ("Product",        "ProductVariant", "1 : N",    "co bien the"),
    ("ProductVariant", "Inventory",      "1 : 1",    "ton kho"),
    ("ProductVariant", "OrderDetail",    "1 : N",    "duoc dat"),
    ("Customer",       "Orders",         "1 : N",    "dat"),
    ("Orders",         "OrderDetail",    "1 : N",    "gom"),
    ("Promotion",      "Orders",         "0..1 : N", "ap dung"),
    ("Orders",         "Payment",        "1 : 1",    "thanh toan"),
    ("Orders",         "Shipment",       "1 : 1",    "giao"),
    ("Product",        "Review",         "1 : N",    "duoc danh gia"),
    ("Customer",       "Review",         "1 : N",    "viet"),
]


def column_of(name: str) -> int:
    return COL.index(ENTITIES[name]["x"])


def box_height(entity: dict) -> int:
    return HEADER_H + len(entity["rows"]) * ROW_H + 6


def render_entity(name: str, e: dict) -> str:
    h = box_height(e)
    fill = GROUPS[e["group"]]
    parts = [
        f'<g class="entity">',
        f'<rect x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{h}" rx="8" '
        f'fill="{fill}" stroke="{LINE}" stroke-width="1.2"/>',
        f'<path d="M{e["x"]} {e["y"] + HEADER_H} h{e["w"]}" stroke="{LINE}" stroke-width="1.2"/>',
        f'<rect x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{HEADER_H}" rx="8" '
        f'fill="{BRAND}" fill-opacity="0.92"/>',
        f'<rect x="{e["x"]}" y="{e["y"] + HEADER_H - 8}" width="{e["w"]}" height="8" '
        f'fill="{BRAND}" fill-opacity="0.92"/>',
        f'<text x="{e["x"] + PAD}" y="{e["y"] + 23}" font-size="15" font-weight="700" '
        f'fill="#ffffff">{escape(name)}</text>',
    ]

    for i, (key, col, dtype) in enumerate(e["rows"]):
        y = e["y"] + HEADER_H + (i + 1) * ROW_H - 7
        weight = "700" if "PK" in key else "400"
        color = INK if key else MUTED
        badge = ""
        if key:
            badge_fill = "#fde68a" if "PK" in key else ("#dbeafe" if "FK" in key else "#e5e7eb")
            badge = (f'<rect x="{e["x"] + PAD}" y="{y - 12}" width="46" height="16" rx="4" '
                     f'fill="{badge_fill}"/>'
                     f'<text x="{e["x"] + PAD + 23}" y="{y}" font-size="9.5" '
                     f'text-anchor="middle" fill="#374151" font-weight="600">{key}</text>')
        parts.append(badge)
        parts.append(
            f'<text x="{e["x"] + PAD + (52 if key else 0)}" y="{y}" font-size="12" '
            f'font-weight="{weight}" fill="{color}">{escape(col)}</text>')
        parts.append(
            f'<text x="{e["x"] + e["w"] - PAD}" y="{y}" font-size="10" text-anchor="end" '
            f'fill="{MUTED}">{escape(dtype)}</text>')

    parts.append("</g>")
    return "\n".join(parts)


def render_relation(src: str, dst: str, card: str, lane_slot: float = 0.0) -> str:
    """Ve duong quan he di vong qua hanh lang giua cac cot.

    lane_slot la do lech (tinh bang pixel) so voi tam hanh lang, de nhieu quan
    he dung chung mot hanh lang khong bi ve chong len nhau.
    """
    a, b = ENTITIES[src], ENTITIES[dst]
    ca, cb = column_of(src), column_of(dst)
    ha, hb = box_height(a), box_height(b)

    if ca == cb:
        # Cung cot -> noi doc tu day bang cha xuong dinh bang con
        x = a["x"] + a["w"] * 0.5
        y1, y2 = a["y"] + ha, b["y"]
        path = f"M{x} {y1} V{y2}"
        lx, ly = x, (y1 + y2) / 2
    else:
        lo, hi = min(ca, cb), max(ca, cb)
        lane = (LANE[lo] if hi - lo == 1 else LANE[hi - 1]) + lane_slot

        if ca < cb:                      # cha ben trai -> con ben phai
            x1, y1 = a["x"] + a["w"], a["y"] + ha / 2
            x2, y2 = b["x"], b["y"] + hb / 2
        else:                            # cha ben phai -> con ben trai
            x1, y1 = a["x"], a["y"] + ha / 2
            x2, y2 = b["x"] + b["w"], b["y"] + hb / 2

        path = f"M{x1} {y1} H{lane} V{y2} H{x2}"

        # Dat nhan tren doan chay doc, lech theo lan de hai nhan khong de len
        # nhau khi hai quan he tinh co co cung diem giua.
        lo_y, hi_y = min(y1, y2), max(y1, y2)
        ly = min(max((y1 + y2) / 2 + lane_slot * 1.6, lo_y + 14), hi_y - 14)
        lx = lane

    w = 8 + len(card) * 5.2
    return (
        f'<path d="{path}" fill="none" stroke="{BRAND}" stroke-width="1.6" '
        f'stroke-opacity="0.8" marker-end="url(#arrow)"/>'
        f'<rect x="{lx - w / 2}" y="{ly - 9}" width="{w}" height="17" rx="4" '
        f'fill="{BG}" stroke="{LINE}" stroke-width="0.8"/>'
        f'<text x="{lx}" y="{ly + 3.5}" font-size="9.5" text-anchor="middle" '
        f'fill="{INK}" font-weight="600">{escape(card)}</text>'
    )


def build_svg() -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="Segoe UI, Helvetica, Arial, sans-serif">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>',
        '<defs>'
        f'<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{BRAND}" fill-opacity="0.75"/></marker>'
        '</defs>',
        f'<text x="40" y="38" font-size="20" font-weight="700" fill="{INK}">'
        f'So do thuc the - lien ket (ERD): San thuong mai dien tu da nguoi ban</text>',
    ]

    # Ve quan he truoc de duong nam duoi hop.
    # Dem so quan he da dung moi hanh lang de cap phat lan rieng cho tung duong.
    def lane_key(src: str, dst: str) -> int | None:
        ca, cb = column_of(src), column_of(dst)
        if ca == cb:
            return None
        lo, hi = min(ca, cb), max(ca, cb)
        return lo if hi - lo == 1 else hi - 1

    # Luot 1: dem so quan he tren moi hanh lang
    lane_total: dict[int, int] = {}
    for src, dst, _, _ in RELATIONS:
        key = lane_key(src, dst)
        if key is not None:
            lane_total[key] = lane_total.get(key, 0) + 1

    # Luot 2: chia deu cac lan ve hai phia quanh tam hanh lang
    lane_seen: dict[int, int] = {}
    for src, dst, card, _ in RELATIONS:
        key = lane_key(src, dst)
        if key is None:
            offset = 0.0
        else:
            i = lane_seen.get(key, 0)
            lane_seen[key] = i + 1
            offset = (i - (lane_total[key] - 1) / 2) * LANE_GAP
        parts.append(render_relation(src, dst, card, offset))
    for name, e in ENTITIES.items():
        parts.append(render_entity(name, e))

    # Chu giai
    lx, ly = 40, HEIGHT - 52
    parts.append(f'<text x="{lx}" y="{ly}" font-size="11.5" font-weight="700" '
                 f'fill="{INK}">Chu giai</text>')
    legend = [("PK", "#fde68a", "Khoa chinh"), ("FK", "#dbeafe", "Khoa ngoai"),
              ("UQ", "#e5e7eb", "Rang buoc duy nhat")]
    x = lx
    for key, fill, label in legend:
        parts.append(f'<rect x="{x}" y="{ly + 8}" width="42" height="16" rx="4" fill="{fill}"/>')
        parts.append(f'<text x="{x + 21}" y="{ly + 19.5}" font-size="9.5" text-anchor="middle" '
                     f'fill="#374151" font-weight="600">{key}</text>')
        parts.append(f'<text x="{x + 50}" y="{ly + 20}" font-size="11" fill="{MUTED}">{label}</text>')
        x += 190
    parts.append(f'<text x="{x + 30}" y="{ly + 20}" font-size="11" fill="{MUTED}">'
                 f'Mui ten tro tu bang cha sang bang con (phia khoa ngoai)</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    svg_path = OUT_DIR / "ERD_ECommerce.svg"
    svg_path.write_text(build_svg(), encoding="utf-8")
    print(f">> {svg_path.relative_to(ROOT)}")

    png_path = OUT_DIR / "ERD_ECommerce.png"
    for cmd in (["rsvg-convert", "-w", "2200", "-o", str(png_path), str(svg_path)],
                ["inkscape", str(svg_path), "-w", "2200", "-o", str(png_path)],
                ["convert", "-density", "160", str(svg_path), str(png_path)]):
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f">> {png_path.relative_to(ROOT)} (bang {cmd[0]})")
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    print(">> Khong tim thay cong cu chuyen SVG sang PNG "
          "(rsvg-convert / inkscape / convert). Chi xuat SVG.", file=sys.stderr)


if __name__ == "__main__":
    main()
