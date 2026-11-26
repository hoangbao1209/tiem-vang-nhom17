-- ============================================================================
--  CƠ SỞ DỮ LIỆU: QUẢN LÝ CỬA HÀNG KINH DOANH VÀNG BẠC ĐÁ QUÝ (NHÓM 17 - SE104)
--  Đúng 21 bảng quan hệ chuẩn hóa theo thiết kế Chương 4
-- ============================================================================
PRAGMA foreign_keys = OFF;

-- Xóa các bảng cũ (nếu có từ phiên bản trước)
DROP TABLE IF EXISTS LOAIDICHVU;
DROP TABLE IF EXISTS KHACHHANG;

-- Xóa 21 bảng theo thứ tự phụ thuộc khóa ngoại
DROP TABLE IF EXISTS NHATKYTHAYDOIQUYDINH;
DROP TABLE IF EXISTS BAOCAODOANHTHU_NGAY;
DROP TABLE IF EXISTS BAOCAOTONKHO_THANG;
DROP TABLE IF EXISTS KYKETOAN;
DROP TABLE IF EXISTS CT_PHIEUKIEMKE;
DROP TABLE IF EXISTS PHIEUKIEMKE;
DROP TABLE IF EXISTS LICHSUTINHTRANG;
DROP TABLE IF EXISTS THUTIENDICHVU;
DROP TABLE IF EXISTS CT_PHIEUDICHVU;
DROP TABLE IF EXISTS PHIEUDICHVU;
DROP TABLE IF EXISTS THAMSO;
DROP TABLE IF EXISTS CT_PHIEUBANHANG;
DROP TABLE IF EXISTS PHIEUBANHANG;
DROP TABLE IF EXISTS CT_PHIEUMUAHANG;
DROP TABLE IF EXISTS PHIEUMUAHANG;
DROP TABLE IF EXISTS NGUOIDUNG;
DROP TABLE IF EXISTS DICHVU;
DROP TABLE IF EXISTS NHACUNGCAP;
DROP TABLE IF EXISTS SANPHAM;
DROP TABLE IF EXISTS LOAISANPHAM;
DROP TABLE IF EXISTS DONVITINH;

-- 1. DONVITINH
CREATE TABLE DONVITINH (
    MaDVT   TEXT PRIMARY KEY NOT NULL,
    TenDVT  TEXT NOT NULL UNIQUE
);

-- 2. LOAISANPHAM (PhanTramLoiNhuan lưu dạng thập phân: 0.05 = 5%)
CREATE TABLE LOAISANPHAM (
    MaLoaiSP          TEXT PRIMARY KEY NOT NULL,
    TenLoaiSP         TEXT NOT NULL UNIQUE,
    MaDVT             TEXT NOT NULL REFERENCES DONVITINH(MaDVT),
    PhanTramLoiNhuan  REAL NOT NULL DEFAULT 0 CHECK (PhanTramLoiNhuan >= 0)
);

-- 3. SANPHAM
CREATE TABLE SANPHAM (
    MaSP        TEXT PRIMARY KEY NOT NULL,
    TenSP       TEXT NOT NULL,
    MaLoaiSP    TEXT NOT NULL REFERENCES LOAISANPHAM(MaLoaiSP),
    DonGiaMua   REAL NOT NULL DEFAULT 0 CHECK (DonGiaMua >= 0),
    SoLuongTon  REAL NOT NULL DEFAULT 0 CHECK (SoLuongTon >= 0),
    TinhTrang   TEXT NOT NULL DEFAULT 'Đang kinh doanh'
                CHECK (TinhTrang IN ('Đang kinh doanh', 'Ngừng kinh doanh')),
    -- Thuộc tính mở rộng phục vụ trưng bày trang bán hàng trực tuyến
    ChatLieu    TEXT,
    TuoiVang    TEXT,
    TrongLuong  TEXT,
    BaoHanh     TEXT DEFAULT 'Bảo hành làm sạch & đánh bóng miễn phí trọn đời',
    MoTa        TEXT,
    HinhAnh     TEXT DEFAULT 'img/products/ring-solitaire.jpg',
    HienThi     INTEGER NOT NULL DEFAULT 1 CHECK (HienThi IN (0, 1))
);

-- 4. NHACUNGCAP
CREATE TABLE NHACUNGCAP (
    MaNCC        TEXT PRIMARY KEY NOT NULL,
    TenNCC       TEXT NOT NULL,
    DiaChi       TEXT,
    SoDienThoai  TEXT,
    TinhTrang    TEXT NOT NULL DEFAULT 'Đang hợp tác'
                 CHECK (TinhTrang IN ('Đang hợp tác', 'Ngừng hợp tác'))
);

-- 5. DICHVU (duy nhất 1 bảng dịch vụ, không dùng bảng song song)
CREATE TABLE DICHVU (
    MaDichVu     TEXT PRIMARY KEY NOT NULL,
    TenDichVu    TEXT NOT NULL UNIQUE,
    DonGiaCoBan  REAL NOT NULL CHECK (DonGiaCoBan >= 0),
    TinhTrang    TEXT NOT NULL DEFAULT 'Đang hoạt động'
                 CHECK (TinhTrang IN ('Đang hoạt động', 'Ngừng hoạt động'))
);

-- 6. NGUOIDUNG (dùng chung toàn hệ thống, khóa chính MaNV VARCHAR(20))
CREATE TABLE NGUOIDUNG (
    MaNV                TEXT PRIMARY KEY NOT NULL,
    TenNV               TEXT NOT NULL,
    VaiTro              TEXT NOT NULL CHECK (VaiTro IN ('NhanVien', 'QuanLy')),
    TenDangNhap         TEXT NOT NULL UNIQUE,
    MatKhau             TEXT NOT NULL,
    CoQuyenChuyenNguoc  INTEGER NOT NULL DEFAULT 0 CHECK (CoQuyenChuyenNguoc IN (0, 1)),
    TinhTrang           TEXT NOT NULL DEFAULT 'Đang làm việc'
                        CHECK (TinhTrang IN ('Đang làm việc', 'Đã nghỉ việc'))
);

-- 7. PHIEUMUAHANG (TongTien được tính động từ CT_PHIEUMUAHANG, không lưu trùng)
CREATE TABLE PHIEUMUAHANG (
    SoPhieuMua  TEXT PRIMARY KEY NOT NULL,
    NgayLap     TEXT NOT NULL,
    MaNCC       TEXT NOT NULL REFERENCES NHACUNGCAP(MaNCC),
    MaNV_Lap    TEXT NOT NULL REFERENCES NGUOIDUNG(MaNV),
    GhiChu      TEXT
);

-- 8. CT_PHIEUMUAHANG
CREATE TABLE CT_PHIEUMUAHANG (
    MaCTPM      INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieuMua  TEXT NOT NULL REFERENCES PHIEUMUAHANG(SoPhieuMua) ON DELETE CASCADE,
    SoDong      INTEGER NOT NULL CHECK (SoDong > 0),
    MaSP        TEXT NOT NULL REFERENCES SANPHAM(MaSP),
    SoLuong     REAL NOT NULL CHECK (SoLuong > 0),
    DonGiaMua   REAL NOT NULL CHECK (DonGiaMua >= 0),
    UNIQUE (SoPhieuMua, SoDong)
);

-- 9. PHIEUBANHANG (hỗ trợ cả bán trực tiếp tại quầy và đơn đặt giữ trực tuyến)
CREATE TABLE PHIEUBANHANG (
    SoPhieuBan           TEXT PRIMARY KEY NOT NULL,
    NgayLap              TEXT NOT NULL,
    TenKhachHang         TEXT,
    MaNV_Lap             TEXT REFERENCES NGUOIDUNG(MaNV),
    PhuongThucThanhToan  TEXT NOT NULL DEFAULT 'Tiền mặt'
                         CHECK (PhuongThucThanhToan IN ('Tiền mặt', 'Chuyển khoản')),
    TongTien             REAL NOT NULL CHECK (TongTien >= 0),
    SoTienNhan           REAL NOT NULL CHECK (SoTienNhan >= 0),
    -- Thuộc tính mở rộng hỗ trợ đặt hàng trực tuyến và tra cứu đơn
    SoDienThoai          TEXT,
    DiaChi               TEXT,
    Nguon                TEXT NOT NULL DEFAULT 'Tại quầy'
                         CHECK (Nguon IN ('Tại quầy', 'Online')),
    TrangThai            TEXT NOT NULL DEFAULT 'Hoàn tất'
                         CHECK (TrangThai IN ('Chờ xử lý', 'Hoàn tất', 'Đã hủy')),
    GhiChu               TEXT
);

-- 10. CT_PHIEUBANHANG
CREATE TABLE CT_PHIEUBANHANG (
    MaCTPB      INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieuBan  TEXT NOT NULL REFERENCES PHIEUBANHANG(SoPhieuBan) ON DELETE CASCADE,
    SoDong      INTEGER NOT NULL CHECK (SoDong > 0),
    MaSP        TEXT NOT NULL REFERENCES SANPHAM(MaSP),
    SoLuong     REAL NOT NULL CHECK (SoLuong > 0),
    DonGiaBan   REAL NOT NULL CHECK (DonGiaBan >= 0),
    UNIQUE (SoPhieuBan, SoDong)
);

-- 11. THAMSO (chỉ có duy nhất 1 dòng MaThamSo = 1, TiLeTraTruoc trong [0, 1])
CREATE TABLE THAMSO (
    MaThamSo      INTEGER PRIMARY KEY NOT NULL CHECK (MaThamSo = 1),
    TiLeTraTruoc  REAL NOT NULL DEFAULT 0.5000 CHECK (TiLeTraTruoc >= 0 AND TiLeTraTruoc <= 1)
);

-- 12. PHIEUDICHVU (tình trạng tổng hợp suy ra từ CT_PHIEUDICHVU, không lưu trùng)
CREATE TABLE PHIEUDICHVU (
    SoPhieuDV           TEXT PRIMARY KEY NOT NULL,
    NgayLap             TEXT NOT NULL,
    TenKhachHang        TEXT NOT NULL,
    SoDienThoai         TEXT NOT NULL,
    MaNV_Lap            TEXT NOT NULL REFERENCES NGUOIDUNG(MaNV),
    TiLeTraTruocApDung  REAL NOT NULL CHECK (TiLeTraTruocApDung >= 0 AND TiLeTraTruocApDung <= 1)
);

-- 13. CT_PHIEUDICHVU
CREATE TABLE CT_PHIEUDICHVU (
    MaChiTiet       INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieuDV       TEXT NOT NULL REFERENCES PHIEUDICHVU(SoPhieuDV) ON DELETE CASCADE,
    SoDong          INTEGER NOT NULL CHECK (SoDong > 0),
    MaDichVu        TEXT NOT NULL REFERENCES DICHVU(MaDichVu),
    DonGiaDichVu    REAL NOT NULL CHECK (DonGiaDichVu >= 0),
    ChiPhiRieng     REAL NOT NULL DEFAULT 0 CHECK (ChiPhiRieng >= 0),
    SoLuong         INTEGER NOT NULL CHECK (SoLuong > 0),
    TraTruoc        REAL NOT NULL CHECK (TraTruoc >= 0),
    NgayGiaoDuKien  TEXT NOT NULL,
    TinhTrang       TEXT NOT NULL DEFAULT 'Chưa giao'
                    CHECK (TinhTrang IN ('Chưa giao', 'Đã giao')),
    GhiChu          TEXT,
    UNIQUE (SoPhieuDV, SoDong)
);

-- 14. THUTIENDICHVU
CREATE TABLE THUTIENDICHVU (
    MaPhieuThuDV       TEXT PRIMARY KEY NOT NULL,
    SoPhieuDV          TEXT NOT NULL REFERENCES PHIEUDICHVU(SoPhieuDV),
    NgayThu            TEXT NOT NULL,
    SoTienThu          REAL NOT NULL CHECK (SoTienThu > 0),
    LoaiThu            TEXT NOT NULL CHECK (LoaiThu IN ('Thu trả trước', 'Thu phần còn lại')),
    HinhThucThanhToan  TEXT NOT NULL CHECK (HinhThucThanhToan IN ('Tiền mặt', 'Chuyển khoản')),
    MaNV_Thu           TEXT NOT NULL REFERENCES NGUOIDUNG(MaNV),
    GhiChu             TEXT
);

-- 15. LICHSUTINHTRANG
CREATE TABLE LICHSUTINHTRANG (
    MaLichSu         INTEGER PRIMARY KEY AUTOINCREMENT,
    MaChiTiet        INTEGER NOT NULL REFERENCES CT_PHIEUDICHVU(MaChiTiet),
    MaNV             TEXT NOT NULL REFERENCES NGUOIDUNG(MaNV),
    ThoiDiemCapNhat  TEXT NOT NULL,
    TinhTrangCu      TEXT NOT NULL CHECK (TinhTrangCu IN ('Chưa giao', 'Đã giao')),
    TinhTrangMoi     TEXT NOT NULL CHECK (TinhTrangMoi IN ('Chưa giao', 'Đã giao')),
    LyDo             TEXT,
    CHECK (TinhTrangCu <> TinhTrangMoi)
);

-- 16. PHIEUKIEMKE
CREATE TABLE PHIEUKIEMKE (
    SoPhieuKK         TEXT PRIMARY KEY NOT NULL,
    NgayKiemKe        TEXT NOT NULL,
    MaNV_KiemKe       TEXT NOT NULL REFERENCES NGUOIDUNG(MaNV),
    TrangThaiXacNhan  TEXT NOT NULL DEFAULT 'Chờ xác nhận'
                      CHECK (TrangThaiXacNhan IN ('Chờ xác nhận', 'Đã xác nhận')),
    MaNV_XacNhan      TEXT REFERENCES NGUOIDUNG(MaNV),
    NgayXacNhan       TEXT,
    GhiChu            TEXT
);

-- 17. CT_PHIEUKIEMKE
CREATE TABLE CT_PHIEUKIEMKE (
    MaCTKK         INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieuKK      TEXT NOT NULL REFERENCES PHIEUKIEMKE(SoPhieuKK) ON DELETE CASCADE,
    MaSP           TEXT NOT NULL REFERENCES SANPHAM(MaSP),
    TonHeThong     REAL NOT NULL CHECK (TonHeThong >= 0),
    TonThucTe      REAL NOT NULL CHECK (TonThucTe >= 0),
    ChenhLech      REAL NOT NULL,
    LyDoChenhLech  TEXT,
    UNIQUE (SoPhieuKK, MaSP)
);

-- 18. KYKETOAN (Mở -> Đã chốt -> Đã khóa)
CREATE TABLE KYKETOAN (
    MaKy       INTEGER PRIMARY KEY AUTOINCREMENT,
    Thang      INTEGER NOT NULL CHECK (Thang BETWEEN 1 AND 12),
    Nam        INTEGER NOT NULL CHECK (Nam >= 2000),
    TrangThai  TEXT NOT NULL DEFAULT 'Mở'
               CHECK (TrangThai IN ('Mở', 'Đã chốt', 'Đã khóa')),
    NgayChot   TEXT,
    NgayKhoa   TEXT,
    MaNV_Chot  TEXT REFERENCES NGUOIDUNG(MaNV),
    GhiChu     TEXT,
    UNIQUE (Thang, Nam)
);

-- 19. BAOCAOTONKHO_THANG
CREATE TABLE BAOCAOTONKHO_THANG (
    MaBCTon     INTEGER PRIMARY KEY AUTOINCREMENT,
    MaKy        INTEGER NOT NULL REFERENCES KYKETOAN(MaKy) ON DELETE CASCADE,
    MaSP        TEXT NOT NULL REFERENCES SANPHAM(MaSP),
    TonDau      REAL NOT NULL CHECK (TonDau >= 0),
    SoLuongMua  REAL NOT NULL CHECK (SoLuongMua >= 0),
    SoLuongBan  REAL NOT NULL CHECK (SoLuongBan >= 0),
    TonCuoi     REAL NOT NULL CHECK (TonCuoi >= 0),
    UNIQUE (MaKy, MaSP)
);

-- 20. BAOCAODOANHTHU_NGAY
CREATE TABLE BAOCAODOANHTHU_NGAY (
    MaBCDT_Ngay       INTEGER PRIMARY KEY AUTOINCREMENT,
    MaKy              INTEGER NOT NULL REFERENCES KYKETOAN(MaKy) ON DELETE CASCADE,
    Ngay              TEXT NOT NULL,
    SoGiaoDichBan     INTEGER NOT NULL DEFAULT 0 CHECK (SoGiaoDichBan >= 0),
    DoanhThuBan       REAL NOT NULL DEFAULT 0 CHECK (DoanhThuBan >= 0),
    SoGiaoDichDV      INTEGER NOT NULL DEFAULT 0 CHECK (SoGiaoDichDV >= 0),
    DoanhThuDV        REAL NOT NULL DEFAULT 0 CHECK (DoanhThuDV >= 0),
    TongDoanhThuNgay  REAL NOT NULL DEFAULT 0 CHECK (TongDoanhThuNgay >= 0),
    UNIQUE (MaKy, Ngay)
);

-- 21. NHATKYTHAYDOIQUYDINH (chỉ ghi thêm để truy vết)
CREATE TABLE NHATKYTHAYDOIQUYDINH (
    MaNhatKy         INTEGER PRIMARY KEY AUTOINCREMENT,
    LoaiQuyDinh      TEXT NOT NULL,
    MaDoiTuong       TEXT NOT NULL,
    GiaTriCu         TEXT,
    GiaTriMoi        TEXT NOT NULL,
    ThoiDiemCapNhat  TEXT NOT NULL,
    MaNV_CapNhat     TEXT NOT NULL REFERENCES NGUOIDUNG(MaNV),
    GhiChu           TEXT
);

-- Chỉ mục tối ưu tốc độ tra cứu và báo cáo (CL02)
CREATE INDEX idx_sanpham_loai_tt ON SANPHAM(MaLoaiSP, TinhTrang);
CREATE INDEX idx_sanpham_ten ON SANPHAM(TenSP);
CREATE INDEX idx_pmh_ngay_ncc ON PHIEUMUAHANG(NgayLap, MaNCC);
CREATE INDEX idx_pbh_ngay_kh ON PHIEUBANHANG(NgayLap, TenKhachHang);
CREATE INDEX idx_pdv_ngay ON PHIEUDICHVU(NgayLap);
CREATE INDEX idx_ctpdv_phieu_tt ON CT_PHIEUDICHVU(SoPhieuDV, TinhTrang);
CREATE INDEX idx_ttdv_ngay ON THUTIENDICHVU(NgayThu);
CREATE INDEX idx_kk_ngay ON PHIEUKIEMKE(NgayKiemKe);

PRAGMA foreign_keys = ON;
