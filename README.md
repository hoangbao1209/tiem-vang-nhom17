# Website Bán Hàng & Quản Lý Cửa Hàng Vàng Bạc Đá Quý (Nhóm 17 – SE104.R11)

Hệ thống ứng dụng web phục vụ đồ án môn **Nhập môn Công nghệ Phần mềm (SE104.R11)**, kết hợp **Website trưng bày – đặt hàng trang sức trực tuyến** và **Hệ thống quản lý cửa hàng vàng bạc đá quý** theo đúng đặc tả nghiệp vụ của Nhóm 17.

---

## 1. Công nghệ sử dụng (Đơn giản – Rõ ràng – Dễ mở rộng)
- **Backend:** Python **Flask** (kiến trúc 3 tầng phân tách rõ: `templates/` Giao diện – `blueprints/` + `services/` Nghiệp vụ – `db.py` + `schema.sql` Dữ liệu).
- **Cơ sở dữ liệu:** **SQLite** (`sqlite3` tích hợp sẵn trong Python; tự động khởi tạo schema, nâng cấp cấu trúc và nạp 19 sản phẩm trang sức mẫu cùng các chứng từ minh họa ở lần chạy đầu tiên).
- **Frontend:** HTML5 + Jinja2 Template, CSS3 thuần (hỗ trợ in chứng từ/báo cáo `@media print`), JavaScript thuần tính toán tự động thành tiền, tiền thừa, trả trước tối thiểu và chênh lệch kiểm kê.
- **Triển khai Web:** `gunicorn` (`Procfile`) sẵn sàng deploy trực tiếp trên **Render**.

---

## 2. Chức năng chính của hệ thống

### A. Phân hệ Khách hàng (Storefront)
- **Trang chủ & Danh mục sản phẩm:** Trưng bày 19 sản phẩm trang sức thuộc 7 nhóm (Nhẫn cưới & Nhẫn vàng, Dây chuyền, Lắc tay & Vòng, Bông tai, Kim cương & Đá quý, Trang sức bạc, Vàng miếng – Vàng nhẫn), hỗ trợ tìm kiếm theo tên/mã SP/chất liệu, lọc theo loại, sắp xếp giá và lọc sản phẩm còn hàng.
- **Trang chi tiết sản phẩm:** Hiển thị đầy đủ mã sản phẩm, chất liệu, tuổi vàng/hàm lượng, trọng lượng tham khảo, chính sách bảo hành – thu đổi, tình trạng tồn kho và giá bán niêm yết.
- **Giỏ hàng & Đặt hàng trực tuyến:** Hỗ trợ thêm sản phẩm vào giỏ, chọn phương thức thanh toán (*Tiền mặt* / *Chuyển khoản*), tự động kiểm tra tồn kho và giữ hàng.
- **Tra cứu đơn hàng & Bảng giá dịch vụ kim hoàn:** Khách hàng tra cứu trạng thái xử lý đơn bằng Mã đơn + Số điện thoại; xem bảng giá các dịch vụ gia công, khắc chữ, làm mới, kiểm định tuổi vàng.

### B. Phân hệ Quản lý Cửa hàng (`/quan-ly`)
- **Tổng quan điều hành:** Thống kê doanh thu bán hàng và thực thu dịch vụ trong tháng, đơn online chờ xử lý, phiếu dịch vụ chưa hoàn thành và cảnh báo sản phẩm sắp hết hàng.
- **Phiếu mua hàng & Nhà cung cấp:** Lập phiếu nhập hàng nhiều dòng, tự động cộng tồn kho và cập nhật đơn giá mua gần nhất; quản lý nhà cung cấp theo trạng thái *Đang hợp tác* / *Ngừng hợp tác*.
- **Phiếu bán hàng tại quầy & Đơn Online:** Tính giá bán tự động `Đơn giá bán = Đơn giá mua × (1 + % lợi nhuận loại SP)`, hỗ trợ thanh toán *Tiền mặt* (tính tiền thừa trả khách) / *Chuyển khoản*, xác nhận hoàn tất đơn Online hoặc hủy phiếu hoàn kho.
- **Phiếu dịch vụ, Thu tiền & Theo dõi tiến độ:** Tự động kiểm tra mức trả trước tối thiểu theo tham số hệ thống, ghi nhận các đợt thu tiền dịch vụ (`Thu trả trước` & `Thu phần còn lại`), theo dõi tiến độ từng hạng mục (*Chưa giao* / *Đã giao*) và lưu vết lịch sử chuyển ngược trạng thái có phân quyền và lý do bắt buộc.
- **Kiểm kê kho:** Chụp tồn hệ thống, nhập tồn thực tế, tính chênh lệch và bắt buộc nhập lý do khi có chênh lệch; hỗ trợ quản lý xác nhận biên bản kiểm kê (người xác nhận độc lập với người kiểm kê).
- **Báo cáo Tồn kho, Doanh thu & Chốt kỳ kế toán:** Báo cáo tồn kho tháng (`Tồn đầu`, `Mua vào`, `Ban ra`, `Tồn cuối`), báo cáo doanh thu tách riêng *Doanh thu bán hàng* và *Doanh thu dịch vụ* kèm tỷ lệ %, Top sản phẩm bán chạy, và chức năng chốt kỳ kế toán cố định số liệu tháng.
- **Danh mục, Quy định & Phân quyền:** Quản lý sản phẩm (mã SP, chất liệu, tuổi vàng, trọng lượng, bảo hành, khóa xóa vật lý khi đã phát sinh giao dịch và cho phép chuyển sang *Ngừng kinh doanh*), loại sản phẩm & ĐVT, dịch vụ, tham số hệ thống, phân quyền nhân viên và nhật ký thay đổi quy định.

---

## 3. Hướng dẫn chạy trên Windows & Cập nhật lên Render

### Chạy trên máy cá nhân (Command Prompt `cmd.exe`)
```bat
cd /d "E:\.SE.104.R11 - CNPM\do an\tiem-vang-nhom17"
pip install -r requirements.txt
python run.py
```
Truy cập:
- **Trang bán hàng (Khách hàng):** http://127.0.0.1:5000
- **Trang quản lý (Nhân viên / Quản trị):** http://127.0.0.1:5000/quan-ly

### Tài khoản đăng nhập mẫu
| Vai trò | Tên đăng nhập | Mật khẩu |
|---|---|---|
| Quản trị viên (toàn quyền + xác nhận kiểm kê + chốt kỳ + quy định) | `admin` | `admin123` |
| Nhân viên bán hàng | `nhanvien` | `nhanvien123` |

### Đẩy bản cập nhật lên GitHub để Render tự động triển khai lại
```bat
cd /d "E:\.SE.104.R11 - CNPM\do an\tiem-vang-nhom17"
git add .
git commit -m "Cap nhat day du san pham va giao dien quan ly Nhom 17"
git push
```

---

## 4. Cấu trúc thư mục dự án
```text
tiem-vang-nhom17/
├── config.py                  # Cấu hình đường dẫn CSDL, upload ảnh
├── run.py                     # Điểm khởi chạy ứng dụng
├── run.bat                    # Script chạy nhanh trên Windows
├── Procfile                   # Cấu hình chạy gunicorn trên Render
├── requirements.txt           # Thư viện Python (Flask, gunicorn)
└── app/
    ├── __init__.py            # Application Factory (đăng ký Blueprint)
    ├── db.py                  # Kết nối SQLite & tự khởi tạo / nâng cấp schema
    ├── schema.sql             # Lược đồ toàn bộ bảng CSDL
    ├── seed.py                # Dữ liệu mẫu 19 sản phẩm trang sức & chứng từ mẫu
    ├── auth.py                # Đăng nhập & phân quyền
    ├── utils.py               # Định dạng tiền VNĐ, ngày tháng, kiểm tra đầu vào
    ├── services/              # Tầng xử lý nghiệp vụ
    │   ├── catalog.py         # Truy vấn sản phẩm & công thức tính giá bán
    │   ├── vouchers.py        # Nghiệp vụ phiếu mua, phiếu bán, phiếu dịch vụ & thu tiền
    │   ├── inventory.py       # Nghiệp vụ lập & xác nhận phiếu kiểm kê kho
    │   ├── reports.py         # Báo cáo tồn kho, báo cáo doanh thu & chốt kỳ
    │   └── settings.py        # Tham số hệ thống & nhật ký thay đổi quy định
    ├── blueprints/
    │   ├── shop.py            # Phân hệ khách hàng (Web bán hàng, giỏ hàng, tra cứu)
    │   └── admin.py           # Phân hệ quản lý cửa hàng
    ├── templates/             # Giao diện HTML (Jinja2)
    └── static/                # CSS, JS tính tự động và hình minh họa SVG
```
