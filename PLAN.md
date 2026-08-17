# PLAN.md — TechStore (13/07–03/08/2026, 5 người)

Mỗi dòng trong kế hoạch là một GitHub Issue. Issue được tạo từ template Task,
gắn người phụ trách, label, milestone và đưa vào Project board.

Quy trình: Issue → tạo branch → code → commit Conventional Commits → Pull
Request ghi `Closes #N` → một người review → merge vào `main` → xóa branch.

## 1. Thành viên và nhánh chức năng

| Thành viên | Nhánh chính | Phụ trách |
| --- | --- | --- |
| Tống Văn Hiệp | `feature/hiep-sales-orders` | Sản phẩm, bán hàng, hóa đơn, PDF, tích hợp |
| Nguyễn Ngọc Mạnh | `feature/manh-products-inventory` | Danh mục, validation, tồn kho, sửa lỗi |
| Nguyễn Vũ Tiến Phát | `feature/phat-ui-auth` | UI, hóa đơn, điều hướng, đăng nhập |
| Ninh Văn Quyền | `feature/quyen-database-reports` | MongoDB, nhập hàng, nhà cung cấp, thống kê |
| Nguyễn Văn Thái | `feature/thai-customers-docs` | Phân tích, khách hàng, biểu đồ, Excel, tài liệu |

## 2. Label và milestone

Labels: `setup`, `database`, `product`, `sales`, `inventory`, `report`, `ui`,
`test`, `docs`, `bug`, `optional`.

Milestones:

- `Giai đoạn 1 — Phân tích và thiết kế` (13–16/07)
- `Giai đoạn 2 — Chức năng cốt lõi` (17–22/07)
- `Giai đoạn 3 — Thống kê và báo cáo` (22–26/07)
- `Giai đoạn 4 — Tích hợp và kiểm thử` (26–30/07)
- `Giai đoạn 5 — Hoàn thiện` (30/07–03/08)

## 3. Giai đoạn 1 — Phân tích và thiết kế

| # | Thời gian | Issue | Người | Acceptance criteria | Label |
| --- | --- | --- | --- | --- | --- |
| 1 | 13/07 | Chốt mục tiêu, phạm vi và quy ước nhóm | Hiệp | Có danh sách chức năng, cách đặt tên và quy trình Git | docs |
| 2 | 13–14/07 | Phân tích luồng bán hàng | Thái | Mô tả sản phẩm → bán → tồn → doanh thu | docs |
| 3 | 14/07 | Tạo cấu trúc, venv và requirements | Mạnh | Clone mới, cài requirements và chạy được entry point | setup |
| 4 | 14–15/07 | Thiết kế MongoDB và seed data | Quyền | Chốt collection, field, index và dữ liệu giả | database |
| 5 | 15–16/07 | Thiết kế App Shell và điều hướng | Phát | Có cửa sổ chính, sidebar và Frame contract | ui |
| 6 | 16/07 | Kết nối MongoDB | Quyền | Có thông báo kết nối thành công/thất bại, index được tạo | database |

**Checkpoint 16/07:** mọi người chạy được cùng một khung ứng dụng và kết nối
cùng schema MongoDB.

## 4. Giai đoạn 2 — Chức năng cốt lõi

| # | Thời gian | Issue | Người | Acceptance criteria | Label |
| --- | --- | --- | --- | --- | --- |
| 7 | 17/07 | CRUD loại sản phẩm | Mạnh | Chặn tên rỗng/trùng; xử lý loại đang được dùng | product |
| 8 | 17–19/07 | CRUD sản phẩm | Hiệp | SKU duy nhất, gắn loại, giá/tồn hợp lệ, Treeview cập nhật | product |
| 9 | 19/07 | Tìm kiếm, lọc và validation sản phẩm | Mạnh | Tìm mã/tên không dấu, lọc loại, báo đúng field sai | product |
| 10 | 19–20/07 | Giao diện giỏ hàng | Phát | Thêm/xóa dòng, đổi số lượng, tổng tiền cập nhật | ui |
| 11 | 20–21/07 | Thanh toán và tạo hóa đơn | Hiệp | Tạo mã duy nhất, lưu đơn, không bán vượt tồn | sales |
| 12 | 20–21/07 | Nhập hàng và giá vốn | Quyền | Phiếu nhập cộng tồn và cập nhật giá vốn bình quân | inventory |
| 13 | 22/07 | Cảnh báo tồn kho thấp | Mạnh | Liệt kê `stock < min_stock`, có badge/cảnh báo | inventory |

**Checkpoint 22/07:** chạy được luồng thêm sản phẩm → nhập hàng → bán hàng →
giảm tồn → xem hóa đơn.

## 5. Giai đoạn 3 — Thống kê và báo cáo

| # | Thời gian | Issue | Người | Acceptance criteria | Label |
| --- | --- | --- | --- | --- | --- |
| 14 | 22–23/07 | Tổng hợp doanh thu/lợi nhuận | Quyền | Lọc ngày, tháng, năm; loại đơn hủy và phần hoàn | report |
| 15 | 23–24/07 | Tra cứu và chi tiết hóa đơn | Phát | Tìm mã/ngày/khách; mở đúng items và trạng thái | sales |
| 16 | 24–25/07 | Biểu đồ thống kê | Thái | Chart thời gian, loại, top sản phẩm/khách; không làm treo UI | report |
| 17 | 25–26/07 | Xuất PDF và Excel | Hiệp, Thái | Tiếng Việt đúng font; số liệu khớp màn hình | report |

## 6. Giai đoạn 4 — Tích hợp và kiểm thử

| # | Thời gian | Issue | Người | Acceptance criteria | Label |
| --- | --- | --- | --- | --- | --- |
| 18 | 26–27/07 | Tích hợp menu và các Frame | Phát | Mở được tất cả màn hình; refresh đúng khi chuyển màn | ui |
| 19 | 27/07 | Hoàn thiện dữ liệu demo | Quyền | Đủ dữ liệu cho tồn kho, biểu đồ, PDF và Excel | database |
| 20 | 27–28/07 | Test từng chức năng | Mạnh | Có bảng test CRUD, sales, inventory, report, export | test |
| 21 | 28–29/07 | Test tích hợp end-to-end | Hiệp | Chạy xuyên suốt không sai tồn/doanh thu | test |
| 22 | 29–30/07 | Sửa lỗi và xử lý ngoại lệ | Mạnh | Không crash do input rỗng, sai kiểu hoặc mất DB | bug |

Các chức năng mở rộng như đăng nhập, khách hàng, nhà cung cấp, audit, backup và
AI phải được tạo Issue riêng; chỉ merge khi core đã ổn định.

## 7. Giai đoạn 5 — Hoàn thiện

| # | Thời gian | Issue | Người | Acceptance criteria | Label |
| --- | --- | --- | --- | --- | --- |
| 23 | 30–31/07 | Viết báo cáo đồ án | Thái | Có phân tích, kiến trúc, DB, ảnh thật và kiểm thử | docs |
| 24 | 31/07–01/08 | Slide và kịch bản demo | Phát | Slide ngắn, phân vai và thứ tự thao tác rõ | docs |
| 25 | 01–02/08 | Rà code và tài liệu cài đặt | Quyền | README đủ bước MongoDB, venv, seed và chạy | docs |
| 26 | 02/08 | Chạy thử thuyết trình | Hiệp | Đúng thời lượng; mỗi người giải thích được phần mình | test |
| 27 | 03/08 | Đóng gói và phát hành v1.0.0 | Hiệp | Clone sạch, cài, seed, chạy; đủ code/tài liệu/slide | setup |

## 8. Rủi ro và hành động

| Rủi ro | Hành động |
| --- | --- |
| Hai người sửa cùng file | Chia ownership; đồng bộ `main` trước khi bắt đầu |
| Sai tồn kho khi thanh toán lỗi | Service rollback các dòng đã trừ; test case thiếu tồn |
| Doanh thu sai sau hủy/hoàn | Báo cáo loại đơn hủy và trừ `returned_amount` |
| MongoDB không chạy | Kiểm tra kết nối sớm và báo lỗi thân thiện |
| Mất dữ liệu khi seed/restore | Cảnh báo rõ và backup trước khi ghi đè |
| Optional lấn core | Chỉ bắt đầu sau checkpoint 22/07 |
| Lộ API key/Mongo URI | `.env` trong `.gitignore`, kiểm tra trước mỗi PR |

## 9. Definition of Done

1. Chạy được từ `python -m app.main`.
2. Có dữ liệu thử và kịch bản kiểm thử trong PR.
3. Validation và thông báo lỗi đầy đủ.
4. Một thành viên khác review và approve.
5. Không commit `.env`, `venv`, cache hay file xuất thử.
6. Không làm sai tồn kho, doanh thu hoặc dữ liệu lịch sử.
