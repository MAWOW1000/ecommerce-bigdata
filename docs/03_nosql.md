# Chương 3 — Lưu trữ dữ liệu phi cấu trúc (NoSQL)

## 3.1. Vì sao cần NoSQL bên cạnh CSDL quan hệ

Một đơn hàng phát sinh khoảng 5–10 bản ghi quan hệ. Cũng trong phiên đó, người dùng
tạo ra hàng chục tới hàng trăm sự kiện: mở trang, tìm kiếm, xem sản phẩm, thêm giỏ,
bỏ giỏ. Nếu nhồi các sự kiện này vào bảng quan hệ:

- Transaction log phình rất nhanh, sao lưu và phục hồi trở nên chậm.
- Ghi liên tục gây tranh chấp khóa với luồng xử lý đơn hàng (OLTP).
- Schema sự kiện thay đổi liên tục theo tính năng mới; mỗi lần đổi phải `ALTER TABLE`
  trên bảng hàng trăm triệu dòng.

MongoDB giải quyết cả ba: ghi nhanh, schema linh hoạt theo từng document, và chấp
nhận nhất quán cuối (eventual consistency) — hoàn toàn phù hợp với dữ liệu phân tích.

## 3.2. Cấu trúc document

### Collection `clickstream_events`

```json
{
  "event_id": "8f14e45f-ceea-467a-9f1b-2c3d4e5f6a7b",
  "session_id": "3c9a1b2d-4e5f-6071-8293-a4b5c6d7e8f9",
  "user_id": 128,
  "event_type": "add_to_cart",
  "timestamp": { "$date": "2026-03-14T20:41:07Z" },
  "device": {
    "platform": "android",
    "os_version": "14.2",
    "app_version": "5.12.0"
  },
  "geo": { "country": "VN", "province": "Ha Noi" },
  "traffic_source": { "channel": "paid_search", "campaign": "tet2026" },
  "payload": {
    "product_id": 147,
    "variant_id": 361,
    "quantity": 2,
    "dwell_seconds": 84,
    "position_in_list": 3
  },
  "source": "live_ui"
}
```

Điểm thiết kế đáng chú ý:

- **`payload` có cấu trúc khác nhau theo `event_type`.** Sự kiện `search` chứa
  `query`, `result_count`, `filters_applied`; sự kiện `purchase` chứa `product_ids`,
  `revenue`. Đây chính là thứ CSDL quan hệ không làm được nếu không sinh ra hàng chục
  cột rỗng.
- **`user_id` có thể `null`** — khách vãng lai chưa đăng nhập, nhưng vẫn theo dõi
  được nhờ `session_id`.
- **`product_id` tham chiếu đúng khóa chính bên SQL Server**, nhờ vậy Chương 4 gộp
  được hai nguồn.
- **`source`** phân biệt dữ liệu sinh tự động (`mock`) với sự kiện thật từ giao diện
  demo (`live_ui`).

### Collection `shipment_scans`

```json
{
  "scan_id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
  "tracking_no": "TRK00004312",
  "order_id": 4312,
  "carrier": "GHN",
  "scan_type": "outbound_scan",
  "station": "Trung chuyen Bac Ninh",
  "device_id": "HH-027",
  "operator": "Nguyen Van Minh",
  "timestamp": { "$date": "2026-03-15T02:18:44Z" },
  "weight_kg": 1.85
}
```

Đây là log thiết bị quét mã vạch cầm tay tại kho và điểm trung chuyển — đúng loại dữ
liệu tần suất cao mà đề bài yêu cầu.

## 3.3. Chỉ mục

| Collection | Chỉ mục | Phục vụ truy vấn |
|---|---|---|
| clickstream_events | `(user_id, timestamp DESC)` | Lịch sử duyệt web của một khách |
| clickstream_events | `(event_type, timestamp DESC)` | Thống kê theo loại sự kiện trong khoảng thời gian |
| clickstream_events | `payload.product_id` | Gộp với dữ liệu sản phẩm bên SQL |
| clickstream_events | `session_id` | Dựng lại toàn bộ một phiên duyệt |
| shipment_scans | `(tracking_no, timestamp)` | Tra cứu hành trình một lô hàng |
| shipment_scans | `order_id` | Đối chiếu với bảng `Shipment` |

## 3.4. Kịch bản sinh dữ liệu

Script `seed_mongo.py` sinh khoảng **50.000 sự kiện clickstream** và **22.000 log quét
mã vạch**, ghi theo lô 5.000 document mỗi lần (`insert_many`) thay vì ghi từng bản ghi.

Ba chi tiết làm dữ liệu giả sát thực tế — không có chúng thì biểu đồ ở Chương 4 sẽ
phẳng và vô nghĩa:

1. **Nhịp ngày đêm.** Giờ phát sinh sự kiện theo phân phối có trọng số: thấp nhất lúc
   3–4h sáng, hai đỉnh vào giờ nghỉ trưa và 19–21h tối.
2. **Nền tảng đổi theo khung giờ.** Ban ngày nhiều `desktop_web` (người dùng ở công
   ty), buổi tối gần như chỉ còn `android`/`ios`.
3. **Độ phổ biến sản phẩm lệch.** Xác suất một sản phẩm được xem tỉ lệ với doanh số
   thực của nó nhân một nhiễu lognormal. Nhờ vậy lượt xem và doanh thu có tương quan
   thật nhưng không hoàn hảo — giống thị trường, và tạo ra nhóm "xem nhiều bán kém"
   mà Chương 4 phân tích.

Ngoài ra, ứng dụng demo web ghi sự kiện **thật** vào cùng collection này mỗi khi người
dùng thao tác trên giao diện, với cùng cấu trúc document.
