# E-Commerce Analytics — Kiến trúc dữ liệu kép (SQL + NoSQL)

Đồ án môn **Cơ sở dữ liệu & Big Data** (Master 2026). Mô phỏng một sàn thương mại
điện tử đa người bán với **kiến trúc polyglot persistence**:

- **Dữ liệu giao dịch** (đơn hàng, tồn kho, thanh toán) → CSDL quan hệ, ràng buộc ACID chặt.
- **Dữ liệu hành vi/log** (clickstream, quét mã vạch) → MongoDB, ghi tần suất cao.
- **Phân tích** → Python join hai nguồn, dựng biểu đồ xu hướng.

> **Lưu ý về SQL Server:** đề bài yêu cầu SQL Server. Repo cung cấp cả hai bản DDL —
> `sql/sqlserver/` (T-SQL, bản nộp) và `sql/postgres/` (chạy thật trên Linux để kiểm chứng
> logic truy vấn). Hai bản tương đương về lược đồ và kết quả.

## Công nghệ

| Lớp | Công nghệ |
|---|---|
| CSDL quan hệ | SQL Server 2022 (bản nộp) / PostgreSQL 17 (bản chạy thử) |
| NoSQL | MongoDB 8.0 (cài native, không Docker) |
| Ngôn ngữ | Python 3.13 |
| Quản lý package | [uv](https://github.com/astral-sh/uv) |
| Thư viện | `psycopg`, `pymongo`, `faker`, `pandas`, `matplotlib`, `python-docx` |

## Cấu trúc

```
├── docs/            # Nội dung từng chương của báo cáo
├── sql/postgres/    # DDL, trigger, 10 view/procedure (bản chạy thử)
├── sql/sqlserver/   # DDL T-SQL tương đương (bản nộp)
├── src/ecommerce_bigdata/
│   ├── config.py      # Cấu hình kết nối, đọc từ .env
│   ├── seed_sql.py    # Sinh dữ liệu giả lập cho CSDL quan hệ
│   ├── seed_mongo.py  # Sinh clickstream + log quét mã vạch
│   └── analytics.py   # Join SQL ↔ MongoDB, vẽ biểu đồ
├── scripts/         # Cài đặt và khởi động MongoDB / PostgreSQL
└── assets/          # ERD và biểu đồ xuất ra
```

## Cài đặt

```bash
# 1. Dependencies
uv sync

# 2. MongoDB (native, không cần sudo)
./scripts/install_mongodb.sh
./scripts/start_mongodb.sh

# 3. PostgreSQL (cần sudo để tạo role/database)
./scripts/setup_postgres.sh

# 4. Cấu hình
cp .env.example .env
```

## Chạy pipeline

```bash
uv run python -m ecommerce_bigdata.seed_sql     # Chương 2: schema + dữ liệu quan hệ
uv run python -m ecommerce_bigdata.seed_mongo   # Chương 3: log vào MongoDB
uv run python -m ecommerce_bigdata.analytics    # Chương 4: join + biểu đồ
```

## Ứng dụng demo

```bash
./scripts/restart_web.sh        # http://127.0.0.1:8000
```

Hai trang:

- **`/` Storefront** — sản phẩm đọc từ PostgreSQL. Mọi thao tác (xem, tìm, thêm giỏ,
  bỏ giỏ, checkout) bắn một event vào MongoDB và hiện ngay trên panel *Event Stream*.
  Đặt hàng tạo đơn thật, kích hoạt trigger trừ tồn kho; đặt quá số lượng tồn thì
  trigger chặn và toàn bộ transaction rollback — thông báo lỗi hiện nguyên văn trên UI.
- **`/dashboard`** — chạy trực tiếp 10 view/procedure nghiệp vụ, cộng phễu chuyển đổi
  tính bằng MongoDB aggregation pipeline.

Event sinh từ UI có thêm trường `source: "live_ui"` để phân biệt với dữ liệu mock,
nhưng cùng cấu trúc document nên nằm chung một không gian phân tích.

## Mười yêu cầu nghiệp vụ

Chi tiết tại [`docs/01_yeu_cau_nghiep_vu.md`](docs/01_yeu_cau_nghiep_vu.md). Tóm tắt:
doanh thu theo tháng/danh mục, top sản phẩm bán chạy, phân khúc khách hàng RFM,
tỷ lệ hủy đơn theo vùng, cảnh báo tồn kho, hiệu suất người bán, AOV theo kênh thanh toán,
hiệu quả khuyến mãi, thời gian giao hàng theo hãng, tỷ lệ đánh giá thấp theo danh mục.
