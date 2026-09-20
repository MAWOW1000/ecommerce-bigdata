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
| Giao diện | React 19 + TypeScript + Vite + Tailwind v4 + shadcn/ui |
| Biểu đồ trên web | Recharts |
| Quản lý package | [uv](https://github.com/astral-sh/uv) (Python) · pnpm (JS) |
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
├── frontend/        # Giao diện React (Vite), build ra web/static/app
├── scripts/         # Cài đặt và khởi động MongoDB / PostgreSQL / web
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

Chạy tất cả một lệnh:

```bash
./scripts/run_all.sh
```

Hoặc từng bước:

```bash
uv run python -m ecommerce_bigdata.seed_sql     # Chương 2: schema + dữ liệu quan hệ
uv run python -m ecommerce_bigdata.seed_mongo   # Chương 3: log vào MongoDB
uv run python scripts/generate_erd.py           # Chương 2: vẽ lại ERD
uv run python -m ecommerce_bigdata.analytics    # Chương 4: join + 6 biểu đồ
uv run python -m ecommerce_bigdata.report       # Sinh BaoCao_ECommerce_BigData.docx
./scripts/export_pdf.sh                         # Xuất PDF (cần LibreOffice)
```

## Ứng dụng demo

```bash
./scripts/fetch_product_images.sh   # tải ảnh minh hoạ về local (chỉ cần 1 lần)
cd frontend && pnpm install && pnpm build && cd ..
./scripts/restart_web.sh            # http://127.0.0.1:8000
```

Bản build sẵn đã nằm trong repo nên có thể bỏ qua bước `pnpm build` nếu chỉ cần chạy demo.
Khi phát triển giao diện thì chạy `pnpm dev` (port 5173, đã cấu hình proxy `/api` sang 8000).

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

## Nội dung báo cáo

| Chương | Nguồn | Sinh ra từ |
|---|---|---|
| 1. Tổng quan bài toán | `docs/01_yeu_cau_nghiep_vu.md` | Viết tay |
| 2. Thiết kế CSDL quan hệ | `docs/02_thiet_ke_csdl.md` | Viết tay + ERD sinh tự động |
| 3. NoSQL | `docs/03_nosql.md` | Viết tay |
| 4. Phân tích dữ liệu lớn | `docs/04_phan_tich.md` | **Sinh tự động** bởi `analytics.py` |

`report.py` gộp bốn file Markdown trên thành `BaoCao_ECommerce_BigData.docx`, kèm
trang bìa, mục lục tự động và số trang. Sửa thông tin sinh viên ở biến `STUDENT`
trong `src/ecommerce_bigdata/report.py` trước khi nộp.
