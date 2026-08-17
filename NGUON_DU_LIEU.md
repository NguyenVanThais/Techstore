# NGUON_DU_LIEU.md — Nguồn và quy tắc dữ liệu TechStore

## 1. Phạm vi

Dữ liệu trong `seed_data.py` là **dữ liệu giả lập phục vụ học tập và demo**, không
phải dữ liệu kinh doanh của một cửa hàng có thật. Tên sản phẩm công nghệ được
dùng để tạo tình huống bán hàng gần thực tế; giá, tồn kho, khách hàng, đơn hàng
và phiếu nhập do nhóm đặt hoặc sinh ngẫu nhiên.

Không dùng dữ liệu seed để báo giá, quyết định mua hàng hoặc công bố như số liệu
thị trường.

## 2. Nguồn theo nhóm dữ liệu

| Nhóm | Nguồn | Mức tin cậy | Mục đích |
| --- | --- | --- | --- |
| Loại sản phẩm | Nhóm tự xây dựng | Demo | Phân loại và lọc |
| Tên/SKU sản phẩm | Nhóm tổng hợp theo sản phẩm phổ biến | Demo | CRUD, bán hàng |
| Giá nhập/giá bán | Nhóm đặt để mô phỏng | Không phải báo giá thật | Tính doanh thu/lợi nhuận |
| Tồn kho/tồn tối thiểu | Nhóm đặt và sinh ngẫu nhiên | Demo | Cảnh báo tồn |
| Khách hàng/SĐT | Dữ liệu giả | Demo | Lịch sử mua, VIP |
| Nhà cung cấp | Dữ liệu giả | Demo | Phiếu nhập |
| Phiếu nhập | Sinh bởi `random` | Demo | Giá vốn, lịch sử nhập |
| Hóa đơn | Sinh bởi `random` | Demo | Dashboard, PDF, Excel |
| Tài khoản mặc định | Nhóm định nghĩa | Chỉ demo | Kiểm tra phân quyền |

## 3. Collection được tạo

Chạy `seed_data.py` sẽ tạo lại dữ liệu trong:

```text
categories
products
orders
customers
suppliers
purchases
audit_logs
counters
```

Collection `users` không bị xóa để tránh mất tài khoản hiện có. Script gọi
`ensure_default_users()` để bảo đảm tài khoản demo tồn tại.

## 4. Quy tắc chất lượng dữ liệu

### Sản phẩm

- `sku` phải duy nhất.
- `name` không rỗng; có thêm `name_search` để tìm không dấu.
- `price`, `cost`, `stock`, `min_stock` không âm.
- `price` và `cost` là số; `stock` và `min_stock` là số nguyên.
- Sản phẩm xóa bằng `is_active = false`, không xóa cứng.

### Hóa đơn

- `order_code` duy nhất, sinh qua collection `counters`.
- `created_at` lưu kiểu MongoDB Date/datetime, không lưu chuỗi.
- `items` phải có sản phẩm, số lượng, đơn giá, giá vốn và thành tiền.
- `total` bằng tổng các dòng trước khi trừ phần đã hoàn.
- Đơn bị hủy không được tính vào doanh thu.

### Khách hàng

- Số điện thoại là khóa nhận diện và có unique index.
- Dữ liệu seed là giả; không dùng số điện thoại cá nhân thật.
- Tổng chi tiêu phải khớp các hóa đơn còn hiệu lực sau hoàn trả.

### Phiếu nhập

- `receipt_code` duy nhất.
- Số lượng nhập và đơn giá phải dương.
- Phiếu nhập làm tăng tồn và tham gia tính giá vốn bình quân.

## 5. Tính ngẫu nhiên và khả năng tái lập

`seed_data.py` dùng module `random`, vì vậy số hóa đơn, ngày giao dịch, sản phẩm
trong đơn và giá nhập có thể khác giữa các lần chạy. Đây là chủ ý để biểu đồ có
dữ liệu đa dạng. Nếu cần ảnh báo cáo có số liệu giống nhau tuyệt đối, thêm một
seed cố định trước khi sinh dữ liệu:

```python
random.seed(20260713)
```

Không thay đổi điều này ngay trước khi nộp nếu chưa chụp lại toàn bộ ảnh và cập
nhật số liệu trong báo cáo.

## 6. Quy trình nạp dữ liệu

> Cảnh báo: script seed xóa dữ liệu nghiệp vụ hiện có trong các collection nêu
> ở mục 3. Chỉ chạy trên database demo hoặc sau khi đã backup.

```powershell
cd "C:\Users\ADMIN\Downloads\TechStore (2)\TechStore"
Copy-Item .env.example .env
.\venv\Scripts\python.exe seed_data.py
```

Kiểm tra tổng quan:

```powershell
.\venv\Scripts\python.exe db_view.py
```

Chạy ứng dụng:

```powershell
.\venv\Scripts\python.exe -m app.main
```

## 7. Sao lưu trước khi seed/restore

Nên dùng chức năng **Cài đặt → Sao lưu dữ liệu** trong ứng dụng. File JSON backup
không nên commit nếu chứa dữ liệu thật. Khi trình diễn, chỉ sử dụng dữ liệu giả
và không đưa URI MongoDB Atlas hoặc API key vào tài liệu/ảnh chụp.

## 8. Checklist trước khi nộp

- [ ] Không có thông tin khách hàng hoặc số điện thoại thật.
- [ ] `.env` không nằm trong Git.
- [ ] Giá được ghi rõ là dữ liệu demo.
- [ ] Hóa đơn và phiếu nhập có mã duy nhất.
- [ ] Dashboard không tính đơn đã hủy và đã trừ phần hoàn trả.
- [ ] Ảnh báo cáo khớp với bộ dữ liệu đang demo.
