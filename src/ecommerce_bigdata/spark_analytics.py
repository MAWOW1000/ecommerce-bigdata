"""Chuong 4 (giai doan 2) - Phan tich du lieu lon bang Apache Spark tren HDFS.

Khac biet so voi analytics.py:

    analytics.py        doc thang tu PostgreSQL/MongoDB vao pandas, xu ly trong
                        bo nho mot tien trinh. Don gian, hop voi vai chuc nghin
                        ban ghi.

    spark_analytics.py  doc tu HDFS bang Spark. Du lieu duoc chia khoi, moi khoi
                        xu ly song song tren nhieu executor. Cung mot doan ma
                        chay duoc tren mot may lan tren cum hang tram may.

Spark chay o che do local[*] - mot JVM, moi loi CPU la mot executor. Day la
cach chay Spark tren may ca nhan; len cum chi can doi --master.

Chay:  uv run python -m ecommerce_bigdata.spark_analytics
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64")

from pyspark.sql import DataFrame, SparkSession           # noqa: E402
from pyspark.sql import functions as F                    # noqa: E402
from pyspark.sql.window import Window                     # noqa: E402

from .config import EXPORT_DIR, PROJECT_ROOT              # noqa: E402

HDFS_URI = "hdfs://127.0.0.1:9000"
RAW = f"{HDFS_URI}/ecommerce/raw"
CURATED = f"{HDFS_URI}/ecommerce/curated"

RESULT_DIR = EXPORT_DIR / "spark"


def build_session() -> SparkSession:
    """Tao phien Spark ket noi toi HDFS."""
    return (
        SparkSession.builder
        .appName("ECommerce-BigData-Analytics")
        .master("local[*]")
        .config("spark.hadoop.fs.defaultFS", HDFS_URI)
        .config("spark.sql.shuffle.partitions", "8")     # mac dinh 200, qua nhieu cho may le
        .config("spark.driver.memory", "2g")
        .config("spark.sql.session.timeZone", "Asia/Ho_Chi_Minh")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


def _show(title: str, df: DataFrame, n: int = 8) -> None:
    print(f"\n--- {title} ---")
    df.show(n, truncate=False)


def _save(df: DataFrame, name: str) -> None:
    """Ghi ket qua vao lop curated tren HDFS, dong thoi xuat CSV de dua vao bao cao."""
    df.coalesce(1).write.mode("overwrite").parquet(f"{CURATED}/{name}")
    pdf = df.toPandas()
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.to_csv(RESULT_DIR / f"{name}.csv", index=False)
    print(f"   [luu] {CURATED}/{name}  ({len(pdf):,} dong)")


# ---------------------------------------------------------------------------
# Cac phep phan tich
# ---------------------------------------------------------------------------
def phan_tich_san_pham(order_line: DataFrame, product: DataFrame,
                       events: DataFrame) -> DataFrame:
    """Gop du lieu giao dich voi du lieu hanh vi tren khoa product_id.

    Day chinh la buoc 'doi chieu va gop' ma de bai yeu cau, nhung thuc hien
    bang Spark tren HDFS thay vi pandas trong bo nho.
    """
    doanh_thu = (
        order_line.filter(F.col("status") == "Delivered")
        .groupBy("product_id")
        .agg(F.countDistinct("order_id").alias("so_don"),
             F.sum("quantity").alias("so_luong_ban"),
             F.sum("line_revenue").alias("doanh_thu"))
    )

    hanh_vi = (
        events.filter(F.col("product_id").isNotNull())
        .groupBy("product_id")
        .pivot("event_type", ["product_view", "add_to_cart", "remove_from_cart"])
        .agg(F.countDistinct("session_id"))
        .na.fill(0)
    )

    return (
        product.join(doanh_thu, "product_id", "left")
               .join(hanh_vi, "product_id", "left")
               .na.fill(0, ["so_don", "so_luong_ban", "doanh_thu",
                            "product_view", "add_to_cart", "remove_from_cart"])
               .withColumn(
                   "ty_le_xem_thanh_don",
                   F.round(F.when(F.col("product_view") > 0,
                                  100 * F.col("so_luong_ban") / F.col("product_view")), 2))
               .select("product_id", "product_name", "category", "shop",
                       "so_don", "so_luong_ban", "doanh_thu",
                       "product_view", "add_to_cart", "ty_le_xem_thanh_don")
    )


def pheu_chuyen_doi(events: DataFrame) -> DataFrame:
    buoc = ["product_view", "add_to_cart", "checkout_start", "purchase"]
    df = (
        events.filter(F.col("event_type").isin(buoc))
        .groupBy("event_type")
        .agg(F.countDistinct("session_id").alias("so_phien"),
             F.count("*").alias("so_su_kien"))
    )
    dinh = df.agg(F.max("so_phien")).collect()[0][0] or 1
    thu_tu = F.when(F.col("event_type") == "product_view", 1) \
              .when(F.col("event_type") == "add_to_cart", 2) \
              .when(F.col("event_type") == "checkout_start", 3).otherwise(4)
    return (df.withColumn("thu_tu", thu_tu)
              .withColumn("ty_le_pct", F.round(100 * F.col("so_phien") / F.lit(dinh), 2))
              .orderBy("thu_tu"))


def doanh_thu_theo_thang(order_line: DataFrame, product: DataFrame) -> DataFrame:
    return (
        order_line.filter(F.col("status") == "Delivered")
        .join(product.select("product_id", "category"), "product_id")
        .withColumn("thang", F.date_format("order_date", "yyyy-MM"))
        .groupBy("thang", "category")
        .agg(F.round(F.sum("line_revenue"), 0).alias("doanh_thu"),
             F.sum("quantity").alias("so_luong"))
        .orderBy("thang", F.desc("doanh_thu"))
    )


def hieu_suat_van_chuyen(shipment: DataFrame, scans: DataFrame) -> DataFrame:
    """Gop bang Shipment (quan he) voi log quet ma vach (NoSQL) tren tracking_no."""
    so_chang = scans.groupBy("tracking_no").agg(
        F.count("*").alias("so_lan_quet"),
        F.countDistinct("station").alias("so_tram"))

    return (
        shipment.filter(F.col("shipped_at").isNotNull()
                        & F.col("delivered_at").isNotNull())
        .join(so_chang, "tracking_no", "left")
        .withColumn("so_ngay_giao",
                    (F.unix_timestamp("delivered_at") - F.unix_timestamp("shipped_at"))
                    / 86400.0)
        .groupBy("carrier")
        .agg(F.count("*").alias("so_lo"),
             F.round(F.avg("so_ngay_giao"), 2).alias("so_ngay_giao_tb"),
             F.round(F.expr("percentile_approx(so_ngay_giao, 0.95)"), 2).alias("p95_ngay"),
             F.round(F.avg("so_lan_quet"), 1).alias("so_lan_quet_tb"),
             F.round(F.avg("so_tram"), 1).alias("so_tram_tb"))
        .orderBy("so_ngay_giao_tb")
    )


def top_san_pham_moi_danh_muc(sp: DataFrame, n: int = 3) -> DataFrame:
    """Dung ham cua so - phep tinh ma Spark xu ly phan tan rat tot."""
    w = Window.partitionBy("category").orderBy(F.desc("doanh_thu"))
    return (sp.withColumn("hang", F.row_number().over(w))
              .filter(F.col("hang") <= n)
              .select("category", "hang", "product_name", "shop",
                      "so_luong_ban", "doanh_thu")
              .orderBy("category", "hang"))


def gio_cao_diem(events: DataFrame) -> DataFrame:
    return (events.withColumn("gio", F.hour("timestamp"))
                  .groupBy("gio", "platform")
                  .agg(F.count("*").alias("so_su_kien"))
                  .orderBy("gio", "platform"))


# ---------------------------------------------------------------------------
def main() -> None:
    spark = build_session()
    spark.sparkContext.setLogLevel("ERROR")

    print(f">> Spark {spark.version}, che do {spark.sparkContext.master}")
    print(f">> Doc du lieu tu {RAW}\n")

    product = spark.read.parquet(f"{RAW}/dim_product.parquet")
    order_line = spark.read.parquet(f"{RAW}/fact_order_line.parquet")
    shipment = spark.read.parquet(f"{RAW}/fact_shipment.parquet")
    events = spark.read.parquet(f"{RAW}/clickstream_events")
    scans = spark.read.parquet(f"{RAW}/shipment_scans.parquet")

    for ten, df in (("dim_product", product), ("fact_order_line", order_line),
                    ("fact_shipment", shipment), ("clickstream_events", events),
                    ("shipment_scans", scans)):
        print(f"   {ten:<20} {df.count():>8,} dong, "
              f"{df.rdd.getNumPartitions()} phan vung")

    # Du lieu su kien duoc dung lai nhieu lan -> giu trong bo nho
    events.cache()

    print("\n>> Tinh toan ...")
    sp = phan_tich_san_pham(order_line, product, events).cache()

    _save(sp, "san_pham_gop_hai_nguon")
    _save(pheu_chuyen_doi(events), "pheu_chuyen_doi")
    _save(doanh_thu_theo_thang(order_line, product), "doanh_thu_theo_thang")
    _save(hieu_suat_van_chuyen(shipment, scans), "hieu_suat_van_chuyen")
    _save(top_san_pham_moi_danh_muc(sp), "top_san_pham_moi_danh_muc")
    _save(gio_cao_diem(events), "gio_cao_diem")

    _show("Pheu chuyen doi", pheu_chuyen_doi(events))
    _show("Hieu suat van chuyen", hieu_suat_van_chuyen(shipment, scans))
    _show("San pham xem nhieu nhung ban kem",
          sp.filter((F.col("product_view") > 60) & (F.col("doanh_thu") < 500_000_000))
            .orderBy(F.desc("product_view"))
            .select("product_name", "category", "product_view", "doanh_thu"))

    print(f"\n>> Ket qua da ghi vao {CURATED} va {RESULT_DIR}")
    spark.stop()


if __name__ == "__main__":
    main()
