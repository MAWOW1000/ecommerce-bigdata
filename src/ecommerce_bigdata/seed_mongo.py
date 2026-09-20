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

DEVICES = ["android", "ios", "desktop_web", "mobile_web"]
DEVICE_WEIGHTS = [0.41, 0.24, 0.21, 0.14]

CHANNELS = ["organic", "paid_search", "social", "email", "direct", "affiliate"]

SCAN_STATIONS = [
    "Kho Ha Noi", "Kho TP HCM", "Kho Da Nang", "Trung chuyen Bac Ninh",
    "Trung chuyen Binh Duong", "Buu cuc quan 7", "Buu cuc Cau Giay",
]

SCAN_TYPES = ["inbound_scan", "sorting", "outbound_scan", "out_for_delivery", "delivered", "failed_attempt"]

BATCH_SIZE = 5_000


def _load_reference_ids() -> tuple[list[int], list[int], list[tuple[int, str, datetime]]]:
    """Doc khoa tu SQL Server/PostgreSQL de log tham chieu dung, phuc vu JOIN o Chuong 4."""
    with psycopg.connect(PG.dsn) as conn:
        cur = conn.cursor()
        cur.execute("SET search_path TO ecom, public")
        cur.execute("SELECT ProductID FROM Product WHERE IsApproved = TRUE")
        product_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT CustomerID FROM Customer")
        customer_ids = [r[0] for r in cur.fetchall()]
        cur.execute(
            "SELECT OrderID, TrackingNo, ShippedAt FROM Shipment WHERE ShippedAt IS NOT NULL"
        )
        shipments = cur.fetchall()
    return product_ids, customer_ids, shipments


def _make_session(customer_ids: list[int], product_ids: list[int]) -> list[dict]:
    """Sinh mot phien duyet web: chuoi su kien co tinh nhat quan theo thoi gian."""
    session_id = str(uuid.uuid4())
    # 35% phien la khach vang lai (chua dang nhap) -> user_id = None
    user_id = random.choice(customer_ids) if random.random() < 0.65 else None
    device = random.choices(DEVICES, weights=DEVICE_WEIGHTS, k=1)[0]
    channel = random.choice(CHANNELS)
    province = fake.city()
    start = datetime(2025, 1, 1) + timedelta(seconds=random.randint(0, 610 * 86400))

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
            product_id = random.choice(product_ids)
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
                               [random.choice(product_ids)],
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


def _make_scans(shipments: list[tuple[int, str, datetime]]) -> list[dict]:
    """Log quet ma vach - mo phong thiet bi handheld tai kho, tan suat rat cao."""
    docs: list[dict] = []
    for order_id, tracking_no, shipped_at in shipments:
        cursor = shipped_at
        n_scans = random.randint(3, 8)
        for i in range(n_scans):
            cursor += timedelta(hours=random.uniform(1, 18))
            docs.append({
                "scan_id": str(uuid.uuid4()),
                "tracking_no": tracking_no,
                "order_id": order_id,
                "scan_type": SCAN_TYPES[min(i, len(SCAN_TYPES) - 1)],
                "station": random.choice(SCAN_STATIONS),
                "device_id": f"HH-{random.randint(1, 60):03d}",
                "operator": fake.name(),
                "timestamp": cursor,
                "weight_kg": round(random.uniform(0.1, 22.0), 2),
            })
    return docs


def seed() -> dict[str, int]:
    random.seed(SEED.random_seed)
    Faker.seed(SEED.random_seed)

    product_ids, customer_ids, shipments = _load_reference_ids()
    if not product_ids:
        raise RuntimeError("CSDL quan he chua co du lieu. Chay seed_sql truoc.")

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
        buffer.extend(_make_session(customer_ids, product_ids))
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
