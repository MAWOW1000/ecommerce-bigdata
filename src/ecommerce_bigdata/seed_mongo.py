"""Sinh du lieu log phi cau truc va day vao MongoDB (Chuong 3).

Hai collection:
  - clickstream_events : su kien hanh vi nguoi dung tren web/app
  - shipment_scans     : log quet ma vach tai kho / diem trung chuyen

Chay:  uv run python -m ecommerce_bigdata.seed_mongo
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta

import psycopg
from faker import Faker
from pymongo import ASCENDING, DESCENDING, MongoClient

from .config import MONGO, PG, SEED

fake = Faker("vi_VN")

EVENT_TYPES = [
    "page_view", "search", "product_view", "add_to_cart",
    "remove_from_cart", "checkout_start", "purchase",
]

# Trong so mo phong hinh pheu: cang ve sau cang it su kien
EVENT_WEIGHTS = [0.30, 0.16, 0.28, 0.13, 0.04, 0.06, 0.03]

CHANNELS = ["organic", "paid_search", "social", "email", "direct", "affiliate"]

SCAN_STATIONS = [
    "Kho Ha Noi", "Kho TP HCM", "Kho Da Nang", "Trung chuyen Bac Ninh",
    "Trung chuyen Binh Duong", "Buu cuc quan 7", "Buu cuc Cau Giay",
]

SCAN_TYPES = ["inbound_scan", "sorting", "outbound_scan", "out_for_delivery", "delivered", "failed_attempt"]

# Trong so luu luong theo gio trong ngay (0h -> 23h).
# Mo phong nhip sinh hoat thuc te: thap nhat rang sang, hai dinh vao gio nghi
# trua va buoi toi. Khong co phan nay thi bieu do nhiet o Chuong 4 se phang det.
HOUR_WEIGHTS = [
    18, 9, 5, 3, 3, 6,        # 00h - 05h: rang sang, gan nhu khong ai dung
    14, 30, 46, 55, 58, 62,   # 06h - 11h: tang dan trong gio hanh chinh
    78, 66, 58, 57, 62, 74,   # 12h - 17h: dinh gio nghi trua roi chung lai
    92, 110, 128, 120, 86, 44 # 18h - 23h: dinh cao nhat buoi toi
]

# Ty le nen tang thay doi theo khung gio: ban ngay nhieu nguoi dung may tinh
# o cong ty, buoi toi gan nhu chi con dien thoai.
PLATFORM_BY_HOUR = {
    "night":   (["android", "ios", "mobile_web", "desktop_web"], [0.50, 0.28, 0.16, 0.06]),
    "office":  (["android", "ios", "mobile_web", "desktop_web"], [0.30, 0.18, 0.10, 0.42]),
    "evening": (["android", "ios", "mobile_web", "desktop_web"], [0.46, 0.27, 0.18, 0.09]),
}


def _pick_hour() -> int:
    """Chon gio bat dau phien theo phan phoi luu luong thuc te."""
    return random.choices(range(24), weights=HOUR_WEIGHTS, k=1)[0]


def _platform_for_hour(hour: int) -> str:
    if hour < 6 or hour >= 22:
        bucket = "night"
    elif 8 <= hour < 18:
        bucket = "office"
    else:
        bucket = "evening"
    platforms, weights = PLATFORM_BY_HOUR[bucket]
    return random.choices(platforms, weights=weights, k=1)[0]

BATCH_SIZE = 5_000


def _load_reference_ids() -> tuple[
    list[int], list[int], list[tuple[int, str, datetime, str]], dict[int, float]
]:
    """Doc khoa tu SQL Server/PostgreSQL de log tham chieu dung, phuc vu JOIN o Chuong 4."""
    with psycopg.connect(PG.dsn) as conn:
        cur = conn.cursor()
        cur.execute("SET search_path TO ecom, public")
        # Lay kem so luong da ban de dung lam trong so do pho bien. Nho vay
        # luot xem trong log co tuong quan (khong hoan hao) voi doanh so thuc -
        # giong thi truong that, thay vi moi san pham duoc xem nhu nhau.
        cur.execute("""
            SELECT p.ProductID, COALESCE(SUM(d.Quantity), 0) AS units_sold
              FROM Product p
              LEFT JOIN ProductVariant v ON v.ProductID = p.ProductID
              LEFT JOIN OrderDetail d    ON d.VariantID = v.VariantID
             WHERE p.IsApproved = TRUE
             GROUP BY p.ProductID
        """)
        rows = cur.fetchall()
        product_ids = [r[0] for r in rows]
        product_sales = {r[0]: float(r[1]) for r in rows}
        cur.execute("SELECT CustomerID FROM Customer")
        customer_ids = [r[0] for r in cur.fetchall()]
        cur.execute(
            "SELECT OrderID, TrackingNo, ShippedAt, Carrier FROM Shipment "
            "WHERE ShippedAt IS NOT NULL"
        )
        shipments = cur.fetchall()
    return product_ids, customer_ids, shipments, product_sales


def _build_popularity(product_ids: list[int],
                      product_sales: dict[int, float]) -> list[float]:
    """Trong so xac suat mot san pham duoc xem.

    Lay doanh so lam nen, nhan them nhieu lognormal de quan he giua luot xem va
    doanh thu la co that nhung khong hoan hao - dung nhu thuc te, va nho vay
    bieu do doi chieu o Chuong 4 moi co y nghia phan tich.
    """
    weights: list[float] = []
    for pid in product_ids:
        base = product_sales.get(pid, 0.0) + 3.0          # san moi cung co luot xem
        noise = random.lognormvariate(0.0, 0.85)
        weights.append(base * noise)
    return weights


def _make_session(customer_ids: list[int], product_ids: list[int],
                  popularity: list[float]) -> list[dict]:
    """Sinh mot phien duyet web: chuoi su kien co tinh nhat quan theo thoi gian."""
    session_id = str(uuid.uuid4())
    # 35% phien la khach vang lai (chua dang nhap) -> user_id = None
    user_id = random.choice(customer_ids) if random.random() < 0.65 else None
    channel = random.choice(CHANNELS)
    province = fake.city()

    # Ngay ngau nhien, nhung gio trong ngay thi theo phan phoi luu luong.
    day = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 609))
    hour = _pick_hour()
    start = day.replace(hour=hour, minute=random.randint(0, 59),
                        second=random.randint(0, 59))
    device = _platform_for_hour(hour)

    events: list[dict] = []
    cursor = start
    n_events = random.randint(1, 12)
    viewed: list[int] = []

    for _ in range(n_events):
        etype = random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS, k=1)[0]
        cursor += timedelta(seconds=random.randint(3, 240))

        doc: dict = {
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user_id,
            "event_type": etype,
            "timestamp": cursor,
            "device": {
                "platform": device,
                "os_version": f"{random.randint(9, 18)}.{random.randint(0, 5)}",
                "app_version": f"{random.randint(3, 7)}.{random.randint(0, 20)}.0",
            },
            "geo": {"country": "VN", "province": province},
            "traffic_source": {"channel": channel, "campaign": fake.word()},
        }

        pick_product = lambda: random.choices(product_ids, weights=popularity, k=1)[0]

        if etype == "search":
            doc["payload"] = {
                "query": fake.word(),
                "result_count": random.randint(0, 480),
                "filters_applied": random.sample(
                    ["price_asc", "rating_4plus", "free_ship", "brand"],
                    k=random.randint(0, 2),
                ),
            }
        elif etype in ("product_view", "add_to_cart", "remove_from_cart"):
            product_id = pick_product()
            viewed.append(product_id)
            doc["payload"] = {
                "product_id": product_id,
                "dwell_seconds": random.randint(1, 300),
                "position_in_list": random.randint(1, 60),
            }
            if etype == "add_to_cart":
                doc["payload"]["quantity"] = random.randint(1, 3)
        elif etype == "checkout_start":
            doc["payload"] = {
                "cart_size": random.randint(1, 6),
                "cart_value": round(random.uniform(90_000, 18_000_000), 2),
            }
        elif etype == "purchase":
            doc["payload"] = {
                "product_ids": random.sample(viewed, k=min(len(viewed), 3)) or
                               [pick_product()],
                "revenue": round(random.uniform(90_000, 18_000_000), 2),
                "payment_method": random.choice(["COD", "EWallet", "CreditCard", "BankTransfer"]),
            }
        else:  # page_view
            doc["payload"] = {
                "page": random.choice(["/", "/category", "/search", "/cart", "/promotion"]),
                "referrer": random.choice(["google.com", "facebook.com", "direct", "tiktok.com"]),
            }

        events.append(doc)

    return events


# Mang luoi cua tung hang khac nhau: hang chay tuyen thang qua it diem trung
# chuyen hon, nen vua giao nhanh vua it lan quet. Nho vay bieu do doi chieu
# o Chuong 4 moi phan anh dung quan he giua hai nguon du lieu.
CARRIER_HOPS = {
    "GHN": (3, 5), "GHTK": (3, 6), "J&T Express": (4, 7),
    "Viettel Post": (5, 8), "Ninja Van": (6, 9),
}


def _make_scans(shipments: list[tuple[int, str, datetime, str]]) -> list[dict]:
    """Log quet ma vach - mo phong thiet bi handheld tai kho, tan suat rat cao."""
    docs: list[dict] = []
    for order_id, tracking_no, shipped_at, carrier in shipments:
        cursor = shipped_at
        lo, hi = CARRIER_HOPS.get(carrier, (3, 8))
        n_scans = random.randint(lo, hi)
        for i in range(n_scans):
            cursor += timedelta(hours=random.uniform(1, 18))
            docs.append({
                "scan_id": str(uuid.uuid4()),
                "tracking_no": tracking_no,
                "order_id": order_id,
                "scan_type": SCAN_TYPES[min(i, len(SCAN_TYPES) - 1)],
                "station": random.choice(SCAN_STATIONS),
                "carrier": carrier,
                "device_id": f"HH-{random.randint(1, 60):03d}",
                "operator": fake.name(),
                "timestamp": cursor,
                "weight_kg": round(random.uniform(0.1, 22.0), 2),
            })
    return docs


def seed() -> dict[str, int]:
    random.seed(SEED.random_seed)
    Faker.seed(SEED.random_seed)

    product_ids, customer_ids, shipments, product_sales = _load_reference_ids()
    if not product_ids:
        raise RuntimeError("CSDL quan he chua co du lieu. Chay seed_sql truoc.")
    popularity = _build_popularity(product_ids, product_sales)

    client = MongoClient(MONGO.uri)
    db = client[MONGO.database]
    db.drop_collection("clickstream_events")
    db.drop_collection("shipment_scans")

    clicks = db["clickstream_events"]
    scans = db["shipment_scans"]

    print(f">> Sinh ~{SEED.log_events:,} su kien clickstream ...")
    buffer: list[dict] = []
    total_events = 0
    while total_events < SEED.log_events:
        buffer.extend(_make_session(customer_ids, product_ids, popularity))
        if len(buffer) >= BATCH_SIZE:
            clicks.insert_many(buffer, ordered=False)
            total_events += len(buffer)
            print(f"   ... {total_events:,} su kien")
            buffer = []
    if buffer:
        clicks.insert_many(buffer, ordered=False)
        total_events += len(buffer)

    print(f">> Sinh log quet ma vach cho {len(shipments):,} lo hang ...")
    scan_docs = _make_scans(shipments)
    for i in range(0, len(scan_docs), BATCH_SIZE):
        scans.insert_many(scan_docs[i:i + BATCH_SIZE], ordered=False)

    print(">> Tao chi muc ...")
    clicks.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
    clicks.create_index([("event_type", ASCENDING), ("timestamp", DESCENDING)])
    clicks.create_index([("payload.product_id", ASCENDING)])
    clicks.create_index([("session_id", ASCENDING)])
    scans.create_index([("tracking_no", ASCENDING), ("timestamp", ASCENDING)])
    scans.create_index([("order_id", ASCENDING)])

    stats = {
        "clickstream_events": clicks.count_documents({}),
        "shipment_scans": scans.count_documents({}),
    }
    client.close()
    return stats


if __name__ == "__main__":
    result = seed()
    print("\n=== SO DOCUMENT DA SINH ===")
    for name, count in result.items():
        print(f"{name:<22} {count:>10,}")
