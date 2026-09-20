# Bản T-SQL cho SQL Server

Đây là bản **nộp theo đề bài** (đề yêu cầu SQL Server). Bản PostgreSQL trong
`sql/postgres/` là bản đã chạy thật trên máy Linux để kiểm chứng logic truy vấn —
hai bản tương đương về lược đồ, ràng buộc và kết quả.

## Thứ tự chạy

```sql
:r 01_schema.sql          -- 12 bảng + ràng buộc + chỉ mục
:r 02_triggers.sql        -- 4 ràng buộc nghiệp vụ
:r 03_views_procedures.sql -- 10 view/procedure/function cho YC01–YC10
```

## Những điểm khác biệt phải xử lý khi chuyển từ PostgreSQL sang T-SQL

| Vấn đề | PostgreSQL | SQL Server |
|---|---|---|
| Kiểu liệt kê | `CREATE TYPE ... AS ENUM` | Không có → `VARCHAR` + ràng buộc `CHECK` |
| Khóa tự tăng | `GENERATED ALWAYS AS IDENTITY` | `IDENTITY(1,1)` |
| Chuỗi Unicode | `VARCHAR` đã là UTF-8 | Phải dùng `NVARCHAR` và tiền tố `N'...'` |
| Thời gian | `TIMESTAMP` | `DATETIME2(0)` (chính xác hơn `DATETIME` cũ) |
| Kiểu luận lý | `BOOLEAN` | `BIT` |
| Trigger | `FOR EACH ROW`, biến `NEW`/`OLD` | Chạy theo **tập hợp**, dùng bảng ảo `inserted`/`deleted` |
| Ném lỗi | `RAISE EXCEPTION` | `THROW <mã>, <thông điệp>, 1` |
| Đếm có điều kiện | `COUNT(*) FILTER (WHERE ...)` | `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` |
| Giá trị xuất hiện nhiều nhất | `MODE() WITHIN GROUP` | Không có → truy vấn con `TOP 1 ... ORDER BY COUNT(*) DESC` |
| Bảng tạm trong procedure | `CREATE TEMP TABLE` | `SELECT TOP (@N)` trả thẳng về client |
| `LEFT JOIN LATERAL` | có | `OUTER APPLY` |
| Hàm trả bảng | `RETURNS TABLE ... LANGUAGE sql` | `RETURNS TABLE AS RETURN (...)` (inline TVF) |

### Ràng buộc khóa ngoại — điểm dễ vướng nhất

SQL Server **không cho nhiều đường CASCADE cùng trỏ về một bảng** (lỗi
*"may cause cycles or multiple cascade paths"*). Bảng `Review` có ba khóa ngoại
tới `Product`, `Customer`, `Orders`, trong đó hai đường sau cùng dẫn về `Customer`.
Vì vậy chỉ `FK_Review_Product` được để `ON DELETE CASCADE`, các đường còn lại để
`NO ACTION`. Tương tự, `Category.ParentID` là khóa ngoại tự tham chiếu nên không
dùng được `ON DELETE SET NULL`.
