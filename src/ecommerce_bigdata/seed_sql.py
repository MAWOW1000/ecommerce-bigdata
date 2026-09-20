"""Sinh du lieu gia lap cho CSDL quan he (Chuong 2).

Chay:  uv run python -m ecommerce_bigdata.seed_sql
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal

import psycopg
from faker import Faker

from .config import PG, SEED, SQL_DIR

fake = Faker("vi_VN")

PROVINCES = [
    "Ha Noi", "TP Ho Chi Minh", "Da Nang", "Hai Phong", "Can Tho",
    "Binh Duong", "Dong Nai", "Khanh Hoa", "Nghe An", "Thanh Hoa",
    "Lam Dong", "Quang Ninh",
]

CARRIERS = ["GHTK", "GHN", "Viettel Post", "J&T Express", "Ninja Van"]

CANCEL_REASONS = [
    "Khach doi y", "Het hang", "Sai dia chi", "Khong lien lac duoc",
    "Thanh toan that bai", "Giao hang tre",
]

# Danh muc cha -> danh muc con
CATEGORY_TREE: dict[str, list[str]] = {
    "Dien tu":      ["Dien thoai", "May tinh bang", "Laptop", "Phu kien dien tu"],
    "Thoi trang":   ["Ao nam", "Ao nu", "Quan nam", "Quan nu", "Giay dep"],
    "Gia dung":     ["Nha bep", "Do dung phong tam", "Noi that nho"],
    "Sach":         ["Sach van hoc", "Sach ky nang", "Sach thieu nhi"],
    "Lam dep":      ["Cham soc da", "Trang diem", "Nuoc hoa"],
    "The thao":     ["Dung cu tap luyen", "Trang phuc the thao"],
}

# Tu vung dat ten san pham theo tung danh muc con, de du lieu demo doc duoc
# thay vi chuoi ngau nhien vo nghia.
PRODUCT_VOCAB: dict[str, tuple[list[str], list[str]]] = {
    "Dien thoai":          (["iPhone", "Galaxy", "Xiaomi", "OPPO", "vivo", "realme"],
                            ["15 Pro", "S24 Ultra", "Note 13", "Reno 11", "V30", "12 Pro"]),
    "May tinh bang":       (["iPad", "Galaxy Tab", "Xiaomi Pad", "Lenovo Tab"],
                            ["Air M2", "S9 FE", "6 Pro", "P12 Pro"]),
    "Laptop":              (["MacBook", "ThinkPad", "Vivobook", "Nitro", "Inspiron"],
                            ["Air M3", "X1 Carbon", "S15 OLED", "V16 RTX4060", "15 3520"]),
    "Phu kien dien tu":    (["Tai nghe", "Sac nhanh", "Cap sac", "Chuot khong day", "Ban phim co"],
                            ["Bluetooth 5.3", "GaN 65W", "USB-C 2m", "Silent 2.4G", "RGB hot-swap"]),
    "Ao nam":              (["Ao thun nam", "Ao so mi nam", "Ao polo nam", "Ao khoac nam"],
                            ["cotton co tron", "tay dai cong so", "pique co be", "gio 2 lop"]),
    "Ao nu":               (["Ao kieu nu", "Ao so mi nu", "Ao len nu", "Ao croptop"],
                            ["tay phong", "lua cao cap", "long cuu", "tron basic"]),
    "Quan nam":            (["Quan jean nam", "Quan kaki nam", "Quan short nam", "Quan tay nam"],
                            ["slim fit", "ong suong", "the thao", "cong so"]),
    "Quan nu":             (["Quan jean nu", "Quan legging", "Chan vay", "Quan culottes"],
                            ["lung cao", "co gian 4 chieu", "xep ly", "vai linen"]),
    "Giay dep":            (["Giay the thao", "Giay luoi", "Dep quai ngang", "Sandal"],
                            ["de em chong truot", "da lon", "chong nuoc", "quai duc"]),
    "Nha bep":             (["Noi chien khong dau", "Bo dao", "Chao chong dinh", "May xay sinh to"],
                            ["5.5L", "inox 6 mon", "28cm granite", "1.5L 3 coi"]),
    "Do dung phong tam":   (["Ke nha tam", "Khan tam", "May say toc", "Voi sen tang ap"],
                            ["inox 304", "cotton 100%", "ion am 1800W", "3 che do"]),
    "Noi that nho":        (["Ke sach", "Ban lam viec", "Ghe cong thai hoc", "Den ban"],
                            ["5 tang go MDF", "120cm chan sat", "luoi tua dau", "LED chong can"]),
    "Sach van hoc":        (["Tieu thuyet", "Tap truyen ngan", "Tho", "Tan van"],
                            ["ban dac biet", "bia cung", "tai ban 2025", "song ngu"]),
    "Sach ky nang":        (["Sach ky nang", "Sach quan tri", "Sach tai chinh", "Sach giao tiep"],
                            ["tu duy phan bien", "lanh dao nhom", "dau tu ca nhan", "thuyet trinh"]),
    "Sach thieu nhi":      (["Truyen tranh", "Sach to mau", "Truyen co tich", "Sach khoa hoc nhi"],
                            ["tron bo 5 tap", "kho lon A4", "minh hoa mau", "thi nghiem vui"]),
    "Cham soc da":         (["Sua rua mat", "Kem chong nang", "Serum", "Mat na giay"],
                            ["dju nhe pH5.5", "SPF50+ PA++++", "vitamin C 10%", "hop 10 mieng"]),
    "Trang diem":          (["Son li", "Kem nen", "Phan phu", "Mascara"],
                            ["ben mau 12h", "che khuyet diem", "kiem dau", "chong troi"]),
    "Nuoc hoa":            (["Nuoc hoa nam", "Nuoc hoa nu", "Xit thom co the"],
                            ["EDP 50ml", "EDT 100ml", "huong go", "huong hoa co"]),
    "Dung cu tap luyen":   (["Ta tay", "Tham yoga", "Day khang luc", "May chay bo"],
                            ["cap 5kg", "TPE 8mm", "bo 5 muc", "gap gon"]),
    "Trang phuc the thao": (["Ao thun the thao", "Quan short chay bo", "Bo do gym", "Ao khoac gio"],
                            ["thoat mo hoi", "2 lop tui khoa", "co gian 4 chieu", "chong tia UV"]),
}

BRAND_SUFFIX = ["Pro", "Plus", "Lite", "Max", "2025", "Premium", "Classic", ""]

COLORS = ["Den", "Trang", "Xanh", "Do", "Xam", "Be", None]
SIZES = ["S", "M", "L", "XL", "Free", None]

# Phan phoi trang thai don hang, mo phong thuc te
STATUS_WEIGHTS = {
    "Delivered": 0.68,
    "Shipping":  0.09,
    "Confirmed": 0.06,
    "Pending":   0.04,
    "Cancelled": 0.10,
    "Returned":  0.03,
}

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 9, 1)


def _run_sql_file(conn: psycopg.Connection, filename: str) -> None:
    path = SQL_DIR / "postgres" / filename
    print(f">> Thuc thi {path.name} ...")
    conn.execute(path.read_text(encoding="utf-8"))


def _random_datetime() -> datetime:
    delta = END_DATE - START_DATE
    return START_DATE + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def seed() -> dict[str, int]:
    random.seed(SEED.random_seed)
    Faker.seed(SEED.random_seed)

    with psycopg.connect(PG.dsn, autocommit=False) as conn:
        _run_sql_file(conn, "01_schema.sql")
        _run_sql_file(conn, "02_triggers.sql")
        conn.commit()

        cur = conn.cursor()
        cur.execute("SET search_path TO ecom, public")

        # ---------------------------------------------------------- Danh muc
        print(">> Sinh danh muc ...")
        category_ids: list[int] = []
        category_names: dict[int, str] = {}
        for parent, children in CATEGORY_TREE.items():
            cur.execute(
                "INSERT INTO Category (CategoryName, ParentID) VALUES (%s, NULL) "
                "RETURNING CategoryID",
                (parent,),
            )
            parent_id = cur.fetchone()[0]
            for child in children:
                cur.execute(
                    "INSERT INTO Category (CategoryName, ParentID) VALUES (%s, %s) "
                    "RETURNING CategoryID",
                    (child, parent_id),
                )
                child_id = cur.fetchone()[0]
                category_ids.append(child_id)
                category_names[child_id] = child

        # ---------------------------------------------------------- Nguoi ban
        print(f">> Sinh {SEED.sellers} nguoi ban ...")
        seller_ids: list[int] = []
        seen_shops: set[str] = set()
        while len(seller_ids) < SEED.sellers:
            shop = f"{fake.company()} Store"
            if shop in seen_shops:
                continue
            seen_shops.add(shop)
            cur.execute(
                "INSERT INTO Seller (ShopName, ContactEmail, Province, JoinedAt) "
                "VALUES (%s, %s, %s, %s) RETURNING SellerID",
                (
                    shop,
                    f"shop{len(seller_ids)}@{fake.free_email_domain()}",
                    random.choice(PROVINCES),
                    _random_datetime(),
                ),
            )
            seller_ids.append(cur.fetchone()[0])

        # ---------------------------------------------------------- Khach hang
        print(f">> Sinh {SEED.customers} khach hang ...")
        customer_ids: list[int] = []
        for i in range(SEED.customers):
            cur.execute(
                "INSERT INTO Customer (FullName, Email, Phone, Province, Address, RegisteredAt) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING CustomerID",
                (
                    fake.name(),
                    f"kh{i:05d}@{fake.free_email_domain()}",
                    fake.phone_number()[:20],
                    random.choice(PROVINCES),
                    fake.address().replace("\n", ", ")[:300],
                    _random_datetime(),
                ),
            )
            customer_ids.append(cur.fetchone()[0])

        # ---------------------------------------------------------- San pham + bien the
        print(f">> Sinh {SEED.products} san pham va cac bien the ...")
        variant_pool: list[tuple[int, Decimal]] = []   # (VariantID, gia ban)
        for i in range(SEED.products):
            base_price = Decimal(random.randrange(50_000, 25_000_000, 10_000))
            cat_id = random.choice(category_ids)
            cat_name = category_names[cat_id]
            nouns, specs = PRODUCT_VOCAB.get(cat_name, (["San pham"], ["tieu chuan"]))
            suffix = random.choice(BRAND_SUFFIX)
            product_name = " ".join(filter(None, [
                random.choice(nouns), random.choice(specs), suffix,
            ]))

            cur.execute(
                "INSERT INTO Product (SellerID, CategoryID, ProductName, Description, "
                "BasePrice, IsApproved, CreatedAt) VALUES (%s,%s,%s,%s,%s,%s,%s) "
                "RETURNING ProductID",
                (
                    random.choice(seller_ids),
                    cat_id,
                    product_name,
                    fake.sentence(nb_words=12),
                    base_price,
                    random.random() < 0.92,
                    _random_datetime(),
                ),
            )
            product_id = cur.fetchone()[0]

            combos = random.sample(
                [(c, s) for c in COLORS for s in SIZES],
                k=random.randint(1, 4),
            )
            for color, size in combos:
                adjust = Decimal(random.randrange(0, 500_000, 10_000))
                cur.execute(
                    "INSERT INTO ProductVariant (ProductID, SKU, Color, Size, PriceAdjust) "
                    "VALUES (%s,%s,%s,%s,%s) RETURNING VariantID",
                    (product_id, f"SKU-{product_id:05d}-{len(variant_pool):06d}",
                     color, size, adjust),
                )
                variant_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO Inventory (VariantID, QuantityOnHand, SafetyStock) "
                    "VALUES (%s,%s,%s)",
                    (variant_id, random.randint(0, 800), random.choice([10, 20, 50])),
                )
                variant_pool.append((variant_id, base_price + adjust))

        # ---------------------------------------------------------- Khuyen mai
        print(">> Sinh chuong trinh khuyen mai ...")
        promo_ids: list[int] = []
        for i in range(12):
            start = START_DATE + timedelta(days=random.randint(0, 550))
            cur.execute(
                "INSERT INTO Promotion (PromoCode, DiscountPct, MaxDiscount, StartDate, EndDate) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING PromotionID",
                (
                    f"SALE{i:02d}{random.choice('ABCXYZ')}",
                    Decimal(random.choice([5, 10, 15, 20, 30, 50])),
                    Decimal(random.choice([50_000, 100_000, 200_000, 500_000])),
                    start.date(),
                    (start + timedelta(days=random.randint(7, 45))).date(),
                ),
            )
            promo_ids.append(cur.fetchone()[0])

        conn.commit()

        # ---------------------------------------------------------- Don hang
        print(f">> Sinh {SEED.orders} don hang (kem dong don, thanh toan, van chuyen) ...")
        statuses = list(STATUS_WEIGHTS)
        weights = list(STATUS_WEIGHTS.values())
        delivered_orders: list[tuple[int, int, list[int]]] = []  # (order, customer, [product])
        skipped_lines = 0

        for n in range(SEED.orders):
            status = random.choices(statuses, weights=weights, k=1)[0]
            order_date = _random_datetime()
            customer_id = random.choice(customer_ids)
            promo_id = random.choice(promo_ids) if random.random() < 0.28 else None

            cur.execute(
                "INSERT INTO Orders (CustomerID, PromotionID, OrderDate, Status, "
                "ShipProvince, CancelReason, DiscountAmount) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING OrderID",
                (
                    customer_id, promo_id, order_date, status,
                    random.choice(PROVINCES),
                    random.choice(CANCEL_REASONS) if status == "Cancelled" else None,
                    Decimal(0),
                ),
            )
            order_id = cur.fetchone()[0]

            # --- Dong don hang. Trigger se tru ton kho va co the bao loi het hang.
            order_total = Decimal(0)
            chosen = random.sample(variant_pool, k=random.randint(1, 5))
            product_ids: list[int] = []
            for variant_id, unit_price in chosen:
                qty = random.randint(1, 4)
                try:
                    with conn.transaction():
                        cur.execute(
                            "INSERT INTO OrderDetail (OrderID, VariantID, Quantity, UnitPrice) "
                            "VALUES (%s,%s,%s,%s)",
                            (order_id, variant_id, qty, unit_price),
                        )
                except psycopg.errors.RaiseException:
                    skipped_lines += 1          # het ton kho -> bo qua dong nay
                    continue
                order_total += unit_price * qty
                cur.execute(
                    "SELECT ProductID FROM ProductVariant WHERE VariantID = %s", (variant_id,)
                )
                product_ids.append(cur.fetchone()[0])

            if order_total == 0:                 # khong dong nao thanh cong
                cur.execute("DELETE FROM Orders WHERE OrderID = %s", (order_id,))
                continue

            # --- Giam gia
            discount = Decimal(0)
            if promo_id is not None:
                cur.execute(
                    "SELECT DiscountPct, MaxDiscount FROM Promotion WHERE PromotionID = %s",
                    (promo_id,),
                )
                pct, cap = cur.fetchone()
                discount = min(order_total * pct / 100, cap).quantize(Decimal("0.01"))
                cur.execute(
                    "UPDATE Orders SET DiscountAmount = %s WHERE OrderID = %s",
                    (discount, order_id),
                )

            # --- Thanh toan
            pay_status = {
                "Delivered": "Paid", "Shipping": "Paid", "Confirmed": "Paid",
                "Pending": "Pending", "Cancelled": random.choice(["Failed", "Refunded"]),
                "Returned": "Refunded",
            }[status]
            paid_at = order_date + timedelta(minutes=random.randint(1, 120)) \
                if pay_status == "Paid" else None
            cur.execute(
                "INSERT INTO Payment (OrderID, Method, Status, Amount, PaidAt) "
                "VALUES (%s,%s,%s,%s,%s)",
                (
                    order_id,
                    random.choices(["COD", "CreditCard", "EWallet", "BankTransfer"],
                                   weights=[0.45, 0.18, 0.28, 0.09], k=1)[0],
                    pay_status,
                    order_total - discount,
                    paid_at,
                ),
            )

            # --- Van chuyen
            if status in ("Shipping", "Delivered", "Returned"):
                shipped_at = order_date + timedelta(hours=random.randint(4, 72))
                carrier = random.choice(CARRIERS)
                # Moi hang co toc do giao khac nhau -> YC09 co y nghia
                lead_days = {"GHTK": 2.6, "GHN": 2.1, "Viettel Post": 3.4,
                             "J&T Express": 3.0, "Ninja Van": 3.9}[carrier]
                delivered_at = (
                    shipped_at + timedelta(days=random.gauss(lead_days, 0.9))
                    if status in ("Delivered", "Returned") else None
                )
                if delivered_at is not None and delivered_at < shipped_at:
                    delivered_at = shipped_at + timedelta(hours=6)
                cur.execute(
                    "INSERT INTO Shipment (OrderID, Carrier, TrackingNo, Status, "
                    "ShippedAt, DeliveredAt) VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        order_id, carrier, f"TRK{order_id:08d}",
                        "Delivered" if status == "Delivered" else
                        ("InTransit" if status == "Shipping" else "Failed"),
                        shipped_at, delivered_at,
                    ),
                )

            if status == "Delivered":
                delivered_orders.append((order_id, customer_id, product_ids))

            if (n + 1) % 1000 == 0:
                conn.commit()
                print(f"   ... {n + 1}/{SEED.orders} don")

        conn.commit()

        # ---------------------------------------------------------- Danh gia
        print(">> Sinh danh gia (chi tren don da giao) ...")
        review_count = 0
        for order_id, customer_id, product_ids in delivered_orders:
            if random.random() > 0.42:            # ~42% don co danh gia
                continue
            for product_id in set(product_ids):
                rating = random.choices([1, 2, 3, 4, 5],
                                        weights=[0.05, 0.08, 0.15, 0.32, 0.40], k=1)[0]
                try:
                    with conn.transaction():
                        cur.execute(
                            "INSERT INTO Review (ProductID, CustomerID, OrderID, Rating, Comment) "
                            "VALUES (%s,%s,%s,%s,%s)",
                            (product_id, customer_id, order_id, rating,
                             fake.sentence(nb_words=10)),
                        )
                    review_count += 1
                except psycopg.errors.Error:
                    continue
        conn.commit()

        _run_sql_file(conn, "03_views_procedures.sql")
        conn.commit()

        stats = {}
        for table in ("Category", "Seller", "Customer", "Product", "ProductVariant",
                      "Inventory", "Promotion", "Orders", "OrderDetail",
                      "Payment", "Shipment", "Review"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cur.fetchone()[0]

    print(f">> Bo qua {skipped_lines} dong don do het ton kho (dung nhu thiet ke).")
    return stats


if __name__ == "__main__":
    result = seed()
    print("\n=== SO BAN GHI DA SINH ===")
    for name, count in result.items():
        print(f"{name:<16} {count:>8,}")
