# Hướng dẫn cài đặt TechStore

Dành cho người mới nhận file `TechStore.zip`. Làm theo đúng thứ tự, mất khoảng
10–15 phút, phần lớn là thời gian tải MongoDB.

---

## Bước 0 — Giải nén

Giải nén `TechStore.zip` ra một thư mục bất kỳ, ví dụ `D:\TechStore`.

**Đừng để thư mục nằm trong OneDrive hoặc Desktop đã đồng bộ.** OneDrive hay
khóa file đang mở, gây lỗi khó hiểu khi ứng dụng ghi PDF.

Đường dẫn không cần giống máy người gửi. Ứng dụng tự xác định thư mục gốc.

---

## Bước 1 — Cài Python

Cần **Python 3.10 trở lên**. Kiểm tra bằng cách mở PowerShell rồi gõ:

```powershell
python --version
```

Nếu báo không tìm thấy lệnh, tải tại [python.org/downloads](https://www.python.org/downloads/).
Khi cài, **nhớ tick ô "Add python.exe to PATH"** ở màn hình đầu tiên. Đây là lỗi
phổ biến nhất, bỏ qua là mọi lệnh phía sau đều không chạy.

Ứng dụng dùng Tkinter để vẽ giao diện. Bản Python tải từ python.org đã có sẵn
Tkinter, không cần cài thêm gì.

---

## Bước 2 — Cài MongoDB

Tải **MongoDB Community Server** tại
[mongodb.com/try/download/community](https://www.mongodb.com/try/download/community),
chọn gói `msi` cho Windows.

Trong lúc cài, ở màn hình *Service Configuration*, giữ nguyên lựa chọn mặc định
**"Install MongoDB as a Service"**. Nhờ vậy MongoDB tự chạy nền mỗi khi bật máy,
bạn không phải khởi động thủ công lần nào nữa.

MongoDB Compass (công cụ xem dữ liệu bằng giao diện) là tùy chọn, không bắt buộc.

Kiểm tra MongoDB đã chạy chưa:

```powershell
Get-Service MongoDB
```

Cột `Status` phải là `Running`. Nếu là `Stopped`, chạy PowerShell với quyền
Administrator rồi gõ `Start-Service MongoDB`.

> Không muốn cài MongoDB? Xem mục [Dùng MongoDB Atlas](#dùng-mongodb-atlas-thay-cho-bản-cài-máy) ở cuối file.

---

## Bước 3 — Tạo môi trường ảo và cài thư viện

Mở PowerShell, chuyển vào thư mục dự án:

```powershell
cd D:\TechStore
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Nếu thành công, đầu dòng lệnh sẽ có chữ `(venv)`.

Bản zip **cố ý không kèm thư mục `venv`**. Môi trường ảo chứa đường dẫn tuyệt đối
của máy người gửi nên copy sang máy khác chắc chắn hỏng. Phải tự tạo mới.

Bước `pip install` mất vài phút. Cài xong, thư mục `venv` chiếm khoảng **180 MB**
trên đĩa — chủ yếu là matplotlib và numpy dùng để vẽ biểu đồ.

---

## Bước 4 — Tạo file cấu hình

```powershell
copy .env.example .env
```

Dùng MongoDB cài trên máy thì **giữ nguyên nội dung**, không cần sửa gì.

File `.env` không nằm trong zip vì mỗi máy một cấu hình, và khi dùng Atlas thì nó
chứa mật khẩu.

**Tùy chọn:** muốn màn "Trợ lý AI" trả lời bằng Claude thì mở `.env` và điền
`ANTHROPIC_API_KEY` (lấy tại console.anthropic.com). Không điền cũng không sao —
trợ lý tự chạy chế độ offline, trả lời theo từ khóa trên dữ liệu thật.

---

## Bước 5 — Tạo dữ liệu mẫu

```powershell
python seed_data.py
```

Kết quả mong đợi:

```
Xóa dữ liệu cũ...
Tạo danh mục...
Tạo sản phẩm...
Tạo đơn hàng mẫu (12 tháng gần nhất)...
Tạo hồ sơ khách hàng từ các đơn trên...
Tạo index và tài khoản mặc định...

Xong. 5 danh mục, 31 sản phẩm, 700 đơn hàng, 6 khách hàng.
Có 6 sản phẩm đang dưới mức tồn kho tối thiểu (để test cảnh báo).
Đăng nhập: admin / admin123 (Quản lý) hoặc nhanvien / 123456 (Nhân viên).
```

Chỉ cần chạy **một lần**. Chạy lại sẽ **xóa sạch dữ liệu cũ** rồi tạo lại từ đầu —
tiện khi muốn làm mới, nhưng đừng chạy nhầm sau khi đã bán hàng thật.

Số đơn hàng mỗi lần seed một khác vì được sinh ngẫu nhiên.

---

## Bước 6 — Chạy ứng dụng

Cách đơn giản nhất: **double-click `run.bat`**.

Hoặc từ PowerShell:

```powershell
python -m app.main
```

Màn đăng nhập hiện ra trước. Hai tài khoản có sẵn:

| Tài khoản | Mật khẩu | Thấy gì |
|---|---|---|
| `admin` | `admin123` | Toàn bộ 8 màn hình |
| `nhanvien` | `123456` | Bán hàng, Hóa đơn, Khách hàng, Trợ lý AI |

Đăng nhập bằng `admin` sẽ thấy 8 mục ở thanh bên trái: Bán hàng, Sản phẩm,
Danh mục, Tồn kho, Hóa đơn, Khách hàng, Thống kê, Trợ lý AI. Nút 🌙 ở góc
dưới thanh bên để đổi giao diện sáng/tối.

---

## Khắc phục lỗi thường gặp

### `venv\Scripts\activate` báo lỗi "cannot be loaded because running scripts is disabled"

Windows chặn chạy script theo mặc định. Có hai cách.

Cách nhanh, không cần đổi cài đặt máy — bỏ qua `activate`, gọi thẳng python trong venv:

```powershell
venv\Scripts\python.exe -m app.main
```

Cách sửa hẳn, chạy một lần cho tài khoản của bạn:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Ứng dụng hiện hộp thoại "Lỗi kết nối" rồi tắt

MongoDB chưa chạy. Kiểm tra bằng `Get-Service MongoDB`, nếu `Stopped` thì mở
PowerShell quyền Administrator và chạy `Start-Service MongoDB`.

### `ModuleNotFoundError: No module named 'matplotlib'`

Bạn đang chạy Python hệ thống chứ không phải Python trong venv. Kiểm tra xem đầu
dòng lệnh có `(venv)` chưa. Nếu chưa, chạy lại `venv\Scripts\activate`, hoặc gọi
trực tiếp `venv\Scripts\python.exe -m app.main`.

### Chữ tiếng Việt trong PDF hoặc biểu đồ thành ô vuông

Kiểm tra thư mục `assets/fonts/` có đủ hai file `DejaVuSans.ttf` và
`DejaVuSans-Bold.ttf` không. Ứng dụng dùng font này thay vì font hệ thống, thiếu
là hỏng. Nếu mất, giải nén lại từ file zip gốc.

### `run.bat` báo "Khong tim thay venv"

Bạn chưa làm Bước 3. Chạy `python -m venv venv` rồi
`venv\Scripts\pip install -r requirements.txt`.

### `run.bat` dừng lại với dòng "App thoat voi loi"

Đó là chủ ý — cửa sổ được giữ lại để bạn đọc thông báo lỗi ngay phía trên dòng
đó. Thường là do MongoDB chưa chạy hoặc thiếu thư viện. Xem hai mục ở trên.

### Cửa sổ đen của console nằm cạnh ứng dụng, trông rối

Bình thường, không phải lỗi. Muốn giấu hẳn, mở `run.bat` bằng Notepad và đổi dòng
`venv\Scripts\python.exe -m app.main` thành:

```bat
start "" venv\Scripts\pythonw.exe -m app.main
```

Đánh đổi: nếu ứng dụng chết lúc khởi động, bạn sẽ không thấy thông báo lỗi nào.

---

## Dùng MongoDB Atlas thay cho bản cài máy

Không muốn cài MongoDB, hoặc muốn mang dữ liệu đi nhiều máy:

1. Tạo tài khoản và một cluster miễn phí tại [cloud.mongodb.com](https://cloud.mongodb.com).
2. Trong mục *Network Access*, thêm IP hiện tại của bạn vào danh sách cho phép.
3. Trong mục *Database Access*, tạo user và mật khẩu.
4. Bấm *Connect* → *Drivers* để lấy chuỗi kết nối.
5. Mở file `.env`, thay dòng `MONGO_URI` bằng chuỗi vừa lấy, nhớ điền mật khẩu thật
   vào chỗ `<password>`.

Rồi chạy lại từ Bước 5. Lúc này cần có mạng mới dùng được ứng dụng.

---

## Cấu trúc thư mục

```
app/
  main.py              điểm khởi chạy
  config.py            đọc .env và settings.json
  database/            kết nối Mongo, index, nâng cấp dữ liệu cũ
  models/              truy cập collection (product, order, category,
                       customer, user)
  services/            nghiệp vụ (bán hàng, thống kê, PDF, Excel,
                       đăng nhập, trợ lý AI)
  views/               các màn hình Tkinter (8 màn + đăng nhập)
assets/fonts/          font Unicode cho PDF và biểu đồ
exports/               nơi lưu PDF / Excel xuất ra
seed_data.py           tạo dữ liệu mẫu
run.bat                chạy nhanh, không cần terminal
```

Danh sách chức năng chi tiết nằm trong `TINH_NANG.md`; kiến trúc và các
quyết định thiết kế nằm trong `README.md`.
