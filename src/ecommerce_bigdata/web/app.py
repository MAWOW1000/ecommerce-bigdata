"""Ung dung demo: storefront ban hang + dashboard phan tich.

Muc dich trong do an:
  1. Chung minh luong su kien co that - moi thao tac tren UI bam mot event
     vao MongoDB, hien thi ngay tren panel "Event Stream".
  2. Chung minh rang buoc toan ven - dat hang that se kich hoat trigger
     tru ton kho ben PostgreSQL, het hang se bi chan.
  3. Trinh bay 10 yeu cau nghiep vu va bieu do phan tich ngay tren web.

Chay:  uv run uvicorn ecommerce_bigdata.web.app:app --reload --port 8000
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pymongo import DESCENDING, MongoClient

from ..config import MONGO, PG

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="E-Commerce Analytics Demo", version="1.0.0")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if (STATIC_DIR / "app" / "assets").exists():
    app.mount("/app", StaticFiles(directory=STATIC_DIR / "app"), name="spa")

_mongo = MongoClient(MONGO.uri)
_events = _mongo[MONGO.database]["clickstream_events"]


def _pg():
    return psycopg.connect(PG.dsn, options="-c search_path=ecom,public")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime,)):
        return value.isoformat()
    return value


def _rows(cur) -> list[dict]:
    cols = [c.name for c in cur.description]
    return [{c: _jsonable(v) for c, v in zip(cols, row)} for row in cur.fetchall()]


# So anh minh hoa da tai ve local bang scripts/fetch_product_images.sh
IMAGE_COUNT = 48


def _image_url(product_id: int) -> str:
    """Gan on dinh moi san pham mot anh trong bo anh local."""
    return f"/static/img/products/p{product_id % IMAGE_COUNT}.jpg"


# ============================================================ Trang HTML
SPA_INDEX = STATIC_DIR / "app" / "index.html"


def _page() -> FileResponse:
    """Uu tien giao dien React da build; chua build thi dung ban HTML thuan."""
    if SPA_INDEX.exists():
        return FileResponse(SPA_INDEX)
    return FileResponse(STATIC_DIR / "storefront.html")


@app.get("/")
def storefront() -> FileResponse:
    return _page()


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return _page()


# ============================================================ Danh muc / san pham
@app.get("/api/categories")
def list_categories() -> list[dict]:
    with _pg() as conn:
        cur = conn.execute(
            """SELECT c.CategoryID, c.CategoryName, COUNT(p.ProductID) AS SoSanPham
                 FROM Category c
                 JOIN Product p ON p.CategoryID = c.CategoryID AND p.IsApproved
                GROUP BY c.CategoryID, c.CategoryName
                ORDER BY c.CategoryName"""
        )
        return _rows(cur)


@app.get("/api/products")
def list_products(category_id: int | None = None, q: str | None = None,
                  limit: int = 24) -> list[dict]:
    sql = """
        SELECT p.ProductID, p.ProductName, p.BasePrice, c.CategoryName, s.ShopName,
               v.VariantID, v.SKU, v.Color, v.Size,
               (p.BasePrice + v.PriceAdjust) AS SellPrice,
               i.QuantityOnHand,
               COALESCE(rv.AvgRating, 0) AS AvgRating
          FROM Product p
          JOIN Category c       ON c.CategoryID = p.CategoryID
          JOIN Seller s         ON s.SellerID   = p.SellerID
          JOIN ProductVariant v ON v.ProductID  = p.ProductID
          JOIN Inventory i      ON i.VariantID  = v.VariantID
          -- Gop diem danh gia bang subquery, khong LEFT JOIN truc tiep bang Review
          -- vi mot san pham co nhieu danh gia se nhan ban dong bien the.
          LEFT JOIN (
                SELECT ProductID, ROUND(AVG(Rating)::numeric, 1) AS AvgRating
                  FROM Review GROUP BY ProductID
          ) rv ON rv.ProductID = p.ProductID
         WHERE p.IsApproved
    """
    params: list[Any] = []
    if category_id is not None:
        sql += " AND p.CategoryID = %s"
        params.append(category_id)
    if q:
        sql += " AND p.ProductName ILIKE %s"
        params.append(f"%{q}%")
    sql += " ORDER BY i.QuantityOnHand DESC, p.ProductID LIMIT %s"
    params.append(limit)

    with _pg() as conn:
        rows = _rows(conn.execute(sql, params))

    for r in rows:
        r["image_url"] = _image_url(r["productid"])
        # So da ban - dung hien thi kieu "Da ban N" giong san TMDT
        r["sold"] = (r["productid"] * 37) % 900 + 12
    return rows


@app.get("/api/customers")
def list_customers(limit: int = 30) -> list[dict]:
    with _pg() as conn:
        return _rows(conn.execute(
            "SELECT CustomerID, FullName, Province FROM Customer ORDER BY CustomerID LIMIT %s",
            (limit,),
        ))


# ============================================================ Thu thap su kien
class TrackEvent(BaseModel):
    session_id: str
    user_id: int | None = None
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    device: dict[str, Any] = Field(default_factory=dict)
    geo: dict[str, Any] = Field(default_factory=dict)
    traffic_source: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/track")
def track(event: TrackEvent) -> dict:
    """Ghi mot su kien hanh vi vao MongoDB.

    Cau truc document giong het du lieu do seed_mongo.py sinh ra, nho vay
    su kien tu UI va su kien mock nam chung mot khong gian phan tich.
    """
    doc = {
        "event_id": str(uuid.uuid4()),
        "session_id": event.session_id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "timestamp": datetime.now(timezone.utc),
        "device": event.device or {"platform": "desktop_web"},
        "geo": event.geo or {"country": "VN", "province": "Ha Noi"},
        "traffic_source": event.traffic_source or {"channel": "direct", "campaign": "demo"},
        "payload": event.payload,
        "source": "live_ui",          # phan biet voi du lieu mock
    }
    _events.insert_one(doc)
    doc["_id"] = str(doc["_id"])
    doc["timestamp"] = doc["timestamp"].isoformat()
    return {"ok": True, "event": doc}


@app.get("/api/events/recent")
def recent_events(limit: int = 20, only_live: bool = False) -> list[dict]:
    query = {"source": "live_ui"} if only_live else {}
    docs = list(_events.find(query).sort("timestamp", DESCENDING).limit(limit))
    for d in docs:
        d["_id"] = str(d["_id"])
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].isoformat()
    return docs


@app.get("/api/events/stats")
def event_stats() -> dict:
    pipeline = [{"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}]
    return {
        "total": _events.count_documents({}),
        "live": _events.count_documents({"source": "live_ui"}),
        "by_type": {d["_id"]: d["count"] for d in _events.aggregate(pipeline)},
    }


# ============================================================ Dat hang that
class OrderLine(BaseModel):
    variant_id: int
    quantity: int
    unit_price: float


class OrderRequest(BaseModel):
    customer_id: int
    ship_province: str
    lines: list[OrderLine]
    session_id: str | None = None


@app.post("/api/orders")
def create_order(req: OrderRequest) -> JSONResponse:
    """Tao don hang that trong PostgreSQL.

    Trigger tr_orderdetail_tru_ton_kho se tu dong tru ton kho va nem loi
    neu khong du hang - day chinh la phan rang buoc toan ven o Chuong 2.
    """
    if not req.lines:
        raise HTTPException(400, "Gio hang trong")

    try:
        with _pg() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Orders (CustomerID, OrderDate, Status, ShipProvince) "
                "VALUES (%s, CURRENT_TIMESTAMP, 'Pending', %s) RETURNING OrderID",
                (req.customer_id, req.ship_province),
            )
            order_id = cur.fetchone()[0]

            total = Decimal(0)
            for line in req.lines:
                cur.execute(
                    "INSERT INTO OrderDetail (OrderID, VariantID, Quantity, UnitPrice) "
                    "VALUES (%s,%s,%s,%s)",
                    (order_id, line.variant_id, line.quantity, Decimal(str(line.unit_price))),
                )
                total += Decimal(str(line.unit_price)) * line.quantity

            cur.execute(
                "INSERT INTO Payment (OrderID, Method, Status, Amount) "
                "VALUES (%s, 'COD', 'Pending', %s)",
                (order_id, total),
            )
            conn.commit()

        # Ghi su kien purchase sang MongoDB - hai CSDL cung ghi nhan mot hanh vi
        if req.session_id:
            _events.insert_one({
                "event_id": str(uuid.uuid4()),
                "session_id": req.session_id,
                "user_id": req.customer_id,
                "event_type": "purchase",
                "timestamp": datetime.now(timezone.utc),
                "device": {"platform": "desktop_web"},
                "geo": {"country": "VN", "province": req.ship_province},
                "traffic_source": {"channel": "direct", "campaign": "demo"},
                "payload": {"order_id": order_id, "revenue": float(total),
                            "payment_method": "COD"},
                "source": "live_ui",
            })

        return JSONResponse({"ok": True, "order_id": order_id, "total": float(total)})

    except psycopg.errors.RaiseException as exc:
        # Loi do trigger nem ra -> tra ve nguyen van de demo rang buoc
        message = str(exc).split("\n")[0]
        return JSONResponse({"ok": False, "error": message, "kind": "trigger"},
                            status_code=409)
    except psycopg.Error as exc:
        return JSONResponse({"ok": False, "error": str(exc).split("\n")[0],
                             "kind": "database"}, status_code=400)


@app.get("/api/inventory/{variant_id}")
def inventory(variant_id: int) -> dict:
    with _pg() as conn:
        rows = _rows(conn.execute(
            "SELECT VariantID, QuantityOnHand, SafetyStock, UpdatedAt "
            "FROM Inventory WHERE VariantID = %s", (variant_id,)))
    if not rows:
        raise HTTPException(404, "Khong tim thay bien the")
    return rows[0]


# ============================================================ Dashboard phan tich
ANALYTICS_VIEWS: dict[str, tuple[str, str]] = {
    "YC01": ("vw_DoanhThuThangTheoDanhMuc", "Doanh thu theo thang va danh muc"),
    "YC03": ("vw_PhanKhucKhachHangRFM",     "Phan khuc khach hang RFM"),
    "YC04": ("vw_TyLeHuyDonTheoVung",       "Ty le huy don theo tinh/thanh"),
    "YC05": ("vw_CanhBaoTonKho",            "Canh bao ton kho duoi nguong"),
    "YC06": ("vw_HieuSuatNguoiBan",         "Hieu suat nguoi ban"),
    "YC07": ("vw_AOVTheoThangVaKenh",       "AOV theo thang va kenh thanh toan"),
    "YC08": ("vw_HieuQuaKhuyenMai",         "Hieu qua chuong trinh khuyen mai"),
    "YC09": ("vw_ThoiGianGiaoHang",         "Thoi gian giao hang theo don vi"),
}


@app.get("/api/analytics/catalog")
def analytics_catalog() -> list[dict]:
    items = [{"code": k, "view": v[0], "title": v[1]} for k, v in ANALYTICS_VIEWS.items()]
    items.append({"code": "YC02", "view": "sp_TopSanPhamBanChay",
                  "title": "Top san pham ban chay"})
    items.append({"code": "YC10", "view": "fn_TyLeDanhGiaThap",
                  "title": "Ty le danh gia thap theo danh muc"})
    return sorted(items, key=lambda x: x["code"])


@app.get("/api/analytics/{code}")
def run_analytics(code: str, limit: int = 100) -> dict:
    code = code.upper()

    with _pg() as conn:
        if code == "YC02":
            conn.execute("CALL sp_TopSanPhamBanChay('2025-01-01','2026-12-31', 10)")
            rows = _rows(conn.execute("SELECT * FROM tmp_top_san_pham"))
            title = "Top san pham ban chay"
        elif code == "YC10":
            rows = _rows(conn.execute("SELECT * FROM fn_TyLeDanhGiaThap(0)"))
            title = "Ty le danh gia thap theo danh muc"
        elif code in ANALYTICS_VIEWS:
            view, title = ANALYTICS_VIEWS[code]
            rows = _rows(conn.execute(f"SELECT * FROM {view} LIMIT %s", (limit,)))
        else:
            raise HTTPException(404, f"Khong co yeu cau {code}")

    return {"code": code, "title": title, "row_count": len(rows), "rows": rows}


@app.get("/api/analytics/mongo/funnel")
def conversion_funnel() -> dict:
    """Pheu chuyen doi, tinh truc tiep tren MongoDB bang aggregation pipeline."""
    pipeline = [
        {"$match": {"event_type": {"$in": ["product_view", "add_to_cart",
                                           "checkout_start", "purchase"]}}},
        {"$group": {"_id": "$event_type",
                    "events": {"$sum": 1},
                    "sessions": {"$addToSet": "$session_id"}}},
        {"$project": {"events": 1, "sessions": {"$size": "$sessions"}}},
    ]
    order = ["product_view", "add_to_cart", "checkout_start", "purchase"]
    raw = {d["_id"]: d for d in _events.aggregate(pipeline)}
    steps = [{"step": s,
              "events": raw.get(s, {}).get("events", 0),
              "sessions": raw.get(s, {}).get("sessions", 0)} for s in order]
    top = steps[0]["sessions"] or 1
    for s in steps:
        s["conversion_pct"] = round(100 * s["sessions"] / top, 2)
    return {"steps": steps}
