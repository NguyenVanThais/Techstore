# TechStore — Danh sách chức năng chi tiết

Tài liệu mô tả đầy đủ các chức năng ứng dụng đã làm được, kèm cách hoạt động
bên dưới. Đọc cùng [README.md](README.md) (quyết định thiết kế) và
[HUONG_DAN_CAI_DAT.md](HUONG_DAN_CAI_DAT.md) (cài đặt từng bước).

**Công nghệ:** Python 3.10+ · Tkinter/ttk · MongoDB (pymongo) · matplotlib ·
reportlab · openpyxl · Pillow · tkcalendar · Claude API (tùy chọn).

**Kiến trúc:** View → Service → Model → MongoDB. View không bao giờ import
pymongo; mọi truy vấn nằm trong `app/models/`, nghiệp vụ nằm trong
`app/services/`.

---

## 1. Đăng nhập và phân quyền

- Đăng nhập bằng tài khoản lưu trong collection `users`. Hai tài khoản mặc
  định được tạo sẵn:

  | Tài khoản | Mật khẩu | Vai trò |
  |---|---|---|
  | `admin` | `admin123` | Quản lý — thấy toàn bộ các màn hình |
  | `nhanvien` | `123456` | Nhân viên — chỉ Bán hàng, Hóa đơn, Khách hàng, Trợ lý AI |

- Mật khẩu **không lưu chữ rõ**: băm PBKDF2-SHA256 100.000 vòng, mỗi tài
  khoản một salt ngẫu nhiên riêng. So khớp bằng `hmac.compare_digest`.
- Menu bên trái dựng theo vai trò: nhân viên không nhìn thấy (và không mở
  được) các màn Sản phẩm, Danh mục, Tồn kho, Nhập hàng, Nhà cung cấp,
  Thống kê, Nhật ký, Cài đặt.
- Đăng xuất ngay trong app (chân sidebar) — quay về màn đăng nhập, menu
  dựng lại theo vai trò của người đăng nhập mới.
- Mọi lần đăng nhập / đăng xuất đều được ghi vào **Nhật ký hoạt động** (mục 16).
- **Quản lý mới:** ở màn Cài đặt, Quản lý tạo được tài khoản đăng nhập mới
  (nhân viên hoặc quản lý khác) — chọn tên đăng nhập, mật khẩu, họ tên hiển
  thị và vai trò. Không tự sửa/xóa tài khoản qua giao diện (làm trực tiếp
  trên MongoDB nếu cần) — tránh tự khóa mất tài khoản admin duy nhất.
- Cửa sổ mở **phóng to sẵn** để các bảng nhiều cột không bị che khuất trên
  màn hình nhỏ.

## 2. Bán hàng (POS)

- Tìm sản phẩm **gõ đến đâu lọc đến đó** (debounce 300ms để không truy vấn
  MongoDB trên từng phím).
- **Quét mã vạch / gõ SKU:** gõ đúng một mã SKU rồi Enter là sản phẩm vào
  thẳng giỏ và ô tìm tự xóa để quét tiếp — máy quét mã vạch hoạt động như
  bàn phím nên dùng được ngay.
- Sản phẩm **yêu thích** (đánh dấu ở màn Sản phẩm) luôn nổi lên đầu danh
  sách, có tiền tố ★ để nhận ra ngay.
- Giỏ hàng nằm trong bộ nhớ, chỉ ghi xuống database khi bấm THANH TOÁN.
- Sửa số lượng bằng nút ＋/－ hoặc hộp thoại đồng bộ theme; kiểm tra lại tồn
  kho **mới nhất** từ DB mỗi lần đổi số lượng.
- **Nhận diện khách quen:** nhập số điện thoại từng mua hàng là app tự điền
  tên và hiện "Khách quen: đã mua N lần, tổng X".
- Giảm giá được kiểm tra hai tầng (giao diện + service): không âm, không
  vượt tạm tính.
- Trừ kho bằng `find_one_and_update` với điều kiện `stock >= quantity` ngay
  trong filter — hai máy cùng bán sản phẩm cuối cùng thì chỉ một đơn thành
  công; đơn nhiều sản phẩm mà hết hàng giữa chừng thì các sản phẩm đã trừ
  được hoàn trả (không để dữ liệu nửa vời).
- Mã đơn `HDyyyymmdd-xxxx` sinh bằng `$inc` nguyên tử trên collection
  `counters` — không bao giờ trùng kể cả khi hai người thanh toán cùng lúc.
- Mỗi dòng sản phẩm trong đơn **nhúng cả giá vốn tại thời điểm bán**
  (`items[].cost`) — đây là dữ liệu Thống kê dùng để tính lợi nhuận (mục 11),
  không phụ thuộc giá vốn hiện tại của sản phẩm về sau.
- Thao tác thành công báo bằng **toast** tự biến mất (không phải bấm OK).

## 3. Quản lý sản phẩm (Quản lý)

- CRUD đầy đủ; **xóa mềm** (`is_active=False`) để hóa đơn cũ giữ nguyên.
- Chặn trùng tên và trùng **SKU** (kể cả khác hoa thường — form tự viết hoa).
- Giá nhập được cả kiểu Việt `29.990.000`, kiểu quốc tế `29,990,000` hay số trần.
- **Giá vốn** (`cost`) hiển thị cạnh giá bán trong bảng, dùng để tính lợi
  nhuận ở Thống kê. Sản phẩm mới mặc định giá vốn = 0; giá vốn thật được
  cập nhật tự động qua **Nhập hàng** (mục 6) chứ không sửa tay ở đây (sửa tay
  vẫn được, dùng khi cần chỉnh gấp).
- **Đánh dấu yêu thích** (★): sản phẩm được đánh dấu nổi lên đầu danh sách ở
  cả màn Sản phẩm và màn Bán hàng.
- Ảnh sản phẩm: chọn file → copy vào `assets/images/`, xem trước thumbnail
  ngay trên form; mất file thì báo "(không đọc được ảnh)" chứ không vỡ.
- Lọc theo danh mục + khoảng giá; click tiêu đề cột để sắp xếp (cột giá và
  giá vốn sắp theo **số**, không phải theo chuỗi).
- Cảnh báo tồn kho tô màu: đỏ = hết hàng, vàng = dưới mức tối thiểu.

## 4. Danh mục (Quản lý)

- Thêm / sửa / xóa. Tên danh mục là duy nhất (unique index).
- **Đổi tên kéo theo sản phẩm:** mọi sản phẩm đang dùng tên cũ được
  `update_many` sang tên mới; hóa đơn cũ giữ tên tại thời điểm bán (item đã
  nhúng category).
- Không xóa được danh mục còn sản phẩm.

## 5. Tồn kho (Quản lý)

- Liệt kê sản phẩm có `stock <= min_stock` (so sánh hai trường bằng `$expr`).
- Hai cách nhập thêm hàng:
  - **Nhập nhanh** ngay tại chỗ: chỉ cộng số lượng, không ghi phiếu, không
    đổi giá vốn — dùng cho việc chỉnh gấp.
  - **Lập phiếu nhập:** chuyển sang màn Nhập hàng (mục 6) với sản phẩm đang
    chọn được điền sẵn, ghi đầy đủ nhà cung cấp / giá nhập / người lập.
- Chấm trạng thái ở chân sidebar đổi màu khi có hàng sắp hết, tự làm mới mỗi
  60 giây, **bấm vào là nhảy sang màn Tồn kho** (tài khoản Quản lý).

## 6. Nhập hàng (Quản lý)

- Phiếu nhập gồm: mã phiếu (`PNyyyymmdd-xxxx`, sinh nguyên tử giống mã hóa
  đơn), nhà cung cấp, người lập, ghi chú, danh sách sản phẩm kèm số lượng và
  giá nhập từng dòng.
- Giỏ phiếu nhập nằm trong bộ nhớ (giống giỏ hàng bán), chỉ ghi xuống
  database khi bấm **TẠO PHIẾU NHẬP** — lúc đó mới cộng tồn kho và tính lại
  giá vốn.
- **Giá vốn tính theo bình quân gia quyền**: `(tồn cũ × vốn cũ + nhập ×
  giá nhập) / (tồn cũ + nhập)`. Nhập một đợt giá cao không làm lệch lợi
  nhuận của các đơn bán sau đó theo kiểu "lấy giá mới nhất".
- Phiếu nhúng TÊN nhà cung cấp tại thời điểm nhập (giống cách hóa đơn nhúng
  tên sản phẩm) — sửa hay xóa nhà cung cấp sau này không làm sai lịch sử.
- Nếu một sản phẩm biến mất giữa chừng khi tạo phiếu (hiếm gặp), phần tồn
  kho đã cộng của các sản phẩm trước đó được hoàn tác, không ghi phiếu dở.
- Tab **Lịch sử nhập hàng**: lọc theo mã phiếu, nhà cung cấp, khoảng ngày;
  double-click xem chi tiết từng dòng sản phẩm.

## 7. Nhà cung cấp (Quản lý)

- CRUD: tên, số điện thoại, email, địa chỉ, ghi chú. Tên là duy nhất.
- Bảng hiển thị luôn **số phiếu đã nhập** và **tổng tiền đã nhập** từ mỗi
  nhà cung cấp (tính trên tên đã nhúng trong phiếu, không phụ thuộc nhà
  cung cấp còn tồn tại hay không).
- Xóa nhà cung cấp không ảnh hưởng phiếu nhập cũ — phiếu giữ nguyên tên tại
  thời điểm nhập.

## 8. Tra cứu hóa đơn

- Lọc theo mã đơn, tên/điện thoại khách (gõ là lọc ngay), khoảng ngày bằng
  **lịch tkcalendar** (ô để trống = không lọc).
- Nút chọn nhanh: **Hôm nay / 7 ngày qua / Tháng này / Tất cả**.
- Click tiêu đề cột để sắp xếp (tiền so theo số, thời gian so theo datetime).
- Double-click xem chi tiết: thông tin khách, từng dòng sản phẩm với giá tại
  thời điểm bán, số lượng đã mua / đã hoàn trả, tạm tính / giảm giá / tổng.
- **Hoàn trả một phần**: từ chi tiết đơn, chọn một dòng sản phẩm và bấm
  "Hoàn trả sản phẩm" để trả lại một phần hoặc toàn bộ số lượng đã mua của
  riêng dòng đó:
  - tồn kho được **cộng trả lại** đúng số lượng hoàn;
  - tiền hoàn tính theo giá bán, **chia theo tỷ lệ giảm giá của đơn** (đơn
    giảm 10% thì hoàn cũng ít hơn 10%, không hoàn dư cho khách);
  - chi tiêu của khách bị trừ đúng phần tiền hoàn;
  - thao tác nguyên tử (điều kiện nằm trong filter Mongo): hai người cùng
    hoàn một dòng sản phẩm thì không bao giờ hoàn vượt số đã mua;
  - **mọi thống kê tự trừ phần đã hoàn trả** (doanh thu, số lượng bán ra).
- **Xuất PDF** hóa đơn lẻ (font DejaVu, tiếng Việt có dấu chuẩn).
- **Xuất Excel** cả danh sách đang lọc (tiền là số thật + dòng tổng SUMIF).

## 9. Hủy hóa đơn

- Chọn đơn → "Hủy đơn" → xác nhận. Sau khi hủy:
  - tồn kho từng sản phẩm được **cộng trả lại phần CHƯA hoàn trả** (nếu đơn
    đã hoàn trả một phần trước đó, phần đó không bị cộng trả hai lần) —
    kể cả sản phẩm đã ngừng bán;
  - số lần mua / tổng chi tiêu của khách được trừ lại đúng phần thực nhận
    (đã trừ đi phần đã hoàn trả trước đó);
  - đơn gắn `status: "cancelled"`, hiện mờ trong bảng kèm nhãn "Đã hủy";
  - **mọi thống kê tự loại đơn hủy** (`$match: {status: {$ne: "cancelled"}}`).
- Đánh dấu hủy là thao tác nguyên tử (`find_one_and_update` với điều kiện
  `status != cancelled`): hai người cùng bấm Hủy thì chỉ một người thành công,
  tồn kho không bị cộng trả hai lần.

## 10. Khách hàng

- **Tự động:** mỗi lần thanh toán có số điện thoại, app tự upsert một khách
  (khách mới thì tạo, khách cũ thì `$inc` số lần mua + tổng chi tiêu).
- **Thêm bằng tay:** cả Quản lý và Nhân viên đều bấm được "Thêm khách hàng"
  để lập hồ sơ trước khi khách mua lần đầu (ví dụ hỏi số qua điện thoại).
  Khách thêm tay bắt đầu với 0 lần mua / 0 đồng chi tiêu — số liệu tự cộng
  dồn khi khách đó thanh toán đơn đầu tiên. Trùng số điện thoại bị chặn.
- Dữ liệu cũ không mất: lần chạy đầu, app tự dựng hồ sơ khách từ toàn bộ đơn
  đã có (aggregation `$group` theo số điện thoại).
- Tìm theo tên (có dấu hoặc không dấu) hoặc số điện thoại.
- Double-click một khách → **lịch sử mua đầy đủ**, double-click tiếp một đơn
  → chi tiết đơn đó (bao gồm cả nút hoàn trả nếu đơn còn hiệu lực).
- **Sửa thông tin**: họ tên, email, địa chỉ, ghi chú và cờ **★ VIP** (số điện
  thoại là khóa nhận diện khách nên không sửa được ở đây — đổi số nghĩa là
  tách thành khách khác). Khách VIP hiện ★ trước tên trong bảng.

## 11. Thống kê (Quản lý)

- 5 thẻ số liệu: doanh thu, **lợi nhuận**, số hóa đơn, sản phẩm đã bán,
  trung bình mỗi đơn.
- 4 biểu đồ matplotlib nhúng trong tab: doanh thu theo thời gian (ngày /
  tháng / năm), tỷ trọng theo danh mục (tròn + chú giải), top 10 bán chạy
  (cột ngang), **top khách hàng theo chi tiêu** (cột ngang).
- **Lợi nhuận** = doanh thu − giá vốn, tính từ `items[].cost` đã nhúng trong
  từng đơn tại thời điểm bán (mục 2) — không bị ảnh hưởng khi giá vốn hiện
  tại của sản phẩm thay đổi về sau.
- Toàn bộ phép cộng chạy **trên server MongoDB** bằng aggregation pipeline
  (`$match` → `$unwind` → `$group`), không kéo dữ liệu về Python cộng tay.
  Doanh thu / số lượng bán ra đều đã **trừ phần hoàn trả** (mục 8).
- Lọc khoảng ngày bằng lịch + nút chọn nhanh, không tính đơn đã hủy.
- **Xuất Excel báo cáo 4 sheet**: Tổng quan (kèm giá vốn, lợi nhuận), Theo
  thời gian, Theo danh mục, Top sản phẩm.

## 12. Trợ lý AI

- Màn chat hỏi đáp về **số liệu thật** của cửa hàng và cách dùng phần mềm.
- Hai chế độ, tự chọn theo cấu hình:
  - **Có `ANTHROPIC_API_KEY` trong `.env`** → gọi Claude API
    (claude-haiku-4-5). App gói sẵn bản chụp số liệu (doanh thu hôm nay /
    tháng, top bán chạy, hàng sắp hết, khách chi tiêu nhiều) vào system
    prompt nên Claude trả lời theo dữ liệu thật, không bịa số.
  - **Không có key** → bộ trả lời theo từ khóa chạy hoàn toàn offline, vẫn
    đọc MongoDB: hiểu "doanh thu hôm nay / hôm qua / tuần / tháng / năm",
    "sắp hết hàng", "top bán chạy", "khách mua nhiều nhất", "hóa đơn gần
    đây" và các câu "cách …". Câu hỏi được bỏ dấu trước khi so khớp nên gõ
    không dấu vẫn hiểu.
- Gọi API ở **thread riêng** + Queue, giao diện không bao giờ đông cứng;
  API lỗi thì tự rơi về chế độ offline kèm ghi chú.

## 13. Giao diện

- Bảng màu tập trung trong `app/views/theme.py`, theme ttk `clam` tùy biến
  toàn bộ (nút, ô nhập, bảng, tab, thanh cuộn).
- **Chế độ sáng / tối**: nút 🌙 ở chân sidebar, đổi ngay lập tức (giao diện
  được dựng lại với bảng màu mới), lựa chọn lưu vào `settings.json` cho lần
  mở sau.
- Toast góc phải dưới cho thao tác thành công; messagebox chỉ dành cho lỗi
  và xác nhận.
- Bảng trống hiện dòng hướng dẫn ("Không tìm thấy… thử Xóa lọc") thay vì
  trắng trơn.
- Sidebar tối, icon từng mục, hover + active rõ ràng; chân sidebar hiện
  người đang đăng nhập và vai trò.
- Kẻ sọc xen kẽ các bảng; dòng đơn đã hủy làm mờ chữ (hai loại tag không
  giẫm chân nhau: sọc chỉ đặt màu nền, trạng thái chỉ đặt màu chữ).
- Mọi chữ hiển thị đều là **tiếng Việt có dấu** — cả PDF (font DejaVu nhúng
  kèm repo) và biểu đồ (matplotlib DejaVu Sans).

## 14. Chống lỗi nhập liệu và dữ liệu

- Mọi ô tìm kiếm `re.escape` trước khi đưa vào `$regex` — gõ `(`, `[`, `C++`
  không làm văng ứng dụng.
- **Tìm không dấu:** sản phẩm, khách hàng và nhà cung cấp lưu thêm trường
  `name_search` (bỏ dấu, chữ thường, cập nhật tự động khi ghi) — gõ
  "dien thoai" ra "Điện thoại".
- Ngày lọc bao trọn ngày kết thúc (đặt cả `microsecond=999999`).
- Ô ngày cho phép để trống (kế thừa `DateEntry`, bỏ hành vi tự điền lại).
- Dữ liệu cũ tự nâng cấp khi khởi động (`app/database/bootstrap.py`):
  bổ sung `name_search`, gắn `status` cho đơn cũ, dựng hồ sơ khách, tạo tài
  khoản mặc định, gán giá vốn / yêu thích mặc định cho sản phẩm cũ, gán cờ
  VIP mặc định cho khách cũ — tất cả idempotent.
- Unique index: mã đơn, mã phiếu nhập, tên danh mục, tên nhà cung cấp, số
  điện thoại khách, tên đăng nhập.

## 15. Dữ liệu mẫu và tiện ích

- `python seed_data.py`: 5 danh mục, 31 sản phẩm (kèm giá vốn và vài sản
  phẩm yêu thích mẫu), 4 nhà cung cấp, ~24 phiếu nhập, ~450 đơn trải 12
  tháng (cuối tuần / cuối năm bán nhiều hơn), hồ sơ khách dựng sẵn, tài
  khoản mặc định. Giữ nguyên collection `users` khi seed lại.
- `run.bat`: double-click là chạy, tự tìm venv.
- `python db_view.py`: xem nhanh nội dung database ngoài terminal.

## 16. Sao lưu & khôi phục (Quản lý)

- Màn **Cài đặt** → "Sao lưu ngay": xuất toàn bộ dữ liệu (sản phẩm, danh
  mục, hóa đơn, khách hàng, tài khoản, phiếu nhập, nhà cung cấp, nhật ký...)
  ra một file JSON trong `exports/`, dùng `bson.json_util` nên giữ nguyên
  `ObjectId` và `datetime` — khôi phục lại là dữ liệu y hệt.
- "Khôi phục từ file...": **ghi đè toàn bộ** dữ liệu hiện tại. Có hai lớp an
  toàn:
  - tự **sao lưu dữ liệu hiện tại** trước khi ghi đè, để còn đường quay lại
    nếu chọn nhầm file;
  - bắt gõ đúng chữ `XAC NHAN` (không phải một cú click Yes/No) trước khi
    thực hiện — thao tác này không thể hoàn tác bằng nút Undo nào.
- Chỉ Quản lý mới thấy màn Cài đặt.

## 17. Nhật ký hoạt động (Quản lý)

- Ghi lại: người thực hiện, vai trò, hành động, nội dung, thời điểm — cho
  các thao tác: đăng nhập / đăng xuất, thêm / sửa / xóa sản phẩm, thêm / sửa
  / xóa nhà cung cấp, thêm / cập nhật khách hàng, thanh toán, hủy đơn, hoàn
  trả hàng, nhập hàng (cả nhập nhanh và lập phiếu), sao lưu / khôi phục dữ
  liệu.
- Việc ghi log **không bao giờ làm hỏng thao tác chính**: nếu ghi log lỗi
  (ví dụ mất mạng trong tích tắc), lỗi bị nuốt âm thầm — thao tác nghiệp vụ
  vừa thành công không bị rollback chỉ vì nhật ký ghi trượt.
- Màn Nhật ký chỉ đọc: tìm theo người dùng / hành động / nội dung, xem 500
  hoạt động gần nhất.

---

## Các collection trong MongoDB

| Collection | Vai trò | Điểm đáng nói |
|---|---|---|
| `products` | sản phẩm | xóa mềm, `name_search`, `cost` (giá vốn), `favorite`, cảnh báo theo `min_stock` |
| `categories` | danh mục | tên unique, đổi tên cascade sang sản phẩm |
| `orders` | hóa đơn | items **nhúng** giá/giá vốn/danh mục tại thời điểm bán, `status`, `returned` + `refunded` khi hoàn trả |
| `customers` | khách hàng | upsert theo `phone` mỗi lần thanh toán, `vip`, `email`, `address`, `note` |
| `suppliers` | nhà cung cấp | tên unique |
| `purchases` | phiếu nhập hàng | items nhúng giá nhập tại thời điểm nhập, nhúng tên nhà cung cấp |
| `audit_logs` | nhật ký hoạt động | chỉ ghi thêm, không sửa/xóa từ giao diện |
| `users` | tài khoản | PBKDF2 + salt riêng, vai trò admin/staff |
| `counters` | bộ đếm mã đơn / mã phiếu nhập | `$inc` nguyên tử theo ngày |

## Kiểm thử

Ứng dụng được kiểm chứng bằng bộ script tự động (chạy trên database tạm
`techstore_selftest`, widget Tkinter thật, tự xóa sau khi chạy): giỏ hàng và
thanh toán, hủy đơn + hoàn kho, hoàn trả một phần (kể cả hủy đơn sau khi đã
hoàn trả một phần), giá vốn bình quân gia quyền qua nhiều phiếu nhập, lợi
nhuận sau hoàn trả, phân quyền đăng nhập, tìm không dấu, xuất PDF/Excel,
thống kê loại đơn hủy, sao lưu/khôi phục dữ liệu, nhật ký hoạt động, trợ lý
AI offline, theme sáng/tối, toàn bộ 12 màn hình dựng không lỗi — tổng cộng
hơn 280 phép kiểm tra.
