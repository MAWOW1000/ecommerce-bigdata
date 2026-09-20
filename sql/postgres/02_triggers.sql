-- ============================================================================
--  Rang buoc toan ven muc nghiep vu - khong the dien dat bang CHECK/FK
-- ============================================================================
SET search_path TO ecom, public;

-- RB1: Tru ton kho khi them dong don hang; chan neu khong du hang.
CREATE OR REPLACE FUNCTION trg_tru_ton_kho() RETURNS TRIGGER AS $$
DECLARE
    v_available INTEGER;
BEGIN
    SELECT QuantityOnHand INTO v_available
    FROM Inventory WHERE VariantID = NEW.VariantID
    FOR UPDATE;                                   -- khoa dong, tranh race condition

    IF v_available IS NULL THEN
        RAISE EXCEPTION 'Bien the % chua co ban ghi ton kho', NEW.VariantID;
    END IF;

    IF v_available < NEW.Quantity THEN
        RAISE EXCEPTION 'Khong du ton kho cho bien the %: con %, can %',
                        NEW.VariantID, v_available, NEW.Quantity;
    END IF;

    UPDATE Inventory
       SET QuantityOnHand = QuantityOnHand - NEW.Quantity,
           UpdatedAt      = CURRENT_TIMESTAMP
     WHERE VariantID = NEW.VariantID;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_orderdetail_tru_ton_kho
    BEFORE INSERT ON OrderDetail
    FOR EACH ROW EXECUTE FUNCTION trg_tru_ton_kho();

-- RB2: Hoan tra ton kho khi don chuyen sang Cancelled hoac Returned.
CREATE OR REPLACE FUNCTION trg_hoan_ton_kho() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.Status IN ('Cancelled','Returned') AND OLD.Status NOT IN ('Cancelled','Returned') THEN
        UPDATE Inventory i
           SET QuantityOnHand = i.QuantityOnHand + d.Quantity,
               UpdatedAt      = CURRENT_TIMESTAMP
          FROM OrderDetail d
         WHERE d.OrderID = NEW.OrderID
           AND i.VariantID = d.VariantID;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_orders_hoan_ton_kho
    AFTER UPDATE OF Status ON Orders
    FOR EACH ROW EXECUTE FUNCTION trg_hoan_ton_kho();

-- RB3: Chi duoc danh gia san pham thuoc don hang da giao cua chinh minh.
CREATE OR REPLACE FUNCTION trg_kiem_tra_danh_gia() RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM Orders o
          JOIN OrderDetail d ON d.OrderID  = o.OrderID
          JOIN ProductVariant v ON v.VariantID = d.VariantID
         WHERE o.OrderID    = NEW.OrderID
           AND o.CustomerID = NEW.CustomerID
           AND o.Status     = 'Delivered'
           AND v.ProductID  = NEW.ProductID
    ) THEN
        RAISE EXCEPTION
          'Khach % chua mua/nhan san pham % trong don % nen khong duoc danh gia',
          NEW.CustomerID, NEW.ProductID, NEW.OrderID;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_review_kiem_tra
    BEFORE INSERT ON Review
    FOR EACH ROW EXECUTE FUNCTION trg_kiem_tra_danh_gia();

-- RB4: Cap nhat diem trung binh cua nguoi ban moi khi co danh gia moi.
CREATE OR REPLACE FUNCTION trg_cap_nhat_rating_seller() RETURNS TRIGGER AS $$
BEGIN
    UPDATE Seller s
       SET RatingAvg = sub.avg_rating
      FROM (
            SELECT p.SellerID, ROUND(AVG(r.Rating)::numeric, 2) AS avg_rating
              FROM Review r JOIN Product p ON p.ProductID = r.ProductID
             WHERE p.SellerID = (SELECT SellerID FROM Product WHERE ProductID = NEW.ProductID)
             GROUP BY p.SellerID
           ) sub
     WHERE s.SellerID = sub.SellerID;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_review_cap_nhat_rating
    AFTER INSERT ON Review
    FOR EACH ROW EXECUTE FUNCTION trg_cap_nhat_rating_seller();
