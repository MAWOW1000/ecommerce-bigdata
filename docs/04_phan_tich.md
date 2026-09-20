# Chương 4 — Phân tích dữ liệu lớn: biểu đồ và ý nghĩa nghiệp vụ

*Sinh tự động bởi `analytics.py` lúc 20/09/2026 09:24*

Mỗi biểu đồ dưới đây được dựng từ dữ liệu đã gộp giữa PostgreSQL (dữ liệu giao dịch) và MongoDB (dữ liệu hành vi).

## 4.1. Phễu chuyển đổi

![4.1. Phễu chuyển đổi](../assets/charts/01_funnel.png)

**Ý nghĩa nghiệp vụ:** Từ lượt xem sản phẩm đến lúc mua hàng, hệ thống mất 77.7% số phiên. Hụt lớn nhất nằm ở bước từ
'Thêm vào giỏ' (69.2%) xuống 'Bắt đầu thanh toán' (39.6%), gợi ý rằng màn hình giỏ hàng và chi
phí vận chuyển là điểm cần tối ưu trước tiên.

## 4.2. Xu hướng doanh thu theo tháng

![4.2. Xu hướng doanh thu theo tháng](../assets/charts/02_monthly_revenue.png)

**Ý nghĩa nghiệp vụ:** Doanh thu đạt đỉnh vào 08/2026 (17.4 tỷ) và thấp nhất vào 03/2026 (13.2 tỷ). Bốn danh mục dẫn
đầu là Phu kien dien tu, Quan nam, Dung cu tap luyen, Sach van hoc; kế hoạch nhập hàng nên bám
theo nhịp mùa vụ này.

## 4.3. Lượt xem so với doanh thu

![4.3. Lượt xem so với doanh thu](../assets/charts/03_view_vs_revenue.png)

**Ý nghĩa nghiệp vụ:** Hệ số tương quan giữa lượt xem và doanh thu chỉ đạt 0.45, nghĩa là nhiều người xem không bảo
đảm bán được hàng. Có 12 sản phẩm nằm trong nhóm 25% được xem nhiều nhất nhưng lại thuộc 35%
doanh thu thấp nhất — đây là nhóm cần rà soát lại giá bán, ảnh mô tả và chi phí vận chuyển.
Phát hiện này chỉ có được khi gộp dữ liệu hành vi (MongoDB) với dữ liệu giao dịch (PostgreSQL).

## 4.4. Mật độ sự kiện theo giờ

![4.4. Mật độ sự kiện theo giờ](../assets/charts/04_hourly_heatmap.png)

**Ý nghĩa nghiệp vụ:** Lưu lượng đạt đỉnh lúc 21h và thấp nhất lúc 03h. Nền tảng chiếm nhiều sự kiện nhất là android.
Khung giờ cao điểm này quyết định thời điểm chạy khuyến mãi flash sale, đồng thời là căn cứ để
đặt lịch sao lưu và bảo trì hệ thống vào khung giờ thấp điểm.

## 4.5. Hiệu suất đơn vị vận chuyển

![4.5. Hiệu suất đơn vị vận chuyển](../assets/charts/05_carrier_performance.png)

**Ý nghĩa nghiệp vụ:** GHN giao nhanh nhất (2.18 ngày), Ninja Van chậm nhất (3.85 ngày) — chênh 1.67 ngày. Số chặng
trung chuyển đi liền với thời gian giao (tương quan 0.99): hãng càng nhiều điểm quét thì đơn
càng lâu đến tay khách, gợi ý nên rút bớt chặng cho các tuyến nội thành. Nên ưu tiên GHN cho
các đơn gấp.

## 4.6. Doanh thu và lượt quan tâm theo danh mục

![4.6. Doanh thu và lượt quan tâm theo danh mục](../assets/charts/06_category_mix.png)

**Ý nghĩa nghiệp vụ:** Danh mục Phu kien dien tu dẫn đầu doanh thu. Ngược lại, Ao nam thu hút nhiều lượt xem nhất trên
mỗi tỷ doanh thu — nhiều người quan tâm nhưng giá trị đơn thấp, phù hợp để làm sản phẩm kéo
chân khách rồi bán chéo sang danh mục giá trị cao hơn.
