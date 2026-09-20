# Chương 4 — Phần A: Trích xuất dữ liệu lên hệ sinh thái Hadoop

## 4A.1. Vì sao cần tầng Hadoop

Hai CSDL vận hành ở Chương 2 và 3 phục vụ **giao dịch**: đọc ghi từng bản ghi, độ
trễ thấp, luôn sẵn sàng. Chạy truy vấn phân tích quét toàn bộ bảng trực tiếp trên
chúng sẽ giành tài nguyên với luồng bán hàng — giờ cao điểm mà chạy báo cáo doanh
thu cả năm thì khách hàng chịu trận.

Kiến trúc chuẩn tách hai việc này:

```
  Tầng vận hành (OLTP)              Tầng phân tích (OLAP)
  ┌──────────────┐                  ┌─────────────────────────┐
  │  SQL Server  │ ──┐              │                         │
  └──────────────┘   │   Parquet    │   HDFS  ──►  Spark      │
                     ├────────────► │   (lưu trữ) (tính toán) │
  ┌──────────────┐   │              │                         │
  │   MongoDB    │ ──┘              └─────────────────────────┘
  └──────────────┘
```

## 4A.2. Kiến trúc Hadoop đã triển khai

| Thành phần | Vai trò | Cấu hình trong đồ án |
|---|---|---|
| **NameNode** | Giữ metadata: cây thư mục, tên file, khối nào nằm ở DataNode nào. Không giữ dữ liệu thật. | Cổng 9000 (RPC), 9870 (web UI) |
| **DataNode** | Lưu các khối dữ liệu thật trên đĩa, báo cáo định kỳ về NameNode | 1 node |
| **Spark** | Lớp tính toán, đọc dữ liệu từ HDFS và xử lý song song | Chế độ `local[*]` |

Hệ thống chạy ở **chế độ pseudo-distributed**: một máy đóng cả hai vai trò NameNode
và DataNode, nhưng các tiến trình vẫn tách biệt và giao tiếp qua RPC đúng như trong
cụm thật. Khác biệt duy nhất so với cụm sản xuất là số máy.

### Hệ số nhân bản

Cấu hình `dfs.replication = 1` vì chỉ có một DataNode. Trong cụm thật giá trị mặc
định là **3**: mỗi khối dữ liệu được lưu trên ba máy khác nhau, thường là hai máy
cùng rack và một máy khác rack. Nhờ vậy hỏng một ổ cứng hay mất một rack đều không
mất dữ liệu, và Spark có thể chọn bản sao gần nhất để đọc.

### Kích thước khối

Đặt `dfs.blocksize = 16 MB` thay vì mặc định 128 MB, vì dữ liệu của đồ án chỉ vài
chục MB — để mặc định thì mọi file đều gói gọn trong một khối và không quan sát được
cơ chế chia khối. Trong thực tế khối lớn có lợi: ít metadata cho NameNode hơn, và
mỗi tác vụ Spark xử lý được nhiều dữ liệu hơn trước khi phải đọc khối mới.

## 4A.3. Định dạng Parquet

Dữ liệu được chuyển sang **Apache Parquet** trước khi đẩy lên HDFS, thay vì CSV hay
JSON. Parquet là định dạng **lưu theo cột**:

| | CSV / JSON (theo dòng) | Parquet (theo cột) |
|---|---|---|
| Đọc 2 cột trong bảng 20 cột | Phải đọc toàn bộ file | Chỉ đọc 2 cột đó |
| Tỷ lệ nén | Thấp | Cao — các giá trị cùng cột giống nhau nên nén rất tốt |
| Kiểu dữ liệu | Mất, phải tự đoán khi đọc | Lưu kèm trong file |
| Đẩy điều kiện lọc xuống tầng lưu trữ | Không | Có (predicate pushdown) |

## 4A.4. Tổ chức dữ liệu trên HDFS

```
/ecommerce
├── raw/                          ← dữ liệu thô vừa trích xuất
│   ├── dim_product.parquet
│   ├── dim_customer.parquet
│   ├── fact_order_line.parquet
│   ├── fact_shipment.parquet
│   ├── shipment_scans.parquet
│   └── clickstream_events/       ← phân vùng theo tháng
│       ├── event_month=2025-01/
│       ├── event_month=2025-02/
│       └── ...
└── curated/                      ← kết quả sau khi Spark xử lý
    ├── san_pham_gop_hai_nguon/
    ├── pheu_chuyen_doi/
    └── ...
```

**Phân vùng (partitioning)** là kỹ thuật quan trọng nhất ở đây. Thư mục
`clickstream_events` được chia theo `event_month`. Khi Spark chạy truy vấn có điều
kiện `WHERE event_month >= '2026-01'`, nó **bỏ qua hoàn toàn** các thư mục không
thỏa mãn thay vì đọc rồi lọc — gọi là *partition pruning*. Với dữ liệu hàng tỷ dòng,
đây là khác biệt giữa vài giây và vài giờ.

### Chọn độ mịn của phân vùng

Bản cài đặt đầu tiên phân vùng theo **ngày**. Dữ liệu trải 20 tháng nên sinh ra 610
thư mục, mỗi thư mục chỉ chứa một file vài chục KB. Đây chính là **"small files
problem"** kinh điển của HDFS:

- NameNode giữ metadata của **mọi** file và khối trong RAM. Hàng triệu file nhỏ làm
  NameNode hết bộ nhớ, dù tổng dung lượng dữ liệu không lớn.
- Mỗi file dù chỉ 30 KB vẫn chiếm một khối riêng về mặt metadata.
- Spark phải mở 610 file thay vì vài file lớn, chi phí mở file lấn át chi phí đọc.

Vì vậy bản cuối chuyển sang phân vùng theo **tháng** — 20 phân vùng. Quy tắc thực tế
trong sản xuất: mỗi phân vùng nên đạt từ 128 MB trở lên, tức bằng đúng một khối HDFS.

Hai lớp `raw` và `curated` phản ánh mô hình **data lake** phổ biến: lớp thô giữ
nguyên dữ liệu gốc để có thể tính lại khi logic thay đổi; lớp tinh chứa kết quả đã
tổng hợp, sẵn sàng cho báo cáo.

## 4A.5. Quy trình chạy

```bash
./scripts/install_hadoop.sh                        # cài Hadoop 3.4.1 (một lần)
./scripts/start_hdfs.sh                            # khởi động NameNode + DataNode
uv run python -m ecommerce_bigdata.hdfs_ingest     # trích xuất → Parquet → HDFS
uv run python -m ecommerce_bigdata.spark_analytics # Spark đọc từ HDFS và phân tích
```

Giao diện web của NameNode tại `http://127.0.0.1:9870` cho phép duyệt cây thư mục
HDFS, xem số khối của từng file và tình trạng DataNode — dùng để minh họa khi demo.

## 4A.6. Kết quả chạy thực tế

Cụm HDFS đã chạy và nạp dữ liệu thành công:

| Chỉ số | Giá trị |
|---|---|
| Phiên bản Hadoop | 3.4.1 |
| Số DataNode hoạt động | 1 |
| Tổng bản ghi đã nạp | 91.315 |
| Số file trên `/ecommerce/raw` | 26 |
| Số khối (block) | 26 |
| Kích thước khối trung bình | 178 KB |
| Hệ số nhân bản | 1 |
| Dung lượng lớp `raw` | 4,4 MB |
| Dung lượng lớp `curated` | 30,6 KB |
| Trạng thái hệ thống tệp | `HEALTHY` |

Đáng chú ý: 91.315 bản ghi từ hai CSDL chỉ chiếm **4,4 MB** ở định dạng Parquet nén
Snappy. Cùng lượng dữ liệu đó xuất ra CSV sẽ lớn gấp nhiều lần — minh chứng cho hiệu
quả nén của định dạng lưu theo cột.
