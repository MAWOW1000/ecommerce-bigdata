# Chương 1 — Tổng quan bài toán

## 1.1. Mô tả đề tài

Hệ thống **sàn thương mại điện tử đa người bán (multi-vendor marketplace)** — mô hình
tương tự Shopee/Lazada, nơi nhiều Người bán (Seller) đăng bán sản phẩm trên cùng một
nền tảng, Khách hàng (Customer) duyệt, đặt hàng, thanh toán và đánh giá.

Bài toán đặt ra **kiến trúc dữ liệu kép (polyglot persistence)**:

| Loại dữ liệu | Đặc điểm | Công nghệ |
|---|---|---|
| Dữ liệu giao dịch | Có cấu trúc, đòi hỏi ACID, ràng buộc toàn vẹn chặt (tiền, tồn kho) | CSDL quan hệ — SQL Server |
| Dữ liệu hành vi/log | Phi cấu trúc, schema biến động, ghi với tần suất rất cao, chấp nhận eventual consistency | NoSQL document — MongoDB |

Lý do tách: một đơn hàng phát sinh vài chục bản ghi quan hệ, nhưng cùng phiên đó
người dùng tạo ra hàng trăm sự kiện click/view/search. Nhồi log vào bảng quan hệ sẽ
làm phình transaction log, khóa bảng và phá vỡ hiệu năng OLTP.

## 1.2. Các quy trình nghiệp vụ thực tế

### QT1 — Quản lý danh mục và sản phẩm
Người bán đăng ký gian hàng → tạo sản phẩm thuộc một Danh mục (cấu trúc cây, danh mục
cha–con) → mỗi sản phẩm có nhiều Biến thể (ProductVariant: màu/size) với SKU riêng →
mỗi biến thể có bản ghi Tồn kho riêng. Sản phẩm phải được duyệt trước khi hiển thị.

### QT2 — Đặt hàng
Khách chọn biến thể → hệ thống **kiểm tra tồn kho khả dụng** → tạo Đơn hàng (Order) với
nhiều Dòng đơn (OrderDetail) → áp dụng Khuyến mãi nếu hợp lệ → **trừ tồn kho trong cùng
một transaction**. Giá bán được *sao chép* vào OrderDetail (snapshot) chứ không tham
chiếu giá hiện tại của sản phẩm, để hóa đơn cũ không bị đổi giá khi sản phẩm tăng giá.

### QT3 — Thanh toán
Đơn hàng sinh bản ghi Payment với phương thức (COD / thẻ / ví điện tử). Trạng thái
chuyển `Pending → Paid → Refunded`. Thanh toán thất bại → đơn về `Cancelled` và
**hoàn trả tồn kho**.

### QT4 — Vận chuyển
Đơn đã thanh toán sinh Shipment, gán đơn vị vận chuyển, sinh mã vận đơn. Trạng thái
đi qua `Preparing → Picked → InTransit → Delivered / Failed`. Mỗi lần quét mã vạch tại
kho/điểm trung chuyển sinh **một log sự kiện đẩy sang MongoDB** (tần suất rất cao).

### QT5 — Đánh giá và hoàn trả
Chỉ khách đã có đơn ở trạng thái `Delivered` mới được đánh giá sản phẩm đó (ràng buộc
nghiệp vụ). Điểm 1–5 sao. Đánh giá ≤ 2 sao kích hoạt quy trình chăm sóc khách hàng.

### QT6 — Theo dõi hành vi (ghi vào MongoDB)
Mọi thao tác của khách trên web/app sinh sự kiện clickstream: `page_view`, `search`,
`product_view`, `add_to_cart`, `remove_from_cart`, `checkout_start`, `purchase`.
Dữ liệu này dùng dựng phễu chuyển đổi và phân tích xu hướng ở Chương 4.

## 1.3. Mười (10) yêu cầu nghiệp vụ cần truy vấn

Mỗi yêu cầu dưới đây được hiện thực bằng một VIEW / FUNCTION / STORED PROCEDURE ở
Chương 2, và được đối chiếu lại với dữ liệu MongoDB ở Chương 4.

| # | Yêu cầu nghiệp vụ | Câu hỏi quản trị trả lời | Đối tượng CSDL |
|---|---|---|---|
| YC01 | Doanh thu theo tháng và theo danh mục | Danh mục nào đang tăng trưởng, mùa nào bán tốt? | `VIEW vw_DoanhThuThangTheoDanhMuc` |
| YC02 | Top 10 sản phẩm bán chạy trong khoảng thời gian | Nên nhập thêm hàng gì? | `PROCEDURE sp_TopSanPhamBanChay` |
| YC03 | Phân khúc khách hàng theo RFM | Ai là khách VIP cần giữ chân, ai sắp rời bỏ? | `VIEW vw_PhanKhucKhachHangRFM` |
| YC04 | Tỷ lệ hủy đơn theo tỉnh/thành và theo lý do | Vùng nào giao hàng kém, vì sao? | `VIEW vw_TyLeHuyDonTheoVung` |
| YC05 | Cảnh báo tồn kho dưới ngưỡng an toàn | Sản phẩm nào sắp hết hàng? | `VIEW vw_CanhBaoTonKho` |
| YC06 | Bảng xếp hạng hiệu suất người bán | Người bán nào đáng được ưu tiên hiển thị? | `VIEW vw_HieuSuatNguoiBan` |
| YC07 | Giá trị đơn hàng trung bình (AOV) theo tháng và kênh thanh toán | Phương thức thanh toán nào cho đơn giá trị cao? | `VIEW vw_AOVTheoThangVaKenh` |
| YC08 | Hiệu quả chương trình khuyến mãi | Mã giảm giá có thực sự tăng doanh thu hay chỉ giảm biên lợi nhuận? | `VIEW vw_HieuQuaKhuyenMai` |
| YC09 | Thời gian giao hàng trung bình theo đơn vị vận chuyển | Hãng vận chuyển nào chậm nhất? | `VIEW vw_ThoiGianGiaoHang` |
| YC10 | Tỷ lệ đánh giá thấp (≤ 2 sao) theo danh mục và người bán | Danh mục nào đang làm hỏng trải nghiệm? | `FUNCTION fn_TyLeDanhGiaThap` |
