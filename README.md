# Website Bán Hàng & Quản Lý Kinh Doanh Vàng Bạc Đá Quý (Nhóm 17 – SE104.R11)

Đồ án môn **Nhập môn Công nghệ Phần mềm (SE104.R11)** — kết hợp **Website thương mại điện tử (bán hàng trang sức trực tuyến)** và **Hệ thống quản lý cửa hàng vàng bạc đá quý** theo đúng các Biểu mẫu (BM1–BM4) và Quy định nghiệp vụ (QĐ1–QĐ6).

---

## 1. Công nghệ sử dụng (Đơn giản – Dễ hiểu – Dễ mở rộng)
- **Backend:** Python **Flask** (chia module bằng `Blueprint` + tầng nghiệp vụ `services/`).
- **Cơ sở dữ liệu:** **SQLite** (`sqlite3` có sẵn trong Python, không cần cài đặt SQL Server/MySQL riêng; tự động khởi tạo bảng và dữ liệu mẫu ngay lần chạy đầu tiên).
- **Frontend:** HTML5 +Jinja2 Template, CSS3 thuần (giao diện sang trọng, hỗ trợ in phiếu `@media print`), JavaScript thuần tự động tính toán thành tiền/trả trước trên biểu mẫu.

---

## 2. Cách chạy nhanh trên Windows

### Cách 1: Nhấp đúp file `run.bat`
Nhấp đúp vào `run.bat` (hoặc mở **Command Prompt `cmd.exe`** trong thư mục dự án và gõ `run.bat`). Script sẽ tự tạo môi trường ảo, cài `Flask` và mở server tại:
- **Trang bán hàng (Khách hàng):** http://127.0.0.1:5000
- **Trang quản lý (Admin / Nhân viên):** http://127.0.0.1:5000/quan-ly

### Cách 2: Chạy thủ công bằng `cmd`
```bat
cd /d "C:\Users\Bao\.gemini\antigravity\scratch\tiem-vang-nhom17"
pip install -r requirements.txt
python run.py
```

### Tài khoản đăng nhập có sẵn
| Vai trò | Tên đăng nhập | Mật khẩu |
|---|---|---|
| Quản trị viên (toàn quyền + đổi quy định) | `admin` | `admin123` |
| Nhân viên bán hàng | `nhanvien` | `nhanvien123` |

*(Muốn tạo lại cơ sở dữ liệu về trạng thái mẫu ban đầu: xóa file `instance/tiemvang.db` hoặc chạy `flask --app run.py init-db`.)*

---

## 3. Đối chiếu Biểu mẫu & Quy định môn Nhập môn CNPM

| Mã | Nghiệp vụ / Quy định | Nơi thực hiện trong hệ thống |
|---|---|---|
| **BM1** | **Phiếu mua hàng** (Số phiếu, Ngày lập, Nhà cung cấp, danh sách Sản phẩm, Loại, ĐVT, SL, Đơn giá mua, Thành tiền, Tổng tiền) | `/quan-ly/phieu-mua/lap` — Tự động cộng tồn kho và cập nhật đơn giá mua gần nhất. |
| **BM2** | **Phiếu bán hàng** (Lập tại quầy + Đơn đặt hàng Online từ khách) | `/quan-ly/phieu-ban/lap` và `/thanh-toan` — Tự động trừ tồn kho, hỗ trợ hủy phiếu hoàn kho. |
| **BM3** | **Phiếu dịch vụ** (Loại dịch vụ, Đơn giá DV, Chi phí riêng, Đơn giá được tính, SL, Thành tiền, Trả trước, Còn lại, Ngày giao, Tình trạng) | `/quan-ly/phieu-dich-vu/lap` — Giao từng dòng dịch vụ; khi tất cả dòng `Đã giao` thì phiếu tự chuyển sang `Hoàn thành`. |
| **BM4** | **Báo cáo tồn kho theo tháng** (`Tồn đầu`, `Mua vào`, `Bán ra`, `Tồn cuối`) | `/quan-ly/bao-cao-ton-kho` |
| **QĐ1** | Thay đổi số lượng loại sản phẩm, đơn vị tính và tỷ lệ % lợi nhuận | `/quan-ly/loai-san-pham` |
| **QĐ2** | `Đơn giá bán = Đơn giá mua × (1 + % lợi nhuận loại SP)` & kiểm tra `SL bán ≤ SL tồn` | Kiểm tra tại `app/services/catalog.py` & `app/services/vouchers.py` |
| **QĐ3** | `Đơn giá được tính = Đơn giá DV + Chi phí riêng`, `Trả trước ≥ % trả trước tối thiểu × Thành tiền`, `Ngày giao ≥ Ngày lập` | Kiểm tra tại `app/services/vouchers.py` và `/quan-ly/loai-dich-vu` |

---

## 4. Cấu trúc thư mục (Sẵn sàng mở rộng)
```text
tiem-vang-nhom17/
├── config.py                  # Cấu hình đường dẫn CSDL, upload ảnh
├── run.py                     # Điểm khởi chạy ứng dụng
├── run.bat                    # Script chạy nhanh bằng cmd trên Windows
├── requirements.txt           # Chỉ cần Flask
└── app/
    ├── __init__.py            # Application Factory (đăng ký Blueprint)
    ├── db.py                  # Kết nối SQLite & tự khởi tạo dữ liệu
    ├── schema.sql             # Toàn bộ bảng CSDL (Chương 4)
    ├── seed.py                # Dữ liệu mẫu phong phú
    ├── auth.py                # Đăng nhập / phân quyền
    ├── utils.py               # Định dạng tiền VNĐ, ngày tháng, kiểm tra lỗi
    ├── services/              # Tầng xử lý nghiệp vụ & quy định (tách biệt giao diện)
    │   ├── catalog.py         # Truy vấn sản phẩm & công thức tính giá bán
    │   ├── vouchers.py        # Lập phiếu mua, phiếu bán, phiếu dịch vụ (transaction)
    │   ├── reports.py         # Báo cáo tồn kho (BM4) & báo cáo doanh thu
    │   └── settings.py        # Tham số quy định cửa hàng
    ├── blueprints/
    │   ├── shop.py            # Phân hệ khách hàng (Web bán hàng, giỏ hàng, tra cứu)
    │   └── admin.py           # Phân hệ quản lý cửa hàng
    ├── templates/             # Giao diện HTML (Jinja2)
    └── static/                # CSS, JS tính tự động và hình minh họa SVG
```
