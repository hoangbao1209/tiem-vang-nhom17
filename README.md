# Hệ Thống Quản Lý & Website Bán Hàng Vàng Bạc Đá Quý — Kim Ngân Jewelry (SE104.R11 – Nhóm 17)

Đồ án môn **Nhập môn Công nghệ Phần mềm (SE104.R11 – Trường ĐH Công nghệ Thông tin, ĐHQG-HCM)**.
Hệ thống kết hợp **Website bán hàng trang sức trực tuyến** cho khách hàng và **Hệ thống quản lý cửa hàng vàng bạc đá quý** đáp ứng trọn vẹn 15 yêu cầu nghiệp vụ, 21 bảng dữ liệu chuẩn hóa, kiến trúc 3 lớp chặt chẽ và bộ yêu cầu chất lượng (`CL01`–`CL05`, `YCHT01`–`YCHT08`).

---

## 1. Thành viên Nhóm 17
- **Lê Văn Viễn** (24520035)
- **Hoàng Đức Bảo** (24520153)
- **Lê Hoàng Gia Bảo** (24520159)
- **Bùi Quốc Cường** (24520235)
- **Dương Thùy Trâm** (24521802)
- **GVHD:** Đỗ Thị Thanh Tuyền

---

## 2. Công nghệ & Kiến trúc 3 lớp (Presentation – Business – Data)

Hệ thống chọn ngăn xếp công nghệ đơn giản, dễ hiểu cho sinh viên, chạy độc lập trên localhost/mạng LAN không phụ thuộc Internet (`YCHT01`) và sẵn sàng triển khai trực tuyến trên Render:
- **Ngôn ngữ & Framework:** Python 3 + **Flask** (`gunicorn` khi deploy).
- **Cơ sở dữ liệu:** **SQLite** (CSDL quan hệ lưu chuẩn Unicode, tích hợp sẵn trong Python; tự khởi tạo đủ **21 bảng chuẩn Chương 4** cùng dữ liệu mẫu ngay lần chạy đầu tiên).
- **Giao diện:** HTML5 + Jinja2 + CSS3 thuần (phong cách kim hoàn *Champagne Gold & Obsidian Navy*, hỗ trợ in ấn chứng từ/báo cáo `@media print`) + JavaScript thuần.

### Tuân thủ quy tắc "thang máy" của Kiến trúc 3 lớp (`CL04`)
```text
tiem-vang-nhom17/
├── config.py                      # Cấu hình đường dẫn CSDL, sao lưu, thông tin thương hiệu
├── run.py                         # Điểm khởi chạy ứng dụng
├── run.bat                        # Nhấp đúp để chạy nhanh trên Windows
├── run_tests.bat                  # Nhấp đúp để chạy bộ kiểm thử tự động (unittest)
├── cap_nhat_github.bat            # Nhấp đúp để đẩy bản cập nhật lên GitHub & Render
├── tests/
│   └── test_business_rules.py     # Kiểm thử tự động 15 nghiệp vụ, phân tách 3 lớp & sao lưu
└── app/
    ├── blueprints/                # [Lớp Presentation] Điều khiển HTTP (KHÔNG chứa SQL)
    │   ├── shop.py                # Trang bán hàng, giỏ hàng, đặt giữ & tra cứu đơn Online
    │   └── admin.py               # 15 chức năng quản lý, báo cáo, quy định, sao lưu/phục hồi
    ├── auth.py                    # [Lớp Presentation] Đăng nhập, đổi mật khẩu, phân quyền
    ├── templates/ & static/       # [Lớp Presentation] Giao diện, CSS, JS, hình minh họa SVG
    ├── services/                  # [Lớp Business] Toàn bộ luật nghiệp vụ & giao dịch
    │   ├── catalog.py             # ĐVT, Loại SP, Sản phẩm, Nhà cung cấp, Dịch vụ
    │   ├── vouchers.py            # Phiếu mua, Phiếu bán, Phiếu dịch vụ, Thu tiền, Tiến độ
    │   ├── inventory.py           # Kiểm kê kho & xác nhận biên bản kiểm kê
    │   ├── reports.py             # Báo cáo tồn kho, Báo cáo doanh thu, Chốt kỳ & Khóa kỳ
    │   └── settings.py            # Tài khoản, Tham số trả trước, Nhật ký & Sao lưu/Phục hồi
    ├── repositories.py            # [Lớp Data] Tập trung toàn bộ câu lệnh SQL tham số hóa
    ├── db.py                      # [Lớp Data] Kết nối SQLite, tự nâng cấp, Backup & Restore
    ├── schema.sql                 # [Lớp Data] Lược đồ chuẩn 21 bảng theo Chương 4 báo cáo
    └── seed.py                    # [Lớp Data] Dữ liệu mẫu 19 trang sức & chứng từ minh họa
```

---

## 3. Đầy đủ 15 chức năng nghiệp vụ & yêu cầu hệ thống
1. **Quản lý danh sách sản phẩm** (`/quan-ly/san-pham`): Mã SP duy nhất (`SP001`...), tự tính giá bán từ giá mua và % lợi nhuận, khóa nút Xóa (`disabled`) khi đã phát sinh chứng từ và chỉ chuyển sang *Ngừng kinh doanh*.
2. **Quản lý thông tin nhà cung cấp** (`/quan-ly/nha-cung-cap`): Thêm/sửa/tìm kiếm/ngừng hợp tác; chặn xóa vật lý nếu đã phát sinh phiếu mua hàng.
3. **Quản lý danh sách dịch vụ** (`/quan-ly/loai-dich-vu`): Quản lý bảng `DICHVU` (tên, đơn giá cơ bản, trạng thái); giá mới chỉ áp dụng cho phiếu mới.
4. **Lập phiếu mua hàng** (`/quan-ly/phieu-mua/lap`): Tích hợp tìm nhanh nhà cung cấp, cộng tồn kho & cập nhật giá mua trong cùng giao dịch.
5. **Lập phiếu bán hàng** (`/quan-ly/phieu-ban/lap` & `/thanh-toan`): Tự áp dụng đơn giá bán hiện hành, kiểm tra tồn kho, thanh toán Tiền mặt (tự tính Tiền thừa) / Chuyển khoản, xử lý đơn Online & hủy phiếu hoàn kho.
6. **Lập phiếu dịch vụ** (`/quan-ly/phieu-dich-vu/lap`): Chụp tỷ lệ trả trước từ bảng `THAMSO`, kiểm tra trả trước tối thiểu, tự tạo chứng từ thu tiền ban đầu (`THUTIENDICHVU`).
7. **Tra cứu sản phẩm tồn kho** (`/quan-ly/ton-kho`): Màn hình tra cứu tồn hiện hành chuyên biệt theo mã, tên, loại, mức tồn và hỗ trợ in ấn.
8. **Tra cứu phiếu mua hàng** (`/quan-ly/phieu-mua`): Lọc theo số phiếu, NCC, khoảng ngày; tổng tiền tính động từ chi tiết.
9. **Tra cứu phiếu bán hàng** (`/quan-ly/phieu-ban`): Lọc theo số phiếu, khách hàng, nguồn, phương thức thanh toán, trạng thái, ngày lập.
10. **Tra cứu phiếu dịch vụ** (`/quan-ly/phieu-dich-vu`): Tự suy ra trạng thái *Hoàn thành / Chưa hoàn thành* từ các dòng dịch vụ, theo dõi số tiền thực thu & còn phải thu.
11. **Quản lý tình trạng phiếu dịch vụ** (`/quan-ly/phieu-dich-vu/tien-do`): Cập nhật *Chưa giao → Đã giao*, chuyển ngược yêu cầu quyền `CoQuyenChuyenNguoc` + lý do bắt buộc, lưu vết vào `LICHSUTINHTRANG`.
12. **Lập phiếu kiểm kê kho** (`/quan-ly/kiem-ke`): Chụp tồn hệ thống, nhập tồn thực tế, bắt buộc lý do nếu chênh lệch ≠ 0, Quản lý độc lập xác nhận và không làm thay đổi tồn kho hệ thống.
13. **Lập báo cáo tồn kho** (`/quan-ly/bao-cao-ton-kho`): `Tồn cuối = Tồn đầu + Mua vào − Bán ra`, nối kỳ liên tục, hỗ trợ **Chốt kỳ** và **Khóa kỳ**.
14. **Lập báo cáo doanh thu** (`/quan-ly/bao-cao-doanh-thu`): Tách rõ *1. Doanh thu bán hàng* và *2. Doanh thu dịch vụ* (theo tiền thực thu), chỉ hiển thị ngày phát sinh kèm tỷ lệ %.
15. **Thay đổi quy định, Phân quyền & Sao lưu/Phục hồi** (`/quan-ly/quy-dinh`): Quản lý ĐVT, Loại SP/% lợi nhuận, Dịch vụ, `THAMSO.TiLeTraTruoc`, tài khoản `NhanVien`/`QuanLy`, nhật ký `NHATKYTHAYDOIQUYDINH` và sao lưu/phục hồi tệp `.db`.

---

## 4. Hướng dẫn chạy nhanh trên Windows

- **Chạy website:** Nhấp đúp [run.bat](run.bat) → mở trình duyệt tại `http://127.0.0.1:5000` (Trang bán hàng) hoặc `http://127.0.0.1:5000/quan-ly` (Trang quản lý).
- **Chạy kiểm thử tự động:** Nhấp đúp [run_tests.bat](run_tests.bat) (hoặc chạy `python -m unittest discover -s tests -v`).
- **Đẩy cập nhật lên GitHub / Render:** Nhấp đúp [cap_nhat_github.bat](cap_nhat_github.bat).

### Tài khoản đăng nhập mẫu
| Vai trò | Tên đăng nhập | Mật khẩu | Ghi chú quyền |
|---|---|---|---|
| **Quản lý** (`NV001`) | `admin` | `admin123` | Toàn quyền: quy định, tài khoản, xác nhận kiểm kê, chốt/khóa kỳ, sao lưu/phục hồi |
| **Nhân viên** (`NV002`) | `nhanvien` | `nhanvien123` | Lập phiếu mua/bán/dịch vụ, tra cứu, giao dịch vụ |
| **Nhân viên kho** (`NV003`) | `kho` | `kho123` | Nghiệp vụ nhân viên + có quyền chuyển ngược trạng thái dịch vụ |
