/* ============================================================================
   Rang buoc toan ven muc nghiep vu - khong dien dat duoc bang CHECK/FK.
   Luu y: trigger SQL Server chay theo TAP HOP dong (bang ao inserted/deleted),
   khong chay tung dong nhu PostgreSQL FOR EACH ROW.
   ============================================================================ */
USE ECommerceDB;
GO

/* --- RB1: Tru ton kho khi them dong don hang; chan neu khong du hang ------ */
CREATE OR ALTER TRIGGER ecom.TR_OrderDetail_TruTonKho
ON ecom.OrderDetail
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    /* Gop theo bien the: mot lenh INSERT co the chua nhieu dong cung VariantID */
    IF EXISTS (
        SELECT 1
          FROM (SELECT VariantID, SUM(Quantity) AS SoLuongCan
                  FROM inserted GROUP BY VariantID) n
          LEFT JOIN ecom.Inventory i ON i.VariantID = n.VariantID
         WHERE i.VariantID IS NULL OR i.QuantityOnHand < n.SoLuongCan
    )
    BEGIN
        DECLARE @msg NVARCHAR(300);
        SELECT TOP 1 @msg = CONCAT(N'Khong du ton kho cho bien the ', n.VariantID,
                                   N': con ', ISNULL(i.QuantityOnHand, 0),
                                   N', can ', n.SoLuongCan)
          FROM (SELECT VariantID, SUM(Quantity) AS SoLuongCan
                  FROM inserted GROUP BY VariantID) n
          LEFT JOIN ecom.Inventory i ON i.VariantID = n.VariantID
         WHERE i.VariantID IS NULL OR i.QuantityOnHand < n.SoLuongCan;

        THROW 51000, @msg, 1;          /* huy toan bo transaction */
    END

    UPDATE i
       SET i.QuantityOnHand = i.QuantityOnHand - n.SoLuongCan,
           i.UpdatedAt      = SYSDATETIME()
      FROM ecom.Inventory i
      JOIN (SELECT VariantID, SUM(Quantity) AS SoLuongCan
              FROM inserted GROUP BY VariantID) n ON n.VariantID = i.VariantID;
END;
GO

/* --- RB2: Hoan tra ton kho khi don chuyen sang Cancelled / Returned ------- */
CREATE OR ALTER TRIGGER ecom.TR_Orders_HoanTonKho
ON ecom.Orders
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT UPDATE(Status) RETURN;

    UPDATE inv
       SET inv.QuantityOnHand = inv.QuantityOnHand + t.SoLuong,
           inv.UpdatedAt      = SYSDATETIME()
      FROM ecom.Inventory inv
      JOIN (
            SELECT d.VariantID, SUM(d.Quantity) AS SoLuong
              FROM inserted i
              JOIN deleted  del ON del.OrderID = i.OrderID
              JOIN ecom.OrderDetail d ON d.OrderID = i.OrderID
             WHERE i.Status   IN ('Cancelled','Returned')
               AND del.Status NOT IN ('Cancelled','Returned')
             GROUP BY d.VariantID
      ) t ON t.VariantID = inv.VariantID;
END;
GO

/* --- RB3: Chi danh gia san pham thuoc don da giao cua chinh minh ---------- */
CREATE OR ALTER TRIGGER ecom.TR_Review_KiemTra
ON ecom.Review
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
          FROM inserted r
         WHERE NOT EXISTS (
                SELECT 1
                  FROM ecom.Orders o
                  JOIN ecom.OrderDetail d    ON d.OrderID   = o.OrderID
                  JOIN ecom.ProductVariant v ON v.VariantID = d.VariantID
                 WHERE o.OrderID    = r.OrderID
                   AND o.CustomerID = r.CustomerID
                   AND o.Status     = 'Delivered'
                   AND v.ProductID  = r.ProductID
         )
    )
        THROW 51001, N'Khach chua mua hoac chua nhan san pham nay nen khong duoc danh gia', 1;
END;
GO

/* --- RB4: Cap nhat diem trung binh cua nguoi ban ------------------------- */
CREATE OR ALTER TRIGGER ecom.TR_Review_CapNhatRating
ON ecom.Review
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    ;WITH SellerBiAnhHuong AS (
        SELECT DISTINCT p.SellerID
          FROM (SELECT ProductID FROM inserted
                UNION
                SELECT ProductID FROM deleted) x
          JOIN ecom.Product p ON p.ProductID = x.ProductID
    )
    UPDATE s
       SET s.RatingAvg = ISNULL(agg.DiemTB, 0)
      FROM ecom.Seller s
      JOIN SellerBiAnhHuong b ON b.SellerID = s.SellerID
      OUTER APPLY (
            SELECT CAST(AVG(CAST(r.Rating AS DECIMAL(5,2))) AS DECIMAL(3,2)) AS DiemTB
              FROM ecom.Review r
              JOIN ecom.Product p2 ON p2.ProductID = r.ProductID
             WHERE p2.SellerID = s.SellerID
      ) agg;
END;
GO
