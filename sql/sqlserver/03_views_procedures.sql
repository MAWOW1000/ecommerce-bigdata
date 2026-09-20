/* ============================================================================
   10 doi tuong CSDL hien thuc 10 yeu cau nghiep vu o Chuong 1 (SQL Server)
   ============================================================================ */
USE ECommerceDB;
GO

/* Khung nhin trung gian: doanh thu tung dong don, dung lai o nhieu truy van */
CREATE OR ALTER VIEW ecom.vw_DongDonMoRong AS
SELECT o.OrderID, o.CustomerID, o.OrderDate, o.Status, o.ShipProvince,
       o.PromotionID, o.DiscountAmount,
       d.VariantID, d.Quantity, d.UnitPrice,
       (d.Quantity * d.UnitPrice) AS LineRevenue,
       v.ProductID, p.SellerID, p.CategoryID, p.ProductName,
       c.CategoryName, s.ShopName
  FROM ecom.Orders o
  JOIN ecom.OrderDetail d    ON d.OrderID   = o.OrderID
  JOIN ecom.ProductVariant v ON v.VariantID = d.VariantID
  JOIN ecom.Product p        ON p.ProductID = v.ProductID
  JOIN ecom.Category c       ON c.CategoryID = p.CategoryID
  JOIN ecom.Seller s         ON s.SellerID  = p.SellerID;
GO

/* ------------------------------------------------------------------- YC01 */
CREATE OR ALTER VIEW ecom.vw_DoanhThuThangTheoDanhMuc AS
SELECT DATEFROMPARTS(YEAR(OrderDate), MONTH(OrderDate), 1) AS Thang,
       CategoryName            AS DanhMuc,
       COUNT(DISTINCT OrderID) AS SoDon,
       SUM(Quantity)           AS SoLuongBan,
       SUM(LineRevenue)        AS DoanhThu
  FROM ecom.vw_DongDonMoRong
 WHERE Status = 'Delivered'
 GROUP BY DATEFROMPARTS(YEAR(OrderDate), MONTH(OrderDate), 1), CategoryName;
GO

/* ------------------------------------------------------------------- YC02 */
CREATE OR ALTER PROCEDURE ecom.sp_TopSanPhamBanChay
    @TuNgay  DATE,
    @DenNgay DATE,
    @TopN    INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@TopN)
           ProductID, ProductName, CategoryName, ShopName,
           SUM(Quantity)    AS SoLuongBan,
           SUM(LineRevenue) AS DoanhThu
      FROM ecom.vw_DongDonMoRong
     WHERE Status = 'Delivered'
       AND OrderDate >= @TuNgay
       AND OrderDate <  DATEADD(DAY, 1, @DenNgay)
     GROUP BY ProductID, ProductName, CategoryName, ShopName
     ORDER BY SoLuongBan DESC;
END;
GO

/* ------------------------------------------------------------------- YC03 */
CREATE OR ALTER VIEW ecom.vw_PhanKhucKhachHangRFM AS
WITH base AS (
    SELECT c.CustomerID, c.FullName, c.Province,
           DATEDIFF(DAY, MAX(o.OrderDate), GETDATE()) AS Recency,
           COUNT(DISTINCT o.OrderID)                  AS Frequency,
           SUM(d.Quantity * d.UnitPrice)              AS Monetary
      FROM ecom.Customer c
      JOIN ecom.Orders o      ON o.CustomerID = c.CustomerID AND o.Status = 'Delivered'
      JOIN ecom.OrderDetail d ON d.OrderID    = o.OrderID
     GROUP BY c.CustomerID, c.FullName, c.Province
), scored AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY Recency   DESC) AS R,
           NTILE(5) OVER (ORDER BY Frequency ASC)  AS F,
           NTILE(5) OVER (ORDER BY Monetary  ASC)  AS M
      FROM base
)
SELECT CustomerID, FullName, Province, Recency, Frequency, Monetary, R, F, M,
       CASE
         WHEN R >= 4 AND F >= 4 AND M >= 4 THEN N'VIP - Champions'
         WHEN R >= 3 AND F >= 3            THEN N'Trung thanh'
         WHEN R >= 4 AND F <= 2            THEN N'Khach moi tiem nang'
         WHEN R <= 2 AND F >= 3            THEN N'Nguy co roi bo'
         ELSE                                   N'Khach thong thuong'
       END AS PhanKhuc
  FROM scored;
GO

/* ------------------------------------------------------------------- YC04 */
CREATE OR ALTER VIEW ecom.vw_TyLeHuyDonTheoVung AS
SELECT o.ShipProvince AS TinhThanh,
       COUNT(*)       AS TongDon,
       SUM(CASE WHEN o.Status = 'Cancelled' THEN 1 ELSE 0 END) AS DonHuy,
       CAST(100.0 * SUM(CASE WHEN o.Status = 'Cancelled' THEN 1 ELSE 0 END)
            / NULLIF(COUNT(*), 0) AS DECIMAL(5,2))             AS TyLeHuyPct,
       /* SQL Server khong co MODE() WITHIN GROUP -> dung truy van con */
       (SELECT TOP 1 o2.CancelReason
          FROM ecom.Orders o2
         WHERE o2.ShipProvince = o.ShipProvince AND o2.CancelReason IS NOT NULL
         GROUP BY o2.CancelReason
         ORDER BY COUNT(*) DESC)                               AS LyDoPhoBien
  FROM ecom.Orders o
 GROUP BY o.ShipProvince;
GO

/* ------------------------------------------------------------------- YC05 */
CREATE OR ALTER VIEW ecom.vw_CanhBaoTonKho AS
SELECT v.SKU, p.ProductName, c.CategoryName, s.ShopName,
       i.QuantityOnHand, i.SafetyStock,
       (i.SafetyStock - i.QuantityOnHand) AS ThieuHut,
       CASE WHEN i.QuantityOnHand = 0                     THEN N'HET HANG'
            WHEN i.QuantityOnHand < i.SafetyStock * 0.5   THEN N'NGHIEM TRONG'
            ELSE                                               N'CANH BAO'
       END AS MucDo
  FROM ecom.Inventory i
  JOIN ecom.ProductVariant v ON v.VariantID  = i.VariantID
  JOIN ecom.Product p        ON p.ProductID  = v.ProductID
  JOIN ecom.Category c       ON c.CategoryID = p.CategoryID
  JOIN ecom.Seller s         ON s.SellerID   = p.SellerID
 WHERE i.QuantityOnHand < i.SafetyStock;
GO

/* ------------------------------------------------------------------- YC06 */
CREATE OR ALTER VIEW ecom.vw_HieuSuatNguoiBan AS
SELECT s.SellerID, s.ShopName, s.Province,
       ISNULL(bh.SoDon, 0)      AS SoDonGiaoThanhCong,
       ISNULL(bh.DoanhThu, 0)   AS DoanhThu,
       ISNULL(sp.SoSanPham, 0)  AS SoSanPham,
       dg.DiemTrungBinh,
       ISNULL(dg.SoDanhGia, 0)  AS SoDanhGia,
       RANK() OVER (ORDER BY ISNULL(bh.DoanhThu, 0) DESC) AS HangDoanhThu
  FROM ecom.Seller s
  OUTER APPLY (SELECT COUNT(DISTINCT e.OrderID) AS SoDon, SUM(e.LineRevenue) AS DoanhThu
                 FROM ecom.vw_DongDonMoRong e
                WHERE e.SellerID = s.SellerID AND e.Status = 'Delivered') bh
  OUTER APPLY (SELECT COUNT(*) AS SoSanPham
                 FROM ecom.Product p WHERE p.SellerID = s.SellerID) sp
  OUTER APPLY (SELECT CAST(AVG(CAST(r.Rating AS DECIMAL(5,2))) AS DECIMAL(3,2)) AS DiemTrungBinh,
                      COUNT(*) AS SoDanhGia
                 FROM ecom.Review r
                 JOIN ecom.Product p2 ON p2.ProductID = r.ProductID
                WHERE p2.SellerID = s.SellerID) dg;
GO

/* ------------------------------------------------------------------- YC07 */
CREATE OR ALTER VIEW ecom.vw_AOVTheoThangVaKenh AS
WITH tong_don AS (
    SELECT o.OrderID,
           DATEFROMPARTS(YEAR(o.OrderDate), MONTH(o.OrderDate), 1) AS Thang,
           pay.Method AS KenhThanhToan,
           SUM(d.Quantity * d.UnitPrice) - o.DiscountAmount AS GiaTriDon
      FROM ecom.Orders o
      JOIN ecom.OrderDetail d ON d.OrderID   = o.OrderID
      JOIN ecom.Payment pay   ON pay.OrderID = o.OrderID
     WHERE o.Status = 'Delivered' AND pay.Status = 'Paid'
     GROUP BY o.OrderID, DATEFROMPARTS(YEAR(o.OrderDate), MONTH(o.OrderDate), 1),
              pay.Method, o.DiscountAmount
)
SELECT Thang, KenhThanhToan,
       COUNT(*)                            AS SoDon,
       CAST(AVG(GiaTriDon) AS DECIMAL(18,2)) AS AOV,
       CAST(SUM(GiaTriDon) AS DECIMAL(18,2)) AS TongDoanhThu
  FROM tong_don
 GROUP BY Thang, KenhThanhToan;
GO

/* ------------------------------------------------------------------- YC08 */
CREATE OR ALTER VIEW ecom.vw_HieuQuaKhuyenMai AS
SELECT pr.PromotionID, pr.PromoCode, pr.DiscountPct, pr.StartDate, pr.EndDate,
       ISNULL(ap.SoDonApDung, 0) AS SoDonApDung,
       ISNULL(ap.DoanhThuGoc, 0) AS DoanhThuGoc,
       ISNULL(ap.TongGiamGia, 0) AS TongGiamGia,
       ap.AOVCoKhuyenMai,
       (SELECT CAST(AVG(x.GiaTri) AS DECIMAL(18,2)) FROM (
            SELECT SUM(d2.Quantity * d2.UnitPrice) AS GiaTri
              FROM ecom.Orders o2
              JOIN ecom.OrderDetail d2 ON d2.OrderID = o2.OrderID
             WHERE o2.PromotionID IS NULL AND o2.Status = 'Delivered'
             GROUP BY o2.OrderID) x) AS AOVKhongKhuyenMai
  FROM ecom.Promotion pr
  OUTER APPLY (
        SELECT COUNT(*)                                  AS SoDonApDung,
               SUM(t.GiaTriDon)                          AS DoanhThuGoc,
               SUM(t.DiscountAmount)                     AS TongGiamGia,
               CAST(AVG(t.GiaTriDon) AS DECIMAL(18,2))   AS AOVCoKhuyenMai
          FROM (SELECT o.OrderID, o.DiscountAmount,
                       SUM(d.Quantity * d.UnitPrice) AS GiaTriDon
                  FROM ecom.Orders o
                  JOIN ecom.OrderDetail d ON d.OrderID = o.OrderID
                 WHERE o.PromotionID = pr.PromotionID AND o.Status = 'Delivered'
                 GROUP BY o.OrderID, o.DiscountAmount) t
  ) ap;
GO

/* ------------------------------------------------------------------- YC09 */
CREATE OR ALTER VIEW ecom.vw_ThoiGianGiaoHang AS
SELECT Carrier AS DonViVanChuyen,
       COUNT(*) AS SoLoHang,
       SUM(CASE WHEN Status = 'Delivered' THEN 1 ELSE 0 END) AS SoLoGiaoThanhCong,
       SUM(CASE WHEN Status = 'Failed'    THEN 1 ELSE 0 END) AS SoLoThatBai,
       CAST(AVG(CAST(DATEDIFF(HOUR, ShippedAt, DeliveredAt) AS DECIMAL(10,2)) / 24.0)
            AS DECIMAL(6,2)) AS SoNgayGiaoTB,
       CAST(MAX(DISTINCT p95.Val) AS DECIMAL(6,2)) AS P95_SoNgay
  FROM ecom.Shipment sh
  OUTER APPLY (
        SELECT TOP 1 PERCENTILE_CONT(0.95) WITHIN GROUP (
                 ORDER BY CAST(DATEDIFF(HOUR, s2.ShippedAt, s2.DeliveredAt)
                               AS DECIMAL(10,2)) / 24.0)
               OVER (PARTITION BY s2.Carrier) AS Val
          FROM ecom.Shipment s2
         WHERE s2.Carrier = sh.Carrier AND s2.DeliveredAt IS NOT NULL
  ) p95
 WHERE sh.ShippedAt IS NOT NULL
 GROUP BY sh.Carrier;
GO

/* ------------------------------------------------------------------- YC10 */
CREATE OR ALTER FUNCTION ecom.fn_TyLeDanhGiaThap (@NguongPct DECIMAL(5,2) = 0)
RETURNS TABLE
AS
RETURN
(
    SELECT c.CategoryName AS DanhMuc,
           COUNT(r.ReviewID) AS TongDanhGia,
           SUM(CASE WHEN r.Rating <= 2 THEN 1 ELSE 0 END) AS DanhGiaThap,
           CAST(100.0 * SUM(CASE WHEN r.Rating <= 2 THEN 1 ELSE 0 END)
                / NULLIF(COUNT(r.ReviewID), 0) AS DECIMAL(5,2)) AS TyLeThapPct,
           CAST(AVG(CAST(r.Rating AS DECIMAL(5,2))) AS DECIMAL(3,2)) AS DiemTrungBinh
      FROM ecom.Review r
      JOIN ecom.Product p  ON p.ProductID  = r.ProductID
      JOIN ecom.Category c ON c.CategoryID = p.CategoryID
     GROUP BY c.CategoryName
    HAVING CAST(100.0 * SUM(CASE WHEN r.Rating <= 2 THEN 1 ELSE 0 END)
                / NULLIF(COUNT(r.ReviewID), 0) AS DECIMAL(5,2)) >= @NguongPct
);
GO
