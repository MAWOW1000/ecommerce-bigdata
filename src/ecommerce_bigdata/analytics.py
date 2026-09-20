"""Chuong 4 - Xu ly va phan tich du lieu lon.

Script doc song song hai nguon du lieu, doi chieu va gop chung tren khoa
ProductID, roi xuat cac bieu do phan tich kem nhan xet nghiep vu.

    PostgreSQL (danh muc, don hang)  ─┐
                                      ├─► pandas.merge ─► bieu do PNG + CSV
    MongoDB (clickstream, scan log)  ─┘

Chay:  uv run python -m ecommerce_bigdata.analytics
"""

from __future__ import annotations

import textwrap
from datetime import datetime

import matplotlib
import pandas as pd
import psycopg
from pymongo import MongoClient

matplotlib.use("Agg")                      # khong can man hinh
import matplotlib.pyplot as plt            # noqa: E402

from .config import ASSETS_DIR, EXPORT_DIR, MONGO, PG   # noqa: E402

# ---------------------------------------------------------------------------
# Thiet lap trinh bay chung cho moi bieu do
# ---------------------------------------------------------------------------
PALETTE = ["#ee4d2d", "#2f80ed", "#27ae60", "#f2994a", "#9b51e0", "#00b8d9"]

plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 130,
    "font.size": 10,
    "axes.titlesize": 12.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "figure.autolayout": True,
})

CHART_DIR = ASSETS_DIR / "charts"

# Ghi lai nhan xet nghiep vu cua tung bieu do de dua thang vao bao cao
INSIGHTS: list[tuple[str, str, str]] = []      # (ma, tieu de, nhan xet)


def _save(fig: plt.Figure, name: str, title: str, insight: str) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    path = CHART_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    INSIGHTS.append((name, title, insight))
    print(f"   [chart] {path.name}")


# ---------------------------------------------------------------------------
# 1. Doc du lieu tu hai nguon
# ---------------------------------------------------------------------------
def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Doi cot kieu Decimal cua PostgreSQL sang float.

    psycopg tra ve DECIMAL duoi dang decimal.Decimal, pandas xep vao dtype
    'object' nen cac phep thong ke nhu nlargest/corr se bao loi.
    """
    for col in df.columns:
        if df[col].dtype == "object":
            converted = pd.to_numeric(df[col], errors="coerce")
            # Chi doi khi toan bo gia tri khong rong deu la so
            if converted.notna().sum() == df[col].notna().sum() and df[col].notna().any():
                df[col] = converted.astype(float)
    return df



def load_sql_frames() -> dict[str, pd.DataFrame]:
    """Doc du lieu giao dich tu CSDL quan he."""
    print(">> Doc du lieu tu PostgreSQL ...")
    queries = {
        # Doanh thu theo san pham - de doi chieu voi luot xem ben MongoDB
        "product_revenue": """
            SELECT p.ProductID          AS product_id,
                   p.ProductName        AS product_name,
                   c.CategoryName       AS category,
                   s.ShopName           AS shop,
                   COUNT(DISTINCT o.OrderID)          AS orders,
                   COALESCE(SUM(d.Quantity), 0)       AS units_sold,
                   COALESCE(SUM(d.Quantity * d.UnitPrice), 0) AS revenue
              FROM Product p
              JOIN Category c        ON c.CategoryID = p.CategoryID
              JOIN Seller s          ON s.SellerID   = p.SellerID
              LEFT JOIN ProductVariant v ON v.ProductID = p.ProductID
              LEFT JOIN OrderDetail d    ON d.VariantID = v.VariantID
              LEFT JOIN Orders o         ON o.OrderID   = d.OrderID
                                        AND o.Status    = 'Delivered'
             GROUP BY p.ProductID, p.ProductName, c.CategoryName, s.ShopName
        """,
        # Doanh thu theo thang, dung ve duong xu huong
        "monthly_revenue": """
            SELECT DATE_TRUNC('month', o.OrderDate)::date AS month,
                   c.CategoryName                          AS category,
                   SUM(d.Quantity * d.UnitPrice)           AS revenue
              FROM Orders o
              JOIN OrderDetail d    ON d.OrderID   = o.OrderID
              JOIN ProductVariant v ON v.VariantID = d.VariantID
              JOIN Product p        ON p.ProductID = v.ProductID
              JOIN Category c       ON c.CategoryID = p.CategoryID
             WHERE o.Status = 'Delivered'
             GROUP BY 1, 2
        """,
        # Thoi gian giao hang - doi chieu voi so lan quet ma vach ben MongoDB
        "shipments": """
            SELECT sh.OrderID    AS order_id,
                   sh.TrackingNo AS tracking_no,
                   sh.Carrier    AS carrier,
                   sh.Status     AS status,
                   EXTRACT(EPOCH FROM (sh.DeliveredAt - sh.ShippedAt)) / 86400.0
                                 AS delivery_days
              FROM Shipment sh
             WHERE sh.ShippedAt IS NOT NULL
        """,
    }

    frames: dict[str, pd.DataFrame] = {}
    with psycopg.connect(PG.dsn, options="-c search_path=ecom,public") as conn:
        for name, sql in queries.items():
            cur = conn.execute(sql)
            cols = [c.name for c in cur.description]
            frames[name] = _coerce_numeric(pd.DataFrame(cur.fetchall(), columns=cols))
            print(f"   {name:<18} {len(frames[name]):>6,} dong")
    return frames


def load_mongo_frames() -> dict[str, pd.DataFrame]:
    """Doc du lieu hanh vi tu MongoDB bang aggregation pipeline.

    Gop ngay trong database thay vi keo toan bo 50.000 document ve Python -
    day la cach lam dung voi du lieu lon.
    """
    print(">> Doc du lieu tu MongoDB ...")
    client = MongoClient(MONGO.uri)
    db = client[MONGO.database]
    events = db["clickstream_events"]
    scans = db["shipment_scans"]

    # -- Luot xem / them gio theo san pham
    product_engagement = list(events.aggregate([
        {"$match": {"payload.product_id": {"$exists": True}}},
        {"$group": {
            "_id": {"product_id": "$payload.product_id", "event_type": "$event_type"},
            "count": {"$sum": 1},
            "sessions": {"$addToSet": "$session_id"},
        }},
        {"$project": {"count": 1, "sessions": {"$size": "$sessions"}}},
    ]))
    engagement = pd.DataFrame([
        {"product_id": d["_id"]["product_id"],
         "event_type": d["_id"]["event_type"],
         "events": d["count"],
         "sessions": d["sessions"]}
        for d in product_engagement
    ])

    # -- Su kien theo gio trong ngay va theo thiet bi
    hourly = pd.DataFrame(list(events.aggregate([
        {"$group": {
            "_id": {"hour": {"$hour": "$timestamp"}, "platform": "$device.platform"},
            "events": {"$sum": 1},
        }},
    ])))
    if not hourly.empty:
        hourly = pd.DataFrame([
            {"hour": r["_id"]["hour"], "platform": r["_id"]["platform"], "events": r["events"]}
            for _, r in hourly.iterrows()
        ])

    # -- Pheu chuyen doi
    funnel_raw = list(events.aggregate([
        {"$match": {"event_type": {"$in": ["product_view", "add_to_cart",
                                           "checkout_start", "purchase"]}}},
        {"$group": {"_id": "$event_type", "sessions": {"$addToSet": "$session_id"}}},
        {"$project": {"sessions": {"$size": "$sessions"}}},
    ]))
    funnel = pd.DataFrame([{"step": d["_id"], "sessions": d["sessions"]} for d in funnel_raw])

    # -- So lan quet ma vach moi lo hang
    scan_counts = pd.DataFrame(list(scans.aggregate([
        {"$group": {"_id": "$tracking_no", "scans": {"$sum": 1},
                    "stations": {"$addToSet": "$station"}}},
        {"$project": {"scans": 1, "stations": {"$size": "$stations"}}},
    ])))
    if not scan_counts.empty:
        scan_counts = scan_counts.rename(columns={"_id": "tracking_no"})

    client.close()
    for name, df in [("engagement", engagement), ("hourly", hourly),
                     ("funnel", funnel), ("scan_counts", scan_counts)]:
        print(f"   {name:<18} {len(df):>6,} dong")
    return {"engagement": engagement, "hourly": hourly,
            "funnel": funnel, "scan_counts": scan_counts}


# ---------------------------------------------------------------------------
# 2. Doi chieu va gop hai nguon
# ---------------------------------------------------------------------------
def join_sources(sql: dict[str, pd.DataFrame],
                 mongo: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Gop du lieu danh muc (SQL) voi du lieu log (MongoDB)."""
    print(">> Doi chieu va gop hai nguon ...")

    # --- Gop 1: san pham  <->  hanh vi xem/them gio
    eng = mongo["engagement"]
    wide = (eng.pivot_table(index="product_id", columns="event_type",
                            values="sessions", aggfunc="sum", fill_value=0)
            .reset_index() if not eng.empty else pd.DataFrame({"product_id": []}))
    for col in ("product_view", "add_to_cart", "remove_from_cart"):
        if col not in wide.columns:
            wide[col] = 0

    product = sql["product_revenue"].merge(wide, on="product_id", how="left")
    product[["product_view", "add_to_cart", "remove_from_cart"]] = (
        product[["product_view", "add_to_cart", "remove_from_cart"]].fillna(0).astype(int))

    # Ty le chuyen doi tu luot xem sang don ban duoc - chi tinh duoc khi
    # co ca hai nguon du lieu.
    product["view_to_sale_pct"] = (
        100 * product["units_sold"] / product["product_view"].where(product["product_view"] > 0)
    ).round(2)

    matched = int((product["product_view"] > 0).sum())
    print(f"   Gop san pham: {len(product):,} dong, {matched:,} san pham co du lieu hanh vi")

    # --- Gop 2: lo hang  <->  so lan quet ma vach
    shipments = sql["shipments"].merge(mongo["scan_counts"], on="tracking_no", how="left")
    shipments["scans"] = shipments["scans"].fillna(0).astype(int)
    matched_ship = int((shipments["scans"] > 0).sum())
    print(f"   Gop lo hang:  {len(shipments):,} dong, {matched_ship:,} lo co log quet")

    return {"product": product, "shipments": shipments}


# ---------------------------------------------------------------------------
# 3. Bieu do
# ---------------------------------------------------------------------------
def chart_funnel(funnel: pd.DataFrame) -> None:
    order = ["product_view", "add_to_cart", "checkout_start", "purchase"]
    labels = ["Xem san pham", "Them vao gio", "Bat dau thanh toan", "Mua hang"]
    df = funnel.set_index("step").reindex(order).fillna(0)
    values = df["sessions"].to_numpy()
    top = values[0] if values[0] else 1
    pct = 100 * values / top

    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.bar(labels, values, color=PALETTE[:4], width=0.62)
    for bar, v, p in zip(bars, values, pct):
        ax.text(bar.get_x() + bar.get_width() / 2, v, f"{int(v):,}\n({p:.1f}%)",
                ha="center", va="bottom", fontsize=9.5)
    ax.set_ylabel("So phien duy nhat")
    ax.set_title("Pheu chuyen doi - tinh tu clickstream trong MongoDB")
    ax.set_ylim(0, values.max() * 1.22)

    drop = 100 - pct[-1]
    _save(fig, "01_funnel", "4.1. Phễu chuyển đổi",
          f"Từ lượt xem sản phẩm đến lúc mua hàng, hệ thống mất {drop:.1f}% số phiên. "
          f"Hụt lớn nhất nằm ở bước từ 'Thêm vào giỏ' ({pct[1]:.1f}%) xuống "
          f"'Bắt đầu thanh toán' ({pct[2]:.1f}%), gợi ý rằng màn hình giỏ hàng "
          f"và chi phí vận chuyển là điểm cần tối ưu trước tiên.")


def chart_monthly_revenue(monthly: pd.DataFrame) -> None:
    total = monthly.groupby("month", as_index=False)["revenue"].sum().sort_values("month")
    top_cats = (monthly.groupby("category")["revenue"].sum()
                .nlargest(4).index.tolist())

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    ax.plot(total["month"], total["revenue"] / 1e9, color="#333", linewidth=2.4,
            marker="o", markersize=4, label="Tong doanh thu", zorder=5)
    for i, cat in enumerate(top_cats):
        sub = (monthly[monthly["category"] == cat]
               .groupby("month", as_index=False)["revenue"].sum().sort_values("month"))
        ax.plot(sub["month"], sub["revenue"] / 1e9, color=PALETTE[i],
                linewidth=1.5, alpha=0.85, label=cat)

    ax.set_ylabel("Doanh thu (ty VND)")
    ax.set_title("Xu huong doanh thu theo thang")
    ax.legend(fontsize=8.5, ncol=3, frameon=False)
    fig.autofmt_xdate(rotation=30)

    best = total.loc[total["revenue"].idxmax()]
    worst = total.loc[total["revenue"].idxmin()]
    _save(fig, "02_monthly_revenue", "4.2. Xu hướng doanh thu theo tháng",
          f"Doanh thu đạt đỉnh vào {best['month']:%m/%Y} ({best['revenue']/1e9:.1f} tỷ) "
          f"và thấp nhất vào {worst['month']:%m/%Y} ({worst['revenue']/1e9:.1f} tỷ). "
          f"Bốn danh mục dẫn đầu là {', '.join(top_cats)}; kế hoạch nhập hàng nên bám "
          f"theo nhịp mùa vụ này.")


def chart_view_vs_revenue(product: pd.DataFrame) -> None:
    """Bieu do the hien ro nhat gia tri cua viec gop hai CSDL."""
    df = product[(product["product_view"] > 0) & (product["revenue"] > 0)].copy()

    fig, ax = plt.subplots(figsize=(8.2, 5))
    cats = df["category"].value_counts().nlargest(6).index.tolist()
    for i, cat in enumerate(cats):
        sub = df[df["category"] == cat]
        ax.scatter(sub["product_view"], sub["revenue"] / 1e6,
                   s=26, alpha=0.7, color=PALETTE[i % len(PALETTE)], label=cat)

    ax.set_xlabel("So phien xem san pham (MongoDB)")
    ax.set_ylabel("Doanh thu (trieu VND) (PostgreSQL)")
    ax.set_title("Luot xem so voi doanh thu tung san pham")
    ax.legend(fontsize=8, frameon=False, ncol=2)

    corr = df["product_view"].corr(df["revenue"])
    # San pham nhieu nguoi xem nhung ban kem - nhom can xem lai gia hoac mo ta
    df["rank_view"] = df["product_view"].rank(pct=True)
    df["rank_rev"] = df["revenue"].rank(pct=True)
    leak = df[(df["rank_view"] > 0.75) & (df["rank_rev"] < 0.35)]

    _save(fig, "03_view_vs_revenue", "4.3. Lượt xem so với doanh thu",
          f"Hệ số tương quan giữa lượt xem và doanh thu chỉ đạt {corr:.2f}, nghĩa là "
          f"nhiều người xem không bảo đảm bán được hàng. Có {len(leak)} sản phẩm nằm "
          f"trong nhóm 25% được xem nhiều nhất nhưng lại thuộc 35% doanh thu thấp nhất "
          f"— đây là nhóm cần rà soát lại giá bán, ảnh mô tả và chi phí vận chuyển. "
          f"Phát hiện này chỉ có được khi gộp dữ liệu hành vi (MongoDB) với dữ liệu "
          f"giao dịch (PostgreSQL).")


def chart_hourly_heatmap(hourly: pd.DataFrame) -> None:
    pivot = hourly.pivot_table(index="platform", columns="hour",
                               values="events", aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(columns=range(24), fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 3.2))
    im = ax.imshow(pivot.to_numpy(), aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}h" for h in range(0, 24, 2)])
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    ax.set_title("Mat do su kien theo gio trong ngay va theo nen tang")
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.85, label="So su kien")

    by_hour = pivot.sum(axis=0)
    peak = by_hour.idxmax()
    quiet = by_hour.idxmin()
    top_platform = pivot.sum(axis=1).idxmax()
    _save(fig, "04_hourly_heatmap", "4.4. Mật độ sự kiện theo giờ",
          f"Lưu lượng đạt đỉnh lúc {peak:02d}h và thấp nhất lúc {quiet:02d}h. "
          f"Nền tảng chiếm nhiều sự kiện nhất là {top_platform}. Khung giờ cao điểm "
          f"này quyết định thời điểm chạy khuyến mãi flash sale, đồng thời là căn cứ "
          f"để đặt lịch sao lưu và bảo trì hệ thống vào khung giờ thấp điểm.")


def chart_carrier_performance(shipments: pd.DataFrame) -> None:
    df = shipments.dropna(subset=["delivery_days"])
    agg = (df.groupby("carrier")
             .agg(days=("delivery_days", "mean"),
                  scans=("scans", "mean"),
                  n=("order_id", "count"))
             .sort_values("days"))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4))
    ax1.barh(agg.index, agg["days"], color=PALETTE[0], height=0.6)
    ax1.set_xlabel("So ngay giao trung binh")
    ax1.set_title("Toc do giao hang (PostgreSQL)")
    ax1.invert_yaxis()
    for i, v in enumerate(agg["days"]):
        ax1.text(v, i, f" {v:.2f}", va="center", fontsize=9)

    ax2.barh(agg.index, agg["scans"], color=PALETTE[1], height=0.6)
    ax2.set_xlabel("So lan quet ma vach trung binh / lo")
    ax2.set_title("So chang trung chuyen (MongoDB)")
    ax2.invert_yaxis()
    for i, v in enumerate(agg["scans"]):
        ax2.text(v, i, f" {v:.1f}", va="center", fontsize=9)

    fastest, slowest = agg.index[0], agg.index[-1]
    gap = agg["days"].iloc[-1] - agg["days"].iloc[0]

    # Tinh tuong quan tu chinh du lieu thay vi khang dinh san.
    corr = agg["days"].corr(agg["scans"]) if len(agg) > 2 else float("nan")
    if pd.notna(corr) and corr >= 0.6:
        relation = (f"Số chặng trung chuyển đi liền với thời gian giao (tương quan "
                    f"{corr:.2f}): hãng càng nhiều điểm quét thì đơn càng lâu đến tay "
                    f"khách, gợi ý nên rút bớt chặng cho các tuyến nội thành.")
    elif pd.notna(corr) and corr <= -0.6:
        relation = (f"Số chặng trung chuyển ngược chiều với thời gian giao (tương quan "
                    f"{corr:.2f}).")
    else:
        relation = (f"Tương quan giữa số chặng trung chuyển và thời gian giao chỉ đạt "
                    f"{corr:.2f}, nghĩa là chênh lệch tốc độ đến từ năng lực nội bộ của "
                    f"từng hãng chứ không phải do số điểm trung chuyển.")

    _save(fig, "05_carrier_performance", "4.5. Hiệu suất đơn vị vận chuyển",
          f"{fastest} giao nhanh nhất ({agg['days'].iloc[0]:.2f} ngày), {slowest} chậm "
          f"nhất ({agg['days'].iloc[-1]:.2f} ngày) — chênh {gap:.2f} ngày. {relation} "
          f"Nên ưu tiên {fastest} cho các đơn gấp.")


def chart_category_mix(product: pd.DataFrame) -> None:
    agg = (product.groupby("category")
                  .agg(revenue=("revenue", "sum"), views=("product_view", "sum"))
                  .sort_values("revenue", ascending=False).head(10))

    x = range(len(agg))
    fig, ax1 = plt.subplots(figsize=(10, 4.4))
    ax1.bar(x, agg["revenue"] / 1e9, color=PALETTE[0], width=0.6, label="Doanh thu")
    ax1.set_ylabel("Doanh thu (ty VND)", color=PALETTE[0])
    ax1.set_xticks(list(x), agg.index, rotation=28, ha="right", fontsize=9)

    ax2 = ax1.twinx()
    ax2.plot(x, agg["views"], color=PALETTE[1], marker="o", linewidth=2, label="Luot xem")
    ax2.set_ylabel("So phien xem", color=PALETTE[1])
    ax2.grid(False)

    ax1.set_title("Doanh thu va luot quan tam theo danh muc")

    billions = (agg["revenue"] / 1e9)
    agg["view_per_billion"] = agg["views"] / billions.where(billions > 0)
    hot = agg["view_per_billion"].idxmax()
    _save(fig, "06_category_mix", "4.6. Doanh thu và lượt quan tâm theo danh mục",
          f"Danh mục {agg.index[0]} dẫn đầu doanh thu. Ngược lại, {hot} thu hút nhiều "
          f"lượt xem nhất trên mỗi tỷ doanh thu — nhiều người quan tâm nhưng giá trị "
          f"đơn thấp, phù hợp để làm sản phẩm kéo chân khách rồi bán chéo sang danh "
          f"mục giá trị cao hơn.")


# ---------------------------------------------------------------------------
# 4. Xuat ket qua
# ---------------------------------------------------------------------------
def export_tables(joined: dict[str, pd.DataFrame]) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    product = joined["product"].sort_values("revenue", ascending=False)
    product.to_csv(EXPORT_DIR / "product_sql_mongo_joined.csv", index=False)
    joined["shipments"].to_csv(EXPORT_DIR / "shipment_sql_mongo_joined.csv", index=False)
    print(f"   [csv] product_sql_mongo_joined.csv ({len(product):,} dong)")
    print(f"   [csv] shipment_sql_mongo_joined.csv ({len(joined['shipments']):,} dong)")


def write_insight_report() -> None:
    """Ghi nhan xet nghiep vu ra Markdown de dua thang vao Chuong 4."""
    lines = [
        "# Chương 4 — Phân tích dữ liệu lớn: biểu đồ và ý nghĩa nghiệp vụ",
        "",
        f"*Sinh tự động bởi `analytics.py` lúc {datetime.now():%d/%m/%Y %H:%M}*",
        "",
        "Mỗi biểu đồ dưới đây được dựng từ dữ liệu đã gộp giữa PostgreSQL "
        "(dữ liệu giao dịch) và MongoDB (dữ liệu hành vi).",
        "",
    ]
    for name, title, insight in INSIGHTS:
        lines += [
            f"## {title}",
            "",
            f"![{title}](../assets/charts/{name}.png)",
            "",
            "**Ý nghĩa nghiệp vụ:** " + textwrap.fill(insight, 95).replace("\n", "\n"),
            "",
        ]
    path = EXPORT_DIR.parent.parent / "docs" / "04_phan_tich.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"   [doc] {path.relative_to(path.parents[1])}")


def main() -> None:
    sql = load_sql_frames()
    mongo = load_mongo_frames()
    joined = join_sources(sql, mongo)

    print(">> Ve bieu do ...")
    chart_funnel(mongo["funnel"])
    chart_monthly_revenue(sql["monthly_revenue"])
    chart_view_vs_revenue(joined["product"])
    chart_hourly_heatmap(mongo["hourly"])
    chart_carrier_performance(joined["shipments"])
    chart_category_mix(joined["product"])

    print(">> Xuat bang du lieu ...")
    export_tables(joined)
    write_insight_report()

    print("\n=== NHAN XET NGHIEP VU ===")
    for _, title, insight in INSIGHTS:
        print(f"\n[{title}]")
        print(textwrap.fill(insight, 88, initial_indent="  ", subsequent_indent="  "))


if __name__ == "__main__":
    main()
