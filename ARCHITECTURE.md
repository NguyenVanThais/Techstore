# ARCHITECTURE.md — TechStore

TechStore là ứng dụng desktop quản lý cửa hàng công nghệ, xây dựng bằng
Tkinter và MongoDB. Tài liệu này mô tả kiến trúc đang được sử dụng trong mã
nguồn. Mọi thay đổi làm ảnh hưởng tên collection, cấu trúc document hoặc luồng
bán/nhập hàng phải được nhóm thống nhất trước khi merge.

## 1. Công nghệ

| Thành phần | Công nghệ | Vai trò |
| --- | --- | --- |
| Ngôn ngữ | Python 3.10+ | Logic ứng dụng |
| Giao diện | Tkinter/ttk | Ứng dụng desktop |
| CSDL | MongoDB + PyMongo | Lưu dữ liệu nghiệp vụ |
| Biểu đồ | Matplotlib | Doanh thu, sản phẩm, khách hàng |
| PDF | ReportLab | Xuất hóa đơn Unicode |
| Excel | OpenPyXL | Xuất hóa đơn và báo cáo |
| Lịch | tkcalendar | Lọc dữ liệu theo ngày |
| Ảnh | Pillow | Xem trước ảnh sản phẩm |
| Cấu hình | python-dotenv | Đọc `MONGO_URI`, `DB_NAME`, API key |
| AI tùy chọn | Anthropic SDK | Trợ lý; có chế độ offline khi thiếu key |

Không commit `.env`, `venv/`, `__pycache__/` hay file xuất thử.

## 2. Kiến trúc phân lớp

```text
┌──────────────────────────────────────────────────────────────┐
│ VIEW — app/views/                                            │
│ MainWindow, Dashboard, Product, Category, Sales, Order,      │
│ Inventory, Customer, Supplier, Purchase, Audit, Settings...  │
└──────────────────────────────┬───────────────────────────────┘
                               │ gọi
┌──────────────────────────────▼───────────────────────────────┐
│ SERVICE — app/services/                                      │
│ sales, purchase, report, PDF, Excel, auth, audit, backup, AI │
└──────────────────────────────┬───────────────────────────────┘
                               │ gọi
┌──────────────────────────────▼───────────────────────────────┐
│ MODEL — app/models/                                          │
│ product, category, order, customer, supplier, purchase...    │
└──────────────────────────────┬───────────────────────────────┘
                               │ PyMongo
┌──────────────────────────────▼───────────────────────────────┐
│ MongoDB — database `techstore`                               │
└──────────────────────────────────────────────────────────────┘
```

Quy tắc:

- View không import hoặc gọi trực tiếp `pymongo`.
- Model chịu trách nhiệm truy cập collection.
- Service điều phối nghiệp vụ có nhiều bước và xử lý rollback.
- Tiện ích dùng chung đặt trong `app/utils/`; giao diện dùng chung đặt trong
  `app/views/widgets.py`, `theme.py` và `base_frame.py`.

## 3. Cấu trúc thư mục thực tế

```text
TechStore/
├── app/
│   ├── main.py                  # điểm khởi chạy
│   ├── config.py                # biến môi trường, đường dẫn, settings
│   ├── database/
│   │   ├── connection.py        # MongoClient, DB, index
│   │   └── bootstrap.py         # nâng cấp dữ liệu cũ, tài khoản mặc định
│   ├── models/                  # thao tác collection
│   ├── services/                # nghiệp vụ và xuất báo cáo
│   ├── utils/                   # validate, format, tìm không dấu
│   └── views/                   # các màn hình Tkinter
├── assets/
│   ├── fonts/                   # DejaVu Sans cho tiếng Việt
│   └── images/                  # ảnh sản phẩm local
├── docs/screenshots/            # ảnh minh họa tài liệu
├── exports/                     # PDF, XLSX và backup sinh khi chạy
├── seed_data.py                 # tạo dữ liệu trình diễn
├── db_view.py                   # xem nhanh dữ liệu MongoDB
├── requirements.txt
├── run.bat
└── README.md
```

## 4. Collection và dữ liệu chính

| Collection | Model | Dữ liệu chính |
| --- | --- | --- |
| `products` | `product.py` | SKU, tên, loại, giá vốn, giá bán, tồn kho |
| `categories` | `category.py` | Tên và mô tả loại sản phẩm |
| `orders` | `order.py` | Mã đơn, items, khách hàng, tổng tiền, hoàn trả |
| `customers` | `customer.py` | Tên, SĐT, tổng chi tiêu, VIP |
| `suppliers` | `supplier.py` | Nhà cung cấp và thông tin liên hệ |
| `purchases` | `purchase.py` | Phiếu nhập, items, nhà cung cấp, tổng tiền |
| `users` | `user.py` | Tài khoản, role, salt và password hash |
| `audit_logs` | `audit.py` | Người dùng, hành động, chi tiết, thời gian |
| `counters` | `order.py`, `purchase.py` | Sinh mã đơn/phiếu nhập nguyên tử |

### Nguyên tắc document hóa đơn

Mỗi item trong hóa đơn nhúng tên, loại, giá bán và giá vốn tại thời điểm bán.
Nhờ đó, sửa sản phẩm sau này không làm thay đổi doanh thu và lợi nhuận lịch sử.

### Nguyên tắc tồn kho

- Bán hàng dùng cập nhật có điều kiện `stock >= quantity`.
- Nếu một dòng thanh toán thất bại, service hoàn lại các dòng đã trừ trước đó.
- Hủy/hoàn hàng cộng lại số lượng tương ứng.
- Nhập hàng cộng tồn và cập nhật giá vốn bình quân gia quyền.

## 5. Luồng ứng dụng

### Khởi động

```text
python -m app.main
  → MainWindow
  → kiểm tra MongoDB và tạo index
  → bootstrap/migrate
  → LoginDialog
  → dựng menu theo quyền
```

### Bán hàng

```text
SalesView → SalesCart → sales_service.checkout()
          → product.decrease_stock()
          → order.create()
          → cập nhật customer
          → audit_service.log()
```

### Nhập hàng

```text
PurchaseView → PurchaseCart → purchase_service.create_receipt()
             → purchase.create()
             → product.apply_purchase()
             → audit_service.log()
```

### Báo cáo

```text
DashboardView → report_service → MongoDB aggregate
              → Matplotlib / excel_service
OrderView     → pdf_service / excel_service
```

## 6. UI và xử lý luồng

- Mọi View kế thừa `BaseFrame` và làm mới dữ liệu bằng `on_show()`.
- `MainWindow.show()` điều hướng màn hình và kiểm tra quyền.
- Matplotlib được nhúng bằng `FigureCanvasTkAgg`; không gọi `plt.show()`.
- AI chạy trong thread nền, nhưng cập nhật Tkinter qua vòng lặp `after()`.
- Theme được khai báo tập trung trong `theme.py`.

## 7. Cấu hình và bảo mật

`.env` tối thiểu:

```dotenv
MONGO_URI=mongodb://localhost:27017
DB_NAME=techstore
# ANTHROPIC_API_KEY=...
```

- Không đưa `.env` lên GitHub.
- Mật khẩu được băm bằng PBKDF2 với salt riêng.
- Tài khoản `admin/admin123` và `nhanvien/123456` chỉ dùng để demo; phải đổi
  khi dùng ngoài môi trường học tập.
- Restore dữ liệu phải tự backup trước khi ghi đè.

## 8. Definition of Done

Một Issue chỉ được coi là hoàn thành khi:

1. Chức năng chạy được từ cửa sổ chính.
2. Dữ liệu sai/rỗng được xử lý và có thông báo rõ.
3. Có kịch bản kiểm thử ghi trong Pull Request.
4. Không lộ thông tin bí mật hoặc commit file sinh khi chạy.
5. Được ít nhất một thành viên khác review và approve.
6. Merge vào `main` không làm hỏng luồng bán hàng, tồn kho và báo cáo.
