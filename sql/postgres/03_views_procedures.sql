-- ============================================================================
--  10 doi tuong CSDL hien thuc 10 yeu cau nghiep vu o Chuong 1
-- ============================================================================
SET search_path TO ecom, public;

-- Bang trung gian: doanh thu tung dong don (dung lai nhieu lan)
CREATE OR REPLACE VIEW vw_DongDonMoRong AS
SELECT o.OrderID, o.CustomerID, o.OrderDate, o.Status, o.ShipProvince,
       o.PromotionID, o.DiscountAmount,
       d.VariantID, d.Quantity, d.UnitPrice,
       (d.Quantity * d.UnitPrice)            AS LineRevenue,
       v.ProductID, p.SellerID, p.CategoryID, p.ProductName,
       c.CategoryName, s.ShopName
  FROM Orders o
  JOIN OrderDetail d     ON d.OrderID   = o.OrderID
  JOIN ProductVariant v  ON v.VariantID = d.VariantID
  JOIN Product p         ON p.ProductID = v.ProductID
  JOIN Category c        ON c.CategoryID = p.CategoryID
  JOIN Seller s          ON s.SellerID  = p.SellerID;

-- ---------------------------------------------------------------- YC01
-- Doanh thu theo thang va theo danh muc (chi tinh don da giao thanh cong)
CREATE OR REPLACE VIEW vw_DoanhThuThangTheoDanhMuc AS
SELECT DATE_TRUNC('month', OrderDate)::date AS Thang,
       CategoryName                          AS DanhMuc,
       COUNT(DISTINCT OrderID)               AS SoDon,
       SUM(Quantity)                         AS SoLuongBan,
       SUM(LineRevenue)                      AS DoanhThu
  FROM vw_DongDonMoRong
 WHERE Status = 'Delivered'
 GROUP BY 1, 2
 ORDER BY 1, 5 DESC;

-- ---------------------------------------------------------------- YC02
-- Top N san pham ban chay trong khoang thoi gian tuy chon
CREATE OR REPLACE PROCEDURE sp_TopSanPhamBanChay(
    p_tu_ngay  DATE,
    p_den_ngay DATE,
    p_top_n    INTEGER DEFAULT 10
) LANGUAGE plpgsql AS $$
BEGIN
    DROP TABLE IF EXISTS tmp_top_san_pham;
    CREATE TEMP TABLE tmp_top_san_pham AS
    SELECT ProductID, ProductName, CategoryName, ShopName,
           SUM(Quantity)    AS SoLuongBan,
           SUM(LineRevenue) AS DoanhThu
      FROM vw_DongDonMoRong
     WHERE Status = 'Delivered'
       AND OrderDate >= p_tu_ngay
       AND OrderDate <  p_den_ngay + INTERVAL '1 day'
     GROUP BY ProductID, ProductName, CategoryName, ShopName
     ORDER BY SoLuongBan DESC
     LIMIT p_top_n;
END;
$$;

-- ---------------------------------------------------------------- YC03
-- Phan khuc khach hang theo mo hinh RFM (Recency - Frequency - Monetary)
CREATE OR REPLACE VIEW vw_PhanKhucKhachHangRFM AS
WITH base AS (
    SELECT c.CustomerID, c.FullName, c.Province,
           (CURRENT_DATE - MAX(o.OrderDate)::date) AS Recency,
           COUNT(DISTINCT o.OrderID)               AS Frequency,
           COALESCE(SUM(d.Quantity * d.UnitPrice), 0) AS Monetary
      FROM Customer c
      JOIN Orders o      ON o.CustomerID = c.CustomerID AND o.Status = 'Delivered'
      JOIN OrderDetail d ON d.OrderID    = o.OrderID
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
         WHEN R >= 4 AND F >= 4 AND M >= 4 THEN 'VIP - Champions'
         WHEN R >= 3 AND F >= 3            THEN 'Trung thanh'
         WHEN R >= 4 AND F <= 2            THEN 'Khach moi tiem nang'
         WHEN R <= 2 AND F >= 3            THEN 'Nguy co roi bo'
         ELSE                                   'Khach thong thuong'
       END AS PhanKhuc
  FROM scored;

-- ---------------------------------------------------------------- YC04
-- Ty le huy don theo tinh/thanh va theo ly do
CREATE OR REPLACE VIEW vw_TyLeHuyDonTheoVung AS
SELECT ShipProvince                                          AS TinhThanh,
       COUNT(*)                                              AS TongDon,
       COUNT(*) FILTER (WHERE Status = 'Cancelled')          AS DonHuy,
       ROUND(100.0 * COUNT(*) FILTER (WHERE Status = 'Cancelled') / NULLIF(COUNT(*), 0), 2)
                                                             AS TyLeHuyPct,
       MODE() WITHIN GROUP (ORDER BY CancelReason)           AS LyDoPhoBien
  FROM Orders
 GROUP BY ShipProvince
 ORDER BY TyLeHuyPct DESC;

-- ---------------------------------------------------------------- YC05
-- Canh bao ton kho duoi nguong an toan
CREATE OR REPLACE VIEW vw_CanhBaoTonKho AS
SELECT v.SKU, p.ProductName, c.CategoryName, s.ShopName,
       i.QuantityOnHand, i.SafetyStock,
       (i.SafetyStock - i.QuantityOnHand) AS ThieuHut,
       CASE WHEN i.QuantityOnHand = 0                  THEN 'HET HANG'
            WHEN i.QuantityOnHand < i.SafetyStock * 0.5 THEN 'NGHIEM TRONG'
            ELSE                                             'CANH BAO'
       END AS MucDo
  FROM Inventory i
  JOIN ProductVariant v ON v.VariantID  = i.VariantID
  JOIN Product p        ON p.ProductID  = v.ProductID
  JOIN Category c       ON c.CategoryID = p.CategoryID
  JOIN Seller s         ON s.SellerID   = p.SellerID
 WHERE i.QuantityOnHand < i.SafetyStock
 ORDER BY ThieuHut DESC;

-- ---------------------------------------------------------------- YC06
-- Bang xep hang hieu suat nguoi ban
CREATE OR REPLACE VIEW vw_HieuSuatNguoiBan AS
SELECT s.SellerID, s.ShopName, s.Province,
       COUNT(DISTINCT e.OrderID)                         AS SoDonGiaoThanhCong,
       COALESCE(SUM(e.LineRevenue), 0)                   AS DoanhThu,
       COUNT(DISTINCT p.ProductID)                       AS SoSanPham,
       ROUND(AVG(r.Rating)::numeric, 2)                  AS DiemTrungBinh,
       COUNT(r.ReviewID)                                 AS SoDanhGia,
       RANK() OVER (ORDER BY COALESCE(SUM(e.LineRevenue), 0) DESC) AS HangDoanhThu
  FROM Seller s
  LEFT JOIN Product p          ON p.SellerID = s.SellerID
  LEFT JOIN vw_DongDonMoRong e ON e.SellerID = s.SellerID AND e.Status = 'Delivered'
  LEFT JOIN Review r           ON r.ProductID = p.ProductID
 GROUP BY s.SellerID, s.ShopName, s.Province;

-- ---------------------------------------------------------------- YC07
-- Gia tri don hang trung binh (AOV) theo thang va kenh thanh toan
CREATE OR REPLACE VIEW vw_AOVTheoThangVaKenh AS
WITH tong_don AS (
    SELECT o.OrderID,
           DATE_TRUNC('month', o.OrderDate)::date AS Thang,
           pay.Method                             AS KenhThanhToan,
           SUM(d.Quantity * d.UnitPrice) - o.DiscountAmount AS GiaTriDon
      FROM Orders o
      JOIN OrderDetail d ON d.OrderID = o.OrderID
      JOIN Payment pay   ON pay.OrderID = o.OrderID
     WHERE o.Status = 'Delivered' AND pay.Status = 'Paid'
     GROUP BY o.OrderID, 2, 3, o.DiscountAmount
)
SELECT Thang, KenhThanhToan,
       COUNT(*)                          AS SoDon,
       ROUND(AVG(GiaTriDon), 2)          AS AOV,
       ROUND(SUM(GiaTriDon), 2)          AS TongDoanhThu
  FROM tong_don
 GROUP BY Thang, KenhThanhToan
 ORDER BY Thang, AOV DESC;

-- ---------------------------------------------------------------- YC08
-- Hieu qua chuong trinh khuyen mai
CREATE OR REPLACE VIEW vw_HieuQuaKhuyenMai AS
SELECT pr.PromoCode, pr.DiscountPct, pr.StartDate, pr.EndDate,
       COUNT(DISTINCT o.OrderID)                          AS SoDonApDung,
       COALESCE(SUM(d.Quantity * d.UnitPrice), 0)         AS DoanhThuGoc,
       COALESCE(SUM(DISTINCT o.DiscountAmount), 0)        AS TongGiamGia,
       ROUND(AVG(sub.GiaTriDon), 2)                       AS AOVCoKhuyenMai,
       (SELECT ROUND(AVG(x.GiaTri), 2) FROM (
            SELECT SUM(d2.Quantity * d2.UnitPrice) AS GiaTri
              FROM Orders o2 JOIN OrderDetail d2 ON d2.OrderID = o2.OrderID
             WHERE o2.PromotionID IS NULL AND o2.Status = 'Delivered'
             GROUP BY o2.OrderID) x)                      AS AOVKhongKhuyenMai
  FROM Promotion pr
  LEFT JOIN Orders o      ON o.PromotionID = pr.PromotionID AND o.Status = 'Delivered'
  LEFT JOIN OrderDetail d ON d.OrderID     = o.OrderID
  LEFT JOIN LATERAL (
        SELECT SUM(d3.Quantity * d3.UnitPrice) AS GiaTriDon
          FROM OrderDetail d3 WHERE d3.OrderID = o.OrderID
  ) sub ON TRUE
 GROUP BY pr.PromotionID, pr.PromoCode, pr.DiscountPct, pr.StartDate, pr.EndDate
 ORDER BY SoDonApDung DESC;

-- ---------------------------------------------------------------- YC09
-- Thoi gian giao hang trung binh theo don vi van chuyen
CREATE OR REPLACE VIEW vw_ThoiGianGiaoHang AS
SELECT sh.Carrier                                           AS DonViVanChuyen,
       COUNT(*)                                             AS SoLoHang,
       COUNT(*) FILTER (WHERE sh.Status = 'Delivered')      AS SoLoGiaoThanhCong,
       COUNT(*) FILTER (WHERE sh.Status = 'Failed')         AS SoLoThatBai,
       ROUND(AVG(EXTRACT(EPOCH FROM (sh.DeliveredAt - sh.ShippedAt)) / 86400.0)::numeric, 2)
                                                            AS SoNgayGiaoTB,
       ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (
             ORDER BY EXTRACT(EPOCH FROM (sh.DeliveredAt - sh.ShippedAt)) / 86400.0)::numeric, 2)
                                                            AS P95_SoNgay
  FROM Shipment sh
 WHERE sh.ShippedAt IS NOT NULL
 GROUP BY sh.Carrier
 ORDER BY SoNgayGiaoTB;

-- ---------------------------------------------------------------- YC10
-- Ty le danh gia thap (<= 2 sao) theo danh muc, loc theo nguong tuy chon
CREATE OR REPLACE FUNCTION fn_TyLeDanhGiaThap(p_nguong_pct NUMERIC DEFAULT 0)
RETURNS TABLE (
    DanhMuc        VARCHAR,
    TongDanhGia    BIGINT,
    DanhGiaThap    BIGINT,
    TyLeThapPct    NUMERIC,
    DiemTrungBinh  NUMERIC
) LANGUAGE sql AS $$
    SELECT c.CategoryName,
           COUNT(r.ReviewID),
           COUNT(*) FILTER (WHERE r.Rating <= 2),
           ROUND(100.0 * COUNT(*) FILTER (WHERE r.Rating <= 2) / NULLIF(COUNT(r.ReviewID), 0), 2),
           ROUND(AVG(r.Rating)::numeric, 2)
      FROM Review r
      JOIN Product p  ON p.ProductID  = r.ProductID
      JOIN Category c ON c.CategoryID = p.CategoryID
     GROUP BY c.CategoryName
    HAVING ROUND(100.0 * COUNT(*) FILTER (WHERE r.Rating <= 2) / NULLIF(COUNT(r.ReviewID), 0), 2)
           >= p_nguong_pct
     ORDER BY 4 DESC;
$$;
