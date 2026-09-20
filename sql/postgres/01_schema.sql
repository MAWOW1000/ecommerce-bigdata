-- ============================================================================
--  Chuong 2 - Luoc do quan he (ban PostgreSQL, dung de chay thu va kiem chung)
--  Ban T-SQL cho SQL Server nam o sql/sqlserver/01_schema.sql
-- ============================================================================

DROP SCHEMA IF EXISTS ecom CASCADE;
CREATE SCHEMA ecom;
SET search_path TO ecom, public;

-- ---------------------------------------------------------------- Kieu liet ke
CREATE TYPE order_status   AS ENUM ('Pending','Confirmed','Shipping','Delivered','Cancelled','Returned');
CREATE TYPE payment_status AS ENUM ('Pending','Paid','Failed','Refunded');
CREATE TYPE payment_method AS ENUM ('COD','CreditCard','EWallet','BankTransfer');
CREATE TYPE ship_status    AS ENUM ('Preparing','Picked','InTransit','Delivered','Failed');

-- ---------------------------------------------------------------- 1. Khach hang
CREATE TABLE Customer (
    CustomerID    INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    FullName      VARCHAR(150) NOT NULL,
    Email         VARCHAR(255) NOT NULL UNIQUE,
    Phone         VARCHAR(20)  NOT NULL,
    Province      VARCHAR(100) NOT NULL,
    Address       VARCHAR(300) NOT NULL,
    RegisteredAt  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_cust_email CHECK (Email LIKE '%@%.%')
);

-- ---------------------------------------------------------------- 2. Nguoi ban
CREATE TABLE Seller (
    SellerID      INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ShopName      VARCHAR(150) NOT NULL UNIQUE,
    ContactEmail  VARCHAR(255) NOT NULL UNIQUE,
    Province      VARCHAR(100) NOT NULL,
    JoinedAt      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    RatingAvg     DECIMAL(3,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT ck_seller_rating CHECK (RatingAvg BETWEEN 0 AND 5)
);

-- ---------------------------------------------------------------- 3. Danh muc (cay)
CREATE TABLE Category (
    CategoryID    INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    CategoryName  VARCHAR(120) NOT NULL UNIQUE,
    ParentID      INTEGER      NULL REFERENCES Category(CategoryID) ON DELETE SET NULL,
    CONSTRAINT ck_cat_not_self CHECK (ParentID IS NULL OR ParentID <> CategoryID)
);

-- ---------------------------------------------------------------- 4. San pham
CREATE TABLE Product (
    ProductID     INTEGER       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    SellerID      INTEGER       NOT NULL REFERENCES Seller(SellerID)     ON DELETE CASCADE,
    CategoryID    INTEGER       NOT NULL REFERENCES Category(CategoryID) ON DELETE RESTRICT,
    ProductName   VARCHAR(250)  NOT NULL,
    Description   TEXT          NULL,
    BasePrice     DECIMAL(18,2) NOT NULL,
    IsApproved    BOOLEAN       NOT NULL DEFAULT FALSE,
    CreatedAt     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_prod_price CHECK (BasePrice > 0)
);

-- ---------------------------------------------------------------- 5. Bien the
CREATE TABLE ProductVariant (
    VariantID     INTEGER       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ProductID     INTEGER       NOT NULL REFERENCES Product(ProductID) ON DELETE CASCADE,
    SKU           VARCHAR(64)   NOT NULL UNIQUE,
    Color         VARCHAR(50)   NULL,
    Size          VARCHAR(30)   NULL,
    PriceAdjust   DECIMAL(18,2) NOT NULL DEFAULT 0,
    CONSTRAINT uq_variant_combo UNIQUE (ProductID, Color, Size)
);

-- ---------------------------------------------------------------- 6. Ton kho
CREATE TABLE Inventory (
    VariantID       INTEGER   PRIMARY KEY REFERENCES ProductVariant(VariantID) ON DELETE CASCADE,
    QuantityOnHand  INTEGER   NOT NULL DEFAULT 0,
    SafetyStock     INTEGER   NOT NULL DEFAULT 10,
    UpdatedAt       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_inv_qty    CHECK (QuantityOnHand >= 0),
    CONSTRAINT ck_inv_safety CHECK (SafetyStock   >= 0)
);

-- ---------------------------------------------------------------- 7. Khuyen mai
CREATE TABLE Promotion (
    PromotionID   INTEGER       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    PromoCode     VARCHAR(40)   NOT NULL UNIQUE,
    DiscountPct   DECIMAL(5,2)  NOT NULL,
    MaxDiscount   DECIMAL(18,2) NOT NULL,
    StartDate     DATE          NOT NULL,
    EndDate       DATE          NOT NULL,
    CONSTRAINT ck_promo_pct   CHECK (DiscountPct > 0 AND DiscountPct <= 100),
    CONSTRAINT ck_promo_range CHECK (EndDate >= StartDate)
);

-- ---------------------------------------------------------------- 8. Don hang
CREATE TABLE Orders (
    OrderID        INTEGER       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    CustomerID     INTEGER       NOT NULL REFERENCES Customer(CustomerID)   ON DELETE RESTRICT,
    PromotionID    INTEGER       NULL     REFERENCES Promotion(PromotionID) ON DELETE SET NULL,
    OrderDate      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Status         order_status  NOT NULL DEFAULT 'Pending',
    ShipProvince   VARCHAR(100)  NOT NULL,
    CancelReason   VARCHAR(200)  NULL,
    DiscountAmount DECIMAL(18,2) NOT NULL DEFAULT 0,
    CONSTRAINT ck_ord_discount CHECK (DiscountAmount >= 0),
    CONSTRAINT ck_ord_cancel   CHECK (Status <> 'Cancelled' OR CancelReason IS NOT NULL)
);

-- ---------------------------------------------------------------- 9. Dong don hang
CREATE TABLE OrderDetail (
    OrderID     INTEGER       NOT NULL REFERENCES Orders(OrderID)           ON DELETE CASCADE,
    VariantID   INTEGER       NOT NULL REFERENCES ProductVariant(VariantID) ON DELETE RESTRICT,
    Quantity    INTEGER       NOT NULL,
    UnitPrice   DECIMAL(18,2) NOT NULL,   -- snapshot gia tai thoi diem dat
    PRIMARY KEY (OrderID, VariantID),
    CONSTRAINT ck_od_qty   CHECK (Quantity  > 0),
    CONSTRAINT ck_od_price CHECK (UnitPrice > 0)
);

-- ---------------------------------------------------------------- 10. Thanh toan
CREATE TABLE Payment (
    PaymentID   INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    OrderID     INTEGER        NOT NULL UNIQUE REFERENCES Orders(OrderID) ON DELETE CASCADE,
    Method      payment_method NOT NULL,
    Status      payment_status NOT NULL DEFAULT 'Pending',
    Amount      DECIMAL(18,2)  NOT NULL,
    PaidAt      TIMESTAMP      NULL,
    CONSTRAINT ck_pay_amount CHECK (Amount >= 0),
    CONSTRAINT ck_pay_paidat CHECK (Status <> 'Paid' OR PaidAt IS NOT NULL)
);

-- ---------------------------------------------------------------- 11. Van chuyen
CREATE TABLE Shipment (
    ShipmentID   INTEGER     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    OrderID      INTEGER     NOT NULL UNIQUE REFERENCES Orders(OrderID) ON DELETE CASCADE,
    Carrier      VARCHAR(80) NOT NULL,
    TrackingNo   VARCHAR(64) NOT NULL UNIQUE,
    Status       ship_status NOT NULL DEFAULT 'Preparing',
    ShippedAt    TIMESTAMP   NULL,
    DeliveredAt  TIMESTAMP   NULL,
    CONSTRAINT ck_ship_dates CHECK (DeliveredAt IS NULL OR ShippedAt IS NULL OR DeliveredAt >= ShippedAt)
);

-- ---------------------------------------------------------------- 12. Danh gia
CREATE TABLE Review (
    ReviewID    INTEGER       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ProductID   INTEGER       NOT NULL REFERENCES Product(ProductID)   ON DELETE CASCADE,
    CustomerID  INTEGER       NOT NULL REFERENCES Customer(CustomerID) ON DELETE CASCADE,
    OrderID     INTEGER       NOT NULL REFERENCES Orders(OrderID)      ON DELETE CASCADE,
    Rating      SMALLINT      NOT NULL,
    Comment     VARCHAR(1000) NULL,
    CreatedAt   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_review_once   UNIQUE (OrderID, ProductID, CustomerID),
    CONSTRAINT ck_review_rating CHECK (Rating BETWEEN 1 AND 5)
);

-- ---------------------------------------------------------------- Chi muc
CREATE INDEX ix_product_category ON Product(CategoryID);
CREATE INDEX ix_product_seller   ON Product(SellerID);
CREATE INDEX ix_orders_customer  ON Orders(CustomerID);
CREATE INDEX ix_orders_date      ON Orders(OrderDate);
CREATE INDEX ix_orders_status    ON Orders(Status);
CREATE INDEX ix_od_variant       ON OrderDetail(VariantID);
CREATE INDEX ix_review_product   ON Review(ProductID);
CREATE INDEX ix_shipment_carrier ON Shipment(Carrier);
