# Phần B: Xử lý phân tán bằng Apache Spark

## 4B.1. Vì sao dùng Spark thay vì MapReduce

MapReduce là cơ chế xử lý nguyên thủy của Hadoop. Mỗi bước Map và Reduce đều **ghi
kết quả trung gian xuống đĩa**, nên một truy vấn nhiều bước phải đọc ghi đĩa rất
nhiều lần. Spark giữ dữ liệu trung gian **trong bộ nhớ**, do đó nhanh hơn đáng kể
với các phép lặp và truy vấn nhiều tầng — đây là lý do Spark gần như thay thế hoàn
toàn MapReduce trong thực tế, dù vẫn chạy trên cùng nền HDFS.

## 4B.2. Mô hình xử lý

Spark chia dữ liệu thành **phân vùng (partition)**, mỗi phân vùng được một luồng xử
lý độc lập. Trong đồ án, Spark chạy ở chế độ `local[*]` — một tiến trình JVM, mỗi lõi
CPU đóng vai một executor. Cùng đoạn mã đó, chỉ cần đổi `--master` sang địa chỉ của
YARN hay Spark Standalone là chạy được trên cụm hàng trăm máy mà **không sửa một dòng
logic nào**. Đây chính là giá trị của mô hình lập trình phân tán.

Hai đặc điểm cần nhớ khi đọc mã nguồn `spark_analytics.py`:

- **Tính toán lười (lazy evaluation).** Các phép `filter`, `join`, `groupBy` chỉ dựng
  kế hoạch thực thi chứ chưa chạy. Spark chỉ thật sự tính khi gặp một *action* như
  `count()`, `show()` hay `write()`. Nhờ vậy nó tối ưu được toàn bộ chuỗi phép biến
  đổi trước khi chạy — ví dụ tự đẩy điều kiện lọc xuống sát tầng đọc file.
- **Bộ nhớ đệm (`cache`).** DataFrame `events` được dùng lại ở bốn phép tính khác
  nhau. Không có `cache()`, Spark sẽ đọc lại từ HDFS bốn lần. Gọi `cache()` giữ nó
  trong RAM sau lần tính đầu tiên.

## 4B.3. Các phép phân tích đã cài đặt

| Hàm | Nội dung | Kỹ thuật Spark |
|---|---|---|
| `phan_tich_san_pham` | Gộp doanh thu (PostgreSQL) với lượt xem, lượt thêm giỏ (MongoDB) trên `product_id` | `join`, `pivot`, `groupBy` |
| `pheu_chuyen_doi` | Đếm số phiên duy nhất ở từng bước của phễu | `countDistinct`, `when/otherwise` |
| `doanh_thu_theo_thang` | Doanh thu theo tháng và danh mục | `date_format`, `groupBy` nhiều khóa |
| `hieu_suat_van_chuyen` | Gộp bảng `Shipment` với log quét mã vạch trên `tracking_no` | `join`, `percentile_approx` |
| `top_san_pham_moi_danh_muc` | Ba sản phẩm doanh thu cao nhất trong mỗi danh mục | **Hàm cửa sổ** `row_number() OVER (PARTITION BY ...)` |
| `gio_cao_diem` | Phân bố sự kiện theo giờ và nền tảng | `hour()`, `groupBy` |

Phép gộp ở hàng đầu tiên là trọng tâm của đề bài: nó **đối chiếu dữ liệu danh mục từ
CSDL quan hệ với dữ liệu log từ NoSQL**, nhưng thực hiện trên HDFS bằng Spark thay vì
trong bộ nhớ một tiến trình.

## 4B.4. So sánh hai cách làm trong đồ án

Đồ án cài đặt **hai phiên bản** của cùng bài toán phân tích để so sánh:

| | `analytics.py` (pandas) | `spark_analytics.py` (Spark + HDFS) |
|---|---|---|
| Nguồn đọc | Trực tiếp PostgreSQL và MongoDB | Parquet trên HDFS |
| Nơi xử lý | Bộ nhớ của một tiến trình | Phân tán trên nhiều executor |
| Giới hạn | Dữ liệu phải vừa RAM | Chỉ giới hạn bởi dung lượng cụm |
| Đầu ra | Biểu đồ PNG cho báo cáo | Parquet ở lớp `curated` + CSV |
| Phù hợp khi | Vài chục nghìn tới vài triệu dòng | Từ hàng chục triệu dòng trở lên |

Với quy mô dữ liệu của đồ án (khoảng 72.000 bản ghi), pandas thực tế **nhanh hơn**
Spark, vì Spark mất vài giây khởi động JVM và lập kế hoạch thực thi. Điều này không
mâu thuẫn với việc chọn Spark: giá trị của nó nằm ở chỗ khi dữ liệu tăng lên hàng
trăm triệu dòng thì pandas không chạy nổi nữa, còn Spark chỉ cần thêm máy vào cụm.
Đây cũng là một kết luận nghiệp vụ đáng lưu ý — **không phải bài toán nào cũng cần
Big Data**.

## 4B.5. Kết quả chạy thực tế

Spark 3.5.3 đọc trực tiếp từ `hdfs://127.0.0.1:9000/ecommerce/raw`:

| Tập dữ liệu | Số dòng | Số phân vùng Spark |
|---|---|---|
| `dim_product` | 300 | 1 |
| `fact_order_line` | 14.319 | 1 |
| `fact_shipment` | 3.972 | 1 |
| `clickstream_events` | 50.029 | 11 |
| `shipment_scans` | 22.195 | 1 |

### Phễu chuyển đổi (tính bằng Spark)

| Bước | Số phiên | Số sự kiện | Tỷ lệ còn lại |
|---|---|---|---|
| Xem sản phẩm | 6.043 | 14.019 | 100,00% |
| Thêm vào giỏ | 4.182 | 6.468 | 69,20% |
| Bắt đầu thanh toán | 2.394 | 2.961 | 39,62% |
| Mua hàng | 1.350 | 1.520 | 22,34% |

### Hiệu suất vận chuyển — kết quả của phép gộp hai nguồn

Bảng dưới đây là **minh chứng rõ nhất cho giá trị của kiến trúc kép**: ba cột đầu đến
từ CSDL quan hệ, hai cột cuối đến từ log quét mã vạch trong MongoDB, gộp trên khóa
`tracking_no`.

| Đơn vị vận chuyển | Số lô | Số ngày giao TB | P95 (ngày) | Số lần quét TB | Số trạm TB |
|---|---|---|---|---|---|
| GHN | 719 | 2,18 | 3,58 | 3,9 | 3,1 |
| GHTK | 733 | 2,64 | 4,13 | 4,6 | 3,5 |
| J&T Express | 670 | 3,08 | 4,62 | 5,4 | 3,9 |
| Viettel Post | 712 | 3,39 | 4,72 | 6,5 | 4,4 |
| Ninja Van | 676 | 3,85 | 5,29 | 7,5 | 4,7 |

**Ý nghĩa nghiệp vụ.** Hai cột cuối tăng đều cùng chiều với số ngày giao: GHN đi qua
3,1 trạm và giao trong 2,18 ngày, trong khi Ninja Van đi qua 4,7 trạm và mất 3,85
ngày. Mỗi trạm trung chuyển cộng thêm khoảng nửa ngày. Kết luận cho vận hành: với
đơn nội thành cần gấp nên ưu tiên hãng có mạng lưới tuyến thẳng; còn muốn cải thiện
hãng đang chậm thì phải giảm số chặng chứ không phải giục tài xế.

Không nguồn dữ liệu nào một mình cho ra kết luận này — CSDL quan hệ biết đơn giao mất
bao lâu nhưng không biết vì sao, còn log quét mã vạch biết đường đi nhưng không biết
kết quả kinh doanh.
