"""Chuong 4 (giai doan 1) - Trich xuat du lieu len HDFS.

Mo phong dung luong ETL cua mot he thong that:

    PostgreSQL (giao dich)  ─┐
                             ├─► Parquet ─► HDFS  ─► Spark doc o buoc sau
    MongoDB (hanh vi)       ─┘

Parquet la dinh dang cot, nen theo tung cot nen ty le nen rat cao va Spark
chi doc dung cot can dung. Day la dinh dang mac dinh cua he sinh thai Hadoop.

Chay:  uv run python -m ecommerce_bigdata.hdfs_ingest
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import psycopg
from pymongo import MongoClient

from .config import MONGO, PG, PROJECT_ROOT

HADOOP_HOME = Path(os.environ.get(
    "HADOOP_HOME", Path.home() / ".local" / "hadoop" / "hadoop-3.4.1"))
HDFS_BIN = HADOOP_HOME / "bin" / "hdfs"
HADOOP_CONF_DIR = PROJECT_ROOT / "data" / "hdfs" / "runtime"
JAVA_HOME = os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64")

# Thu muc trung gian tren dia truoc khi day len HDFS
STAGING = PROJECT_ROOT / "data" / "staging"

# Cay thu muc tren HDFS, dat theo quy uoc data lake
HDFS_ROOT = "/ecommerce"
HDFS_RAW = f"{HDFS_ROOT}/raw"


def _hdfs_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "JAVA_HOME": JAVA_HOME,
        "HADOOP_HOME": str(HADOOP_HOME),
        "HADOOP_CONF_DIR": str(HADOOP_CONF_DIR),
        "HADOOP_LOG_DIR": str(PROJECT_ROOT / "data" / "logs" / "hadoop"),
    })
    return env


def hdfs(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Goi lenh `hdfs dfs ...`."""
    cmd = [str(HDFS_BIN), "dfs", *args]
    return subprocess.run(cmd, env=_hdfs_env(), check=check,
                          capture_output=True, text=True)


def _ensure_hdfs_running() -> None:
    result = hdfs("-ls", "/", check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "Khong ket noi duoc HDFS. Chay truoc: ./scripts/start_hdfs.sh\n"
            + result.stderr.strip()[:400])


# ---------------------------------------------------------------------------
# Trich xuat tu PostgreSQL
# ---------------------------------------------------------------------------
SQL_EXTRACTS: dict[str, str] = {
    "dim_product": """
        SELECT p.ProductID AS product_id, p.ProductName AS product_name,
               c.CategoryName AS category, s.ShopName AS shop,
               s.SellerID AS seller_id, p.BasePrice::float8 AS base_price
          FROM Product p
          JOIN Category c ON c.CategoryID = p.CategoryID
          JOIN Seller s   ON s.SellerID   = p.SellerID
    """,
    "dim_customer": """
        SELECT CustomerID AS customer_id, FullName AS full_name,
               Province AS province, RegisteredAt AS registered_at
          FROM Customer
    """,
    "fact_order_line": """
        SELECT o.OrderID AS order_id, o.CustomerID AS customer_id,
               o.OrderDate AS order_date, o.Status::text AS status,
               o.ShipProvince AS ship_province,
               v.ProductID AS product_id, d.VariantID AS variant_id,
               d.Quantity AS quantity, d.UnitPrice::float8 AS unit_price,
               (d.Quantity * d.UnitPrice)::float8 AS line_revenue
          FROM Orders o
          JOIN OrderDetail d    ON d.OrderID   = o.OrderID
          JOIN ProductVariant v ON v.VariantID = d.VariantID
    """,
    "fact_shipment": """
        SELECT OrderID AS order_id, TrackingNo AS tracking_no,
               Carrier AS carrier, Status::text AS status,
               ShippedAt AS shipped_at, DeliveredAt AS delivered_at
          FROM Shipment
    """,
}


def extract_postgres() -> dict[str, int]:
    print(">> Trich xuat tu PostgreSQL sang Parquet ...")
    counts: dict[str, int] = {}
    with psycopg.connect(PG.dsn, options="-c search_path=ecom,public") as conn:
        for name, sql in SQL_EXTRACTS.items():
            cur = conn.execute(sql)
            cols = [c.name for c in cur.description]
            df = pd.DataFrame(cur.fetchall(), columns=cols)

            out = STAGING / f"{name}.parquet"
            df.to_parquet(out, engine="pyarrow", compression="snappy", index=False)
            counts[name] = len(df)
            size_kb = out.stat().st_size / 1024
            print(f"   {name:<18} {len(df):>7,} dong  ->  {size_kb:>7,.0f} KB")
    return counts


# ---------------------------------------------------------------------------
# Trich xuat tu MongoDB
# ---------------------------------------------------------------------------
def extract_mongo() -> dict[str, int]:
    print(">> Trich xuat tu MongoDB sang Parquet ...")
    client = MongoClient(MONGO.uri)
    db = client[MONGO.database]
    counts: dict[str, int] = {}

    # --- Clickstream: lam phang cac truong long nhau de Spark doc de hon
    events = list(db["clickstream_events"].find({}, {
        "_id": 0, "event_id": 1, "session_id": 1, "user_id": 1,
        "event_type": 1, "timestamp": 1, "device.platform": 1,
        "geo.province": 1, "traffic_source.channel": 1,
        "payload.product_id": 1, "payload.revenue": 1, "payload.quantity": 1,
        "source": 1,
    }))
    df_events = pd.DataFrame([{
        "event_id": e.get("event_id"),
        "session_id": e.get("session_id"),
        "user_id": e.get("user_id"),
        "event_type": e.get("event_type"),
        "timestamp": e.get("timestamp"),
        "platform": (e.get("device") or {}).get("platform"),
        "province": (e.get("geo") or {}).get("province"),
        "channel": (e.get("traffic_source") or {}).get("channel"),
        "product_id": (e.get("payload") or {}).get("product_id"),
        "revenue": (e.get("payload") or {}).get("revenue"),
        "quantity": (e.get("payload") or {}).get("quantity"),
        "source": e.get("source", "mock"),
    } for e in events])

    # Phan vung theo ngay - dung dung cach Hive/Spark to chuc du lieu lon:
    # truy van loc theo ngay se chi doc dung thu muc can, bo qua phan con lai.
    df_events["event_date"] = pd.to_datetime(df_events["timestamp"]).dt.date.astype(str)

    events_dir = STAGING / "clickstream_events"
    shutil.rmtree(events_dir, ignore_errors=True)
    df_events.to_parquet(events_dir, engine="pyarrow", compression="snappy",
                         index=False, partition_cols=["event_date"])
    counts["clickstream_events"] = len(df_events)
    n_parts = len(list(events_dir.rglob("*.parquet")))
    print(f"   clickstream_events {len(df_events):>7,} dong  ->  {n_parts} phan vung theo ngay")

    # --- Log quet ma vach
    scans = list(db["shipment_scans"].find({}, {"_id": 0, "operator": 0}))
    df_scans = pd.DataFrame(scans)
    out = STAGING / "shipment_scans.parquet"
    df_scans.to_parquet(out, engine="pyarrow", compression="snappy", index=False)
    counts["shipment_scans"] = len(df_scans)
    print(f"   shipment_scans     {len(df_scans):>7,} dong  ->  "
          f"{out.stat().st_size / 1024:>7,.0f} KB")

    client.close()
    return counts


# ---------------------------------------------------------------------------
# Day len HDFS
# ---------------------------------------------------------------------------
def upload_to_hdfs() -> None:
    print(">> Day du lieu len HDFS ...")
    _ensure_hdfs_running()

    hdfs("-rm", "-r", "-f", "-skipTrash", HDFS_ROOT, check=False)
    hdfs("-mkdir", "-p", HDFS_RAW)

    for item in sorted(STAGING.iterdir()):
        hdfs("-put", "-f", str(item), f"{HDFS_RAW}/{item.name}")
        print(f"   {HDFS_RAW}/{item.name}")

    print("\n>> Cay thu muc tren HDFS:")
    print(hdfs("-du", "-h", HDFS_RAW).stdout.rstrip())

    print("\n>> Thong tin khoi du lieu (block):")
    report = subprocess.run(
        [str(HDFS_BIN), "fsck", HDFS_RAW, "-files", "-blocks"],
        env=_hdfs_env(), capture_output=True, text=True)
    for line in report.stdout.splitlines():
        if any(k in line for k in ("Total size", "Total files", "Total blocks",
                                   "Average block size", "HEALTHY", "replication")):
            print("   " + line.strip())


def main() -> None:
    shutil.rmtree(STAGING, ignore_errors=True)
    STAGING.mkdir(parents=True, exist_ok=True)

    sql_counts = extract_postgres()
    mongo_counts = extract_mongo()
    upload_to_hdfs()

    total = sum(sql_counts.values()) + sum(mongo_counts.values())
    print(f"\n>> Da nap {total:,} ban ghi len {HDFS_RAW}")


if __name__ == "__main__":
    main()
