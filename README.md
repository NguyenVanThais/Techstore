# TechStore — Ứng dụng bán hàng công nghệ (Tkinter + MongoDB)

Đồ án môn Python nâng cao.


## Quy trình thực hiện một task

1. Mở Issue được giao và chọn **Create a branch**.
2. Đồng bộ nhánh về máy:

   ```powershell
   git fetch origin
   git switch <ten-nhanh-tu-issue>
   ```

3. Code và tự kiểm tra chức năng bằng môi trường ảo.
4. Chỉ stage các file thuộc task, sau đó commit theo Conventional Commits:

   ```powershell
   git status
   git add <file-1> <file-2>
   git commit -m "feat(product): them tim kiem san pham"
   ```

   Tiền tố thường dùng: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

5. Push đúng nhánh cá nhân:

   ```powershell
   git push -u origin <ten-nhanh>
   ```

6. Tạo Pull Request vào `main`; ghi `Closes #N` trong mô tả.
7. Nhờ ít nhất một thành viên khác review. Chỉ merge khi đã kiểm tra luồng liên
   quan và không có thông tin bí mật trong thay đổi.
8. Squash and merge, xóa nhánh đã hoàn thành và cập nhật `main` local.

Không push trực tiếp vào `main` và không push lên nhánh của thành viên khác.

> Mới tải dự án về? Đọc **[HUONG_DAN_CAI_DAT.md](HUONG_DAN_CAI_DAT.md)** — hướng
> dẫn từng bước kèm cách xử lý các lỗi thường gặp.

## Cài đặt

Cần **Python 3.10+** và một **MongoDB** đang chạy (bản local tải ở
[mongodb.com/try/download/community](https://www.mongodb.com/try/download/community),
hoặc một cluster miễn phí trên MongoDB Atlas).

```bash
cd TechStore
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Sao chép `.env.example` thành `.env`. Dùng MongoDB local thì giữ nguyên nội dung
mặc định, dùng Atlas thì thay `MONGO_URI` bằng chuỗi kết nối của bạn.
Muốn Trợ lý AI trả lời bằng Claude thì thêm `ANTHROPIC_API_KEY` (không có
cũng được — trợ lý tự chạy chế độ offline).

## Chạy

```bash
python seed_data.py --force      # tạo dữ liệu mẫu (chạy một lần)
python -m app.main        # mở ứng dụng
```

Hoặc double-click `run.bat` — nó tự tìm venv và chạy app, không cần mở terminal.

Đăng nhập: `admin / admin123` (Quản lý) hoặc `nhanvien / 123456` (Nhân viên).

## Cấu trúc

```
app/
  main.py              điểm khởi chạy
  config.py            đọc .env và settings.json
  database/            kết nối Mongo, index, nâng cấp dữ liệu cũ (bootstrap)
  models/              truy cập collection (product, order, category,
                       customer, user, supplier, purchase, audit)
  services/            nghiệp vụ (bán hàng, nhập hàng, thống kê, PDF, Excel,
                       đăng nhập, trợ lý AI, sao lưu/khôi phục, nhật ký)
  views/               các màn hình Tkinter (12 màn + đăng nhập)
  utils/               validate, định dạng, bỏ dấu tiếng Việt
assets/fonts/          font Unicode cho PDF và biểu đồ
exports/               nơi lưu PDF / Excel xuất ra
```

View không được import `pymongo`. View gọi service, service gọi model, model nói chuyện với Mongo.

## Tiến độ

- [x] Giai đoạn 1 — Nền móng: kết nối, models, seed data, điều hướng
- [x] Giai đoạn 2 — Quản lý sản phẩm: CRUD, phân loại, tìm kiếm, lọc
- [x] Giai đoạn 4a — Tồn kho: cảnh báo dưới mức tối thiểu, nhập thêm hàng
- [x] Giai đoạn 3 — Bán hàng: giỏ hàng, thanh toán, trừ kho
- [x] Giai đoạn 4b — Tra cứu hóa đơn: lọc, xem chi tiết
- [x] Giai đoạn 5 — Thống kê: 4 thẻ số liệu và 3 biểu đồ
- [x] Giai đoạn 6 — Xuất hóa đơn ra PDF
- [x] Quản lý danh mục: thêm, sửa, xóa; đổi tên kéo theo sản phẩm
- [x] Toàn bộ giao diện, dữ liệu mẫu và PDF dùng tiếng Việt có dấu
- [x] Chọn ngày bằng lịch (tkcalendar), xem trước ảnh sản phẩm (Pillow)
- [x] Chống lỗi nhập liệu: escape regex khi tìm kiếm, chặn SKU trùng,
      chấp nhận giá gõ kiểu Việt `1.500.000`
- [x] Đăng nhập + phân quyền (admin / nhân viên), mật khẩu băm PBKDF2
- [x] Khách hàng: tự ghi nhận khi thanh toán, lịch sử mua, nhận diện khách quen
- [x] Hủy hóa đơn: hoàn tồn kho, thống kê tự loại đơn hủy
- [x] Xuất Excel (danh sách hóa đơn + báo cáo thống kê 4 sheet)
- [x] Trợ lý AI chat: Claude API (tùy chọn) hoặc offline theo từ khóa
- [x] Giao diện: chế độ tối, toast, gõ-là-lọc, quét SKU/mã vạch,
      chọn nhanh khoảng ngày, tìm không dấu
- [x] Giá vốn & lợi nhuận: giá vốn tính bình quân gia quyền qua các phiếu
      nhập, đơn hàng nhúng giá vốn tại thời điểm bán, thẻ Lợi nhuận ở Thống kê
- [x] Nhập hàng & Nhà cung cấp: phiếu nhập cộng tồn kho + cập nhật giá vốn,
      lịch sử nhập lọc theo nhà cung cấp / khoảng ngày
- [x] Hoàn trả một phần: hoàn từng dòng sản phẩm trong đơn, cộng trả tồn
      kho, trừ chi tiêu khách, thống kê tự trừ phần đã hoàn
- [x] Khách hàng: sửa thông tin liên hệ, đánh dấu VIP, top khách hàng theo
      chi tiêu ở Thống kê
- [x] Sản phẩm yêu thích: nổi lên đầu danh sách ở màn Sản phẩm và Bán hàng
- [x] Sao lưu / khôi phục dữ liệu ra file JSON (tự sao lưu trước khi ghi đè)
- [x] Nhật ký hoạt động: ai làm gì, lúc nào — đăng nhập, CRUD, thanh toán,
      hủy đơn, hoàn trả, nhập hàng, sao lưu/khôi phục
- [x] Thêm khách hàng bằng tay (admin + nhân viên); admin tạo tài khoản
      đăng nhập mới cho nhân viên ở màn Cài đặt

Toàn bộ chức năng đã hoàn thành — mô tả chi tiết từng chức năng nằm trong
**[TINH_NANG.md](TINH_NANG.md)**. `views/placeholder_view.py` không còn được
dùng ở đâu, có thể xóa.

Mã nguồn (tên biến, chú thích) vẫn viết không dấu; chỉ chữ **hiển thị cho người
dùng** mới có dấu. `seed_data.py` và `db_view.py` gọi
`sys.stdout.reconfigure(encoding="utf-8")` vì console Windows mặc định là cp1252,
in chữ có dấu sẽ ném `UnicodeEncodeError`.

## Bốn quyết định thiết kế cần nhớ khi bảo vệ

**`created_at` lưu kiểu `datetime`, không phải chuỗi.** Toàn bộ thống kê dựa vào
`$dateToString` trên trường này.

**Đơn hàng nhúng sẵn `items` với `category` và `price` copy tại thời điểm bán.**
Nhờ vậy sửa giá sản phẩm không làm sai doanh thu cũ, và thống kê theo loại
không cần `$lookup`. Đây là ưu điểm của NoSQL so với SQL trong bài toán này.

**Trừ kho bằng `find_one_and_update` với điều kiện `stock >= quantity` nằm trong
filter.** Hai nhân viên cùng bán sản phẩm cuối cùng thì chỉ một người thành công.
`is_active: true` cũng nằm trong filter nên không bán được sản phẩm vừa bị xóa
trong lúc nó đang nằm trong giỏ. Nếu đơn có nhiều sản phẩm mà một sản phẩm hết
hàng giữa chừng, `checkout()` hoàn tác các sản phẩm đã trừ trước đó.

**Mã đơn sinh bằng `$inc` trên collection `counters`, không phải bằng cách đếm
số đơn trong ngày.** Đếm thì hai nhân viên bấm Thanh toán cùng lúc sẽ ra cùng
một mã, và xóa một đơn cũ làm mã tiếp theo đâm vào mã đã tồn tại.
`find_one_and_update` với `$inc` là thao tác nguyên tử nên mỗi lần gọi chắc chắn
ra một số khác nhau. Bộ đếm tự khởi tạo từ mã lớn nhất đã có, nên dữ liệu seed
tạo trước đó vẫn dùng được.

## Xử lý tiếng Việt

Font `DejaVuSans.ttf` nằm trong `assets/fonts/` và được commit cùng repo, không
phụ thuộc font hệ thống.

- reportlab: `pdfmetrics.registerFont(TTFont('DejaVu', str(FONT_REGULAR)))`, rồi
  mọi style phải chỉ định `fontName='DejaVu'`.
- matplotlib: `matplotlib.rcParams['font.family'] = 'DejaVu Sans'`.

Quên bước này thì chữ có dấu sẽ thành ô vuông hoặc mất dấu.

## Index

Tạo tự động khi khởi động (`ensure_indexes`): `products.name`, `products.category`,
`categories.name` (unique), `orders.order_code` (unique), `orders.created_at`,
`suppliers.name` (unique), `purchases.receipt_code` (unique), `purchases.created_at`,
`audit_logs.created_at`. Danh sách đầy đủ và lý do từng index nằm trong
[TINH_NANG.md](TINH_NANG.md) mục 14.
