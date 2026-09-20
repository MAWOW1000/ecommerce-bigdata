/* ============================================================================
   Chuong 2 - Luoc do quan he tren SQL Server 2022 (ban nop)
   Ban PostgreSQL tuong duong dung de chay thu nam o sql/postgres/01_schema.sql
   ============================================================================ */

IF DB_ID('ECommerceDB') IS NULL
    CREATE DATABASE ECommerceDB;
GO
USE ECommerceDB;
GO

IF SCHEMA_ID('ecom') IS NULL EXEC('CREATE SCHEMA ecom');
GO

/* Xoa theo dung thu tu phu thuoc khoa ngoai */
DROP TABLE IF EXISTS ecom.Review, ecom.Shipment, ecom.Payment, ecom.OrderDetail,
                     ecom.Orders, ecom.Promotion, ecom.Inventory,
                     ecom.ProductVariant, ecom.Product, ecom.Category,
                     ecom.Seller, ecom.Customer;
GO

/* ----------------------------------------------------------- 1. Khach hang */
CREATE TABLE ecom.Customer (
    CustomerID   INT IDENTITY(1,1) NOT NULL,
    FullName     NVARCHAR(150)  NOT NULL,
    Email        VARCHAR(255)   NOT NULL,
    Phone        VARCHAR(20)    NOT NULL,
    Province     NVARCHAR(100)  NOT NULL,
    Address      NVARCHAR(300)  NOT NULL,
    RegisteredAt DATETIME2(0)   NOT NULL CONSTRAINT DF_Customer_RegisteredAt DEFAULT SYSDATETIME(),
    CONSTRAINT PK_Customer     PRIMARY KEY (CustomerID),
    CONSTRAINT UQ_Customer_Email UNIQUE (Email),
    CONSTRAINT CK_Customer_Email CHECK (Email LIKE '%_@_%._%')
);
GO

/* ----------------------------------------------------------- 2. Nguoi ban */
CREATE TABLE ecom.Seller (
    SellerID     INT IDENTITY(1,1) NOT NULL,
    ShopName     NVARCHAR(150) NOT NULL,
    ContactEmail VARCHAR(255)  NOT NULL,
    Province     NVARCHAR(100) NOT NULL,
    JoinedAt     DATETIME2(0)  NOT NULL CONSTRAINT DF_Seller_JoinedAt DEFAULT SYSDATETIME(),
    RatingAvg    DECIMAL(3,2)  NOT NULL CONSTRAINT DF_Seller_Rating DEFAULT 0.00,
    CONSTRAINT PK_Seller          PRIMARY KEY (SellerID),
    CONSTRAINT UQ_Seller_ShopName UNIQUE (ShopName),
    CONSTRAINT UQ_Seller_Email    UNIQUE (ContactEmail),
    CONSTRAINT CK_Seller_Rating   CHECK (RatingAvg BETWEEN 0 AND 5)
);
GO

/* ----------------------------------------------------- 3. Danh muc (cay) */
CREATE TABLE ecom.Category (
    CategoryID   INT IDENTITY(1,1) NOT NULL,
    CategoryName NVARCHAR(120) NOT NULL,
    ParentID     INT NULL,
    CONSTRAINT PK_Category        PRIMARY KEY (CategoryID),
    CONSTRAINT UQ_Category_Name   UNIQUE (CategoryName),
    /* Khong dung ON DELETE SET NULL vi day la khoa ngoai tu tham chieu:
       SQL Server cam cascade vong. Xu ly bang trigger hoac tang ung dung. */
    CONSTRAINT FK_Category_Parent FOREIGN KEY (ParentID)
        REFERENCES ecom.Category(CategoryID),
    CONSTRAINT CK_Category_NotSelf CHECK (ParentID IS NULL OR ParentID <> CategoryID)
);
GO

/* ----------------------------------------------------------- 4. San pham */
CREATE TABLE ecom.Product (
    ProductID   INT IDENTITY(1,1) NOT NULL,
    SellerID    INT            NOT NULL,
    CategoryID  INT            NOT NULL,
    ProductName NVARCHAR(250)  NOT NULL,
    Description NVARCHAR(MAX)  NULL,
    BasePrice   DECIMAL(18,2)  NOT NULL,
    IsApproved  BIT            NOT NULL CONSTRAINT DF_Product_Approved DEFAULT 0,
    CreatedAt   DATETIME2(0)   NOT NULL CONSTRAINT DF_Product_CreatedAt DEFAULT SYSDATETIME(),
    CONSTRAINT PK_Product          PRIMARY KEY (ProductID),
    CONSTRAINT FK_Product_Seller   FOREIGN KEY (SellerID)
        REFERENCES ecom.Seller(SellerID)   ON DELETE CASCADE,
    CONSTRAINT FK_Product_Category FOREIGN KEY (CategoryID)
        REFERENCES ecom.Category(CategoryID),          /* NO ACTION: cam xoa danh muc con hang */
    CONSTRAINT CK_Product_Price    CHECK (BasePrice > 0)
);
GO

/* ------------------------------------------------------- 5. Bien the SP */
CREATE TABLE ecom.ProductVariant (
    VariantID   INT IDENTITY(1,1) NOT NULL,
    ProductID   INT           NOT NULL,
    SKU         VARCHAR(64)   NOT NULL,
    Color       NVARCHAR(50)  NULL,
    Size        NVARCHAR(30)  NULL,
    PriceAdjust DECIMAL(18,2) NOT NULL CONSTRAINT DF_Variant_Adjust DEFAULT 0,
    CONSTRAINT PK_ProductVariant    PRIMARY KEY (VariantID),
    CONSTRAINT UQ_Variant_SKU       UNIQUE (SKU),
    CONSTRAINT UQ_Variant_Combo     UNIQUE (ProductID, Color, Size),
    CONSTRAINT FK_Variant_Product   FOREIGN KEY (ProductID)
        REFERENCES ecom.Product(ProductID) ON DELETE CASCADE
);
GO

/* ------------------------------------------------------------ 6. Ton kho */
CREATE TABLE ecom.Inventory (
    VariantID      INT          NOT NULL,
    QuantityOnHand INT          NOT NULL CONSTRAINT DF_Inventory_Qty    DEFAULT 0,
    SafetyStock    INT          NOT NULL CONSTRAINT DF_Inventory_Safety DEFAULT 10,
    UpdatedAt      DATETIME2(0) NOT NULL CONSTRAINT DF_Inventory_Updated DEFAULT SYSDATETIME(),
    CONSTRAINT PK_Inventory         PRIMARY KEY (VariantID),
    CONSTRAINT FK_Inventory_Variant FOREIGN KEY (VariantID)
        REFERENCES ecom.ProductVariant(VariantID) ON DELETE CASCADE,
    CONSTRAINT CK_Inventory_Qty     CHECK (QuantityOnHand >= 0),
    CONSTRAINT CK_Inventory_Safety  CHECK (SafetyStock    >= 0)
);
GO

/* --------------------------------------------------------- 7. Khuyen mai */
CREATE TABLE ecom.Promotion (
    PromotionID INT IDENTITY(1,1) NOT NULL,
    PromoCode   VARCHAR(40)   NOT NULL,
    DiscountPct DECIMAL(5,2)  NOT NULL,
    MaxDiscount DECIMAL(18,2) NOT NULL,
    StartDate   DATE          NOT NULL,
    EndDate     DATE          NOT NULL,
    CONSTRAINT PK_Promotion       PRIMARY KEY (PromotionID),
    CONSTRAINT UQ_Promotion_Code  UNIQUE (PromoCode),
    CONSTRAINT CK_Promotion_Pct   CHECK (DiscountPct > 0 AND DiscountPct <= 100),
    CONSTRAINT CK_Promotion_Range CHECK (EndDate >= StartDate)
);
GO

/* ----------------------------------------------------------- 8. Don hang */
CREATE TABLE ecom.Orders (
    OrderID        INT IDENTITY(1,1) NOT NULL,
    CustomerID     INT           NOT NULL,
    PromotionID    INT           NULL,
    OrderDate      DATETIME2(0)  NOT NULL CONSTRAINT DF_Orders_Date   DEFAULT SYSDATETIME(),
    Status         VARCHAR(12)   NOT NULL CONSTRAINT DF_Orders_Status DEFAULT 'Pending',
    ShipProvince   NVARCHAR(100) NOT NULL,
    CancelReason   NVARCHAR(200) NULL,
    DiscountAmount DECIMAL(18,2) NOT NULL CONSTRAINT DF_Orders_Discount DEFAULT 0,
    CONSTRAINT PK_Orders           PRIMARY KEY (OrderID),
    CONSTRAINT FK_Orders_Customer  FOREIGN KEY (CustomerID)
        REFERENCES ecom.Customer(CustomerID),          /* NO ACTION: giu lich su don hang */
    CONSTRAINT FK_Orders_Promotion FOREIGN KEY (PromotionID)
        REFERENCES ecom.Promotion(PromotionID),
    /* SQL Server khong co kieu ENUM -> mo phong bang CHECK */
    CONSTRAINT CK_Orders_Status    CHECK (Status IN
        ('Pending','Confirmed','Shipping','Delivered','Cancelled','Returned')),
    CONSTRAINT CK_Orders_Discount  CHECK (DiscountAmount >= 0),
    CONSTRAINT CK_Orders_Cancel    CHECK (Status <> 'Cancelled' OR CancelReason IS NOT NULL)
);
GO

/* ------------------------------------------------------ 9. Dong don hang */
CREATE TABLE ecom.OrderDetail (
    OrderID   INT           NOT NULL,
    VariantID INT           NOT NULL,
    Quantity  INT           NOT NULL,
    UnitPrice DECIMAL(18,2) NOT NULL,   /* snapshot gia tai thoi diem dat hang */
    CONSTRAINT PK_OrderDetail         PRIMARY KEY (OrderID, VariantID),
    CONSTRAINT FK_OrderDetail_Order   FOREIGN KEY (OrderID)
        REFERENCES ecom.Orders(OrderID) ON DELETE CASCADE,
    CONSTRAINT FK_OrderDetail_Variant FOREIGN KEY (VariantID)
        REFERENCES ecom.ProductVariant(VariantID),
    CONSTRAINT CK_OrderDetail_Qty     CHECK (Quantity  > 0),
    CONSTRAINT CK_OrderDetail_Price   CHECK (UnitPrice > 0)
);
GO

/* -------------------------------------------------------- 10. Thanh toan */
CREATE TABLE ecom.Payment (
    PaymentID INT IDENTITY(1,1) NOT NULL,
    OrderID   INT           NOT NULL,
    Method    VARCHAR(15)   NOT NULL,
    Status    VARCHAR(10)   NOT NULL CONSTRAINT DF_Payment_Status DEFAULT 'Pending',
    Amount    DECIMAL(18,2) NOT NULL,
    PaidAt    DATETIME2(0)  NULL,
    CONSTRAINT PK_Payment        PRIMARY KEY (PaymentID),
    CONSTRAINT UQ_Payment_Order  UNIQUE (OrderID),
    CONSTRAINT FK_Payment_Order  FOREIGN KEY (OrderID)
        REFERENCES ecom.Orders(OrderID) ON DELETE CASCADE,
    CONSTRAINT CK_Payment_Method CHECK (Method IN ('COD','CreditCard','EWallet','BankTransfer')),
    CONSTRAINT CK_Payment_Status CHECK (Status IN ('Pending','Paid','Failed','Refunded')),
    CONSTRAINT CK_Payment_Amount CHECK (Amount >= 0),
    CONSTRAINT CK_Payment_PaidAt CHECK (Status <> 'Paid' OR PaidAt IS NOT NULL)
);
GO

/* ------------------------------------------------------- 11. Van chuyen */
CREATE TABLE ecom.Shipment (
    ShipmentID  INT IDENTITY(1,1) NOT NULL,
    OrderID     INT           NOT NULL,
    Carrier     NVARCHAR(80)  NOT NULL,
    TrackingNo  VARCHAR(64)   NOT NULL,
    Status      VARCHAR(12)   NOT NULL CONSTRAINT DF_Shipment_Status DEFAULT 'Preparing',
    ShippedAt   DATETIME2(0)  NULL,
    DeliveredAt DATETIME2(0)  NULL,
    CONSTRAINT PK_Shipment          PRIMARY KEY (ShipmentID),
    CONSTRAINT UQ_Shipment_Order    UNIQUE (OrderID),
    CONSTRAINT UQ_Shipment_Tracking UNIQUE (TrackingNo),
    CONSTRAINT FK_Shipment_Order    FOREIGN KEY (OrderID)
        REFERENCES ecom.Orders(OrderID) ON DELETE CASCADE,
    CONSTRAINT CK_Shipment_Status   CHECK (Status IN
        ('Preparing','Picked','InTransit','Delivered','Failed')),
    CONSTRAINT CK_Shipment_Dates    CHECK
        (DeliveredAt IS NULL OR ShippedAt IS NULL OR DeliveredAt >= ShippedAt)
);
GO

/* --------------------------------------------------------- 12. Danh gia */
CREATE TABLE ecom.Review (
    ReviewID   INT IDENTITY(1,1) NOT NULL,
    ProductID  INT             NOT NULL,
    CustomerID INT             NOT NULL,
    OrderID    INT             NOT NULL,
    Rating     TINYINT         NOT NULL,
    Comment    NVARCHAR(1000)  NULL,
    CreatedAt  DATETIME2(0)    NOT NULL CONSTRAINT DF_Review_CreatedAt DEFAULT SYSDATETIME(),
    CONSTRAINT PK_Review          PRIMARY KEY (ReviewID),
    CONSTRAINT UQ_Review_Once     UNIQUE (OrderID, ProductID, CustomerID),
    /* Ba khoa ngoai cung tro ve Orders/Customer -> chi mot duong duoc CASCADE,
       cac duong con lai de NO ACTION de tranh loi "multiple cascade paths". */
    CONSTRAINT FK_Review_Product  FOREIGN KEY (ProductID)
        REFERENCES ecom.Product(ProductID)  ON DELETE CASCADE,
    CONSTRAINT FK_Review_Customer FOREIGN KEY (CustomerID)
        REFERENCES ecom.Customer(CustomerID),
    CONSTRAINT FK_Review_Order    FOREIGN KEY (OrderID)
        REFERENCES ecom.Orders(OrderID),
    CONSTRAINT CK_Review_Rating   CHECK (Rating BETWEEN 1 AND 5)
);
GO

/* --------------------------------------------------------------- Chi muc */
CREATE NONCLUSTERED INDEX IX_Product_Category  ON ecom.Product(CategoryID);
CREATE NONCLUSTERED INDEX IX_Product_Seller    ON ecom.Product(SellerID);
CREATE NONCLUSTERED INDEX IX_Orders_Customer   ON ecom.Orders(CustomerID);
CREATE NONCLUSTERED INDEX IX_Orders_Date       ON ecom.Orders(OrderDate)
    INCLUDE (Status, ShipProvince);
CREATE NONCLUSTERED INDEX IX_Orders_Status     ON ecom.Orders(Status);
CREATE NONCLUSTERED INDEX IX_OrderDetail_Variant ON ecom.OrderDetail(VariantID)
    INCLUDE (Quantity, UnitPrice);
CREATE NONCLUSTERED INDEX IX_Review_Product    ON ecom.Review(ProductID) INCLUDE (Rating);
CREATE NONCLUSTERED INDEX IX_Shipment_Carrier  ON ecom.Shipment(Carrier)
    INCLUDE (ShippedAt, DeliveredAt, Status);
GO
