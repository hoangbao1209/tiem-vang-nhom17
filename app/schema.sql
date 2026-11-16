-- =============================================================
--  CSDL: Quản lý kinh doanh vàng bạc đá quý - Nhóm 17
-- =============================================================
PRAGMA foreign_keys = OFF;

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
DROP TABLE IF EXISTS LOAIDICHVU;
DROP TABLE IF EXISTS CT_PHIEUBANHANG;
DROP TABLE IF EXISTS PHIEUBANHANG;
DROP TABLE IF EXISTS CT_PHIEUMUAHANG;
DROP TABLE IF EXISTS PHIEUMUAHANG;
DROP TABLE IF EXISTS KHACHHANG;
DROP TABLE IF EXISTS NHACUNGCAP;
DROP TABLE IF EXISTS SANPHAM;
DROP TABLE IF EXISTS LOAISANPHAM;
DROP TABLE IF EXISTS DONVITINH;
DROP TABLE IF EXISTS THAMSO;
DROP TABLE IF EXISTS NGUOIDUNG;

-- ---------- Danh mục ----------
CREATE TABLE DONVITINH (
    MaDVT   INTEGER PRIMARY KEY AUTOINCREMENT,
    TenDVT  TEXT NOT NULL UNIQUE
);

CREATE TABLE LOAISANPHAM (
    MaLoaiSP          INTEGER PRIMARY KEY AUTOINCREMENT,
    TenLoaiSP         TEXT NOT NULL UNIQUE,
    MaDVT             INTEGER NOT NULL REFERENCES DONVITINH(MaDVT),
    PhanTramLoiNhuan  REAL NOT NULL DEFAULT 0 CHECK (PhanTramLoiNhuan >= 0)
);

CREATE TABLE SANPHAM (
    MaSP        INTEGER PRIMARY KEY AUTOINCREMENT,
    MaCode      TEXT UNIQUE,
    TenSP       TEXT NOT NULL,
    MaLoaiSP    INTEGER NOT NULL REFERENCES LOAISANPHAM(MaLoaiSP),
    DonGiaMua   REAL NOT NULL DEFAULT 0 CHECK (DonGiaMua >= 0),
    SoLuongTon  INTEGER NOT NULL DEFAULT 0 CHECK (SoLuongTon >= 0),
    ChatLieu    TEXT,
    TuoiVang    TEXT,
    TrongLuong  TEXT,
    BaoHanh     TEXT DEFAULT 'Bảo hành đánh bóng & làm sạch trọn đời',
    MoTa        TEXT,
    HinhAnh     TEXT,
    TinhTrang   TEXT NOT NULL DEFAULT 'Đang kinh doanh' CHECK (TinhTrang IN ('Đang kinh doanh', 'Ngừng kinh doanh')),
    HienThi     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE NHACUNGCAP (
    MaNCC        INTEGER PRIMARY KEY AUTOINCREMENT,
    TenNCC       TEXT NOT NULL,
    DiaChi       TEXT,
    SoDienThoai  TEXT,
    TinhTrang    TEXT NOT NULL DEFAULT 'Đang hợp tác' CHECK (TinhTrang IN ('Đang hợp tác', 'Ngừng hợp tác'))
);

CREATE TABLE KHACHHANG (
    MaKH         INTEGER PRIMARY KEY AUTOINCREMENT,
    TenKH        TEXT NOT NULL,
    SoDienThoai  TEXT,
    DiaChi       TEXT,
    Email        TEXT
);

CREATE TABLE LOAIDICHVU (
    MaLoaiDV          INTEGER PRIMARY KEY AUTOINCREMENT,
    TenLoaiDV         TEXT NOT NULL UNIQUE,
    DonGia            REAL NOT NULL DEFAULT 0 CHECK (DonGia >= 0),
    PhanTramTraTruoc  REAL NOT NULL DEFAULT 50 CHECK (PhanTramTraTruoc BETWEEN 0 AND 100),
    TinhTrang         TEXT NOT NULL DEFAULT 'Đang hoạt động' CHECK (TinhTrang IN ('Đang hoạt động', 'Ngừng hoạt động'))
);

-- ---------- Tài khoản & phân quyền ----------
CREATE TABLE NGUOIDUNG (
    MaND               INTEGER PRIMARY KEY AUTOINCREMENT,
    TenDangNhap        TEXT NOT NULL UNIQUE,
    MatKhau            TEXT NOT NULL,
    HoTen              TEXT NOT NULL,
    VaiTro             TEXT NOT NULL DEFAULT 'nhanvien' CHECK (VaiTro IN ('admin', 'nhanvien')),
    CoQuyenChuyenNguoc INTEGER NOT NULL DEFAULT 0,
    TinhTrang          TEXT NOT NULL DEFAULT 'Đang làm việc' CHECK (TinhTrang IN ('Đang làm việc', 'Đã nghỉ việc'))
);

-- ---------- Phiếu mua hàng ----------
CREATE TABLE PHIEUMUAHANG (
    SoPhieu   INTEGER PRIMARY KEY AUTOINCREMENT,
    NgayLap   TEXT NOT NULL,
    MaNCC     INTEGER NOT NULL REFERENCES NHACUNGCAP(MaNCC),
    MaND_Lap  INTEGER REFERENCES NGUOIDUNG(MaND),
    TongTien  REAL NOT NULL DEFAULT 0,
    GhiChu    TEXT
);

CREATE TABLE CT_PHIEUMUAHANG (
    MaCT       INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieu    INTEGER NOT NULL REFERENCES PHIEUMUAHANG(SoPhieu) ON DELETE CASCADE,
    MaSP       INTEGER NOT NULL REFERENCES SANPHAM(MaSP),
    SoLuong    INTEGER NOT NULL CHECK (SoLuong > 0),
    DonGia     REAL NOT NULL CHECK (DonGia >= 0),
    ThanhTien  REAL NOT NULL
);

-- ---------- Phiếu bán hàng (tại quầy + đơn đặt online) ----------
CREATE TABLE PHIEUBANHANG (
    SoPhieu              INTEGER PRIMARY KEY AUTOINCREMENT,
    NgayLap              TEXT NOT NULL,
    MaKH                 INTEGER NOT NULL REFERENCES KHACHHANG(MaKH),
    MaND_Lap             INTEGER REFERENCES NGUOIDUNG(MaND),
    PhuongThucThanhToan  TEXT NOT NULL DEFAULT 'Tiền mặt',
    TongTien             REAL NOT NULL DEFAULT 0,
    SoTienNhan           REAL NOT NULL DEFAULT 0,
    TienThua             REAL NOT NULL DEFAULT 0,
    Nguon                TEXT NOT NULL DEFAULT 'Tại quầy',
    TrangThai            TEXT NOT NULL DEFAULT 'Hoàn tất',
    GhiChu               TEXT
);

CREATE TABLE CT_PHIEUBANHANG (
    MaCT       INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieu    INTEGER NOT NULL REFERENCES PHIEUBANHANG(SoPhieu) ON DELETE CASCADE,
    MaSP       INTEGER NOT NULL REFERENCES SANPHAM(MaSP),
    SoLuong    INTEGER NOT NULL CHECK (SoLuong > 0),
    DonGiaBan  REAL NOT NULL CHECK (DonGiaBan >= 0),
    ThanhTien  REAL NOT NULL
);

-- ---------- Phiếu dịch vụ, thu tiền & lịch sử trạng thái ----------
CREATE TABLE PHIEUDICHVU (
    SoPhieu             INTEGER PRIMARY KEY AUTOINCREMENT,
    NgayLap             TEXT NOT NULL,
    MaKH                INTEGER NOT NULL REFERENCES KHACHHANG(MaKH),
    MaND_Lap            INTEGER REFERENCES NGUOIDUNG(MaND),
    TiLeTraTruocApDung  REAL NOT NULL DEFAULT 50,
    TongTien            REAL NOT NULL DEFAULT 0,
    TongTraTruoc        REAL NOT NULL DEFAULT 0,
    TongConLai          REAL NOT NULL DEFAULT 0,
    TinhTrang           TEXT NOT NULL DEFAULT 'Chưa hoàn thành'
);

CREATE TABLE CT_PHIEUDICHVU (
    MaCT            INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieu         INTEGER NOT NULL REFERENCES PHIEUDICHVU(SoPhieu) ON DELETE CASCADE,
    MaLoaiDV        INTEGER NOT NULL REFERENCES LOAIDICHVU(MaLoaiDV),
    DonGiaDuocTinh  REAL NOT NULL,
    ChiPhiRieng     REAL NOT NULL DEFAULT 0,
    SoLuong         INTEGER NOT NULL CHECK (SoLuong > 0),
    ThanhTien       REAL NOT NULL,
    TraTruoc        REAL NOT NULL,
    ConLai          REAL NOT NULL,
    NgayGiao        TEXT NOT NULL,
    TinhTrang       TEXT NOT NULL DEFAULT 'Chưa giao',
    GhiChu          TEXT
);

CREATE TABLE THUTIENDICHVU (
    MaPhieuThu         INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieuDV          INTEGER NOT NULL REFERENCES PHIEUDICHVU(SoPhieu) ON DELETE CASCADE,
    NgayThu            TEXT NOT NULL,
    SoTienThu          REAL NOT NULL CHECK (SoTienThu > 0),
    LoaiThu            TEXT NOT NULL DEFAULT 'Thu trả trước',
    HinhThucThanhToan  TEXT NOT NULL DEFAULT 'Tiền mặt',
    MaND_Thu           INTEGER REFERENCES NGUOIDUNG(MaND),
    GhiChu             TEXT
);

CREATE TABLE LICHSUTINHTRANG (
    MaLichSu         INTEGER PRIMARY KEY AUTOINCREMENT,
    MaCT             INTEGER NOT NULL REFERENCES CT_PHIEUDICHVU(MaCT) ON DELETE CASCADE,
    MaND             INTEGER REFERENCES NGUOIDUNG(MaND),
    ThoiDiemCapNhat  TEXT NOT NULL,
    TinhTrangCu      TEXT NOT NULL,
    TinhTrangMoi     TEXT NOT NULL,
    LyDo             TEXT
);

-- ---------- Kiểm kê kho ----------
CREATE TABLE PHIEUKIEMKE (
    SoPhieuKK         INTEGER PRIMARY KEY AUTOINCREMENT,
    NgayKiemKe        TEXT NOT NULL,
    MaND_KiemKe       INTEGER REFERENCES NGUOIDUNG(MaND),
    TrangThaiXacNhan  TEXT NOT NULL DEFAULT 'Chờ xác nhận',
    MaND_XacNhan      INTEGER REFERENCES NGUOIDUNG(MaND),
    NgayXacNhan       TEXT,
    GhiChu            TEXT
);

CREATE TABLE CT_PHIEUKIEMKE (
    MaCTKK         INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieuKK      INTEGER NOT NULL REFERENCES PHIEUKIEMKE(SoPhieuKK) ON DELETE CASCADE,
    MaSP           INTEGER NOT NULL REFERENCES SANPHAM(MaSP),
    TonHeThong     INTEGER NOT NULL CHECK (TonHeThong >= 0),
    TonThucTe      INTEGER NOT NULL CHECK (TonThucTe >= 0),
    ChenhLech      INTEGER NOT NULL,
    LyDoChenhLech  TEXT,
    UNIQUE (SoPhieuKK, MaSP)
);

-- ---------- Kỳ kế toán & báo cáo chốt kỳ ----------
CREATE TABLE KYKETOAN (
    MaKy       INTEGER PRIMARY KEY AUTOINCREMENT,
    Thang      INTEGER NOT NULL CHECK (Thang BETWEEN 1 AND 12),
    Nam        INTEGER NOT NULL CHECK (Nam >= 2000),
    TrangThai  TEXT NOT NULL DEFAULT 'Đã chốt',
    NgayChot   TEXT,
    MaND_Chot  INTEGER REFERENCES NGUOIDUNG(MaND),
    GhiChu     TEXT,
    UNIQUE (Thang, Nam)
);

CREATE TABLE BAOCAOTONKHO_THANG (
    MaBCTon     INTEGER PRIMARY KEY AUTOINCREMENT,
    MaKy        INTEGER NOT NULL REFERENCES KYKETOAN(MaKy) ON DELETE CASCADE,
    MaSP        INTEGER NOT NULL REFERENCES SANPHAM(MaSP),
    TonDau      INTEGER NOT NULL CHECK (TonDau >= 0),
    SoLuongMua  INTEGER NOT NULL CHECK (SoLuongMua >= 0),
    SoLuongBan  INTEGER NOT NULL CHECK (SoLuongBan >= 0),
    TonCuoi     INTEGER NOT NULL CHECK (TonCuoi >= 0),
    UNIQUE (MaKy, MaSP)
);

CREATE TABLE BAOCAODOANHTHU_NGAY (
    MaBCDT_Ngay       INTEGER PRIMARY KEY AUTOINCREMENT,
    MaKy              INTEGER NOT NULL REFERENCES KYKETOAN(MaKy) ON DELETE CASCADE,
    Ngay              TEXT NOT NULL,
    SoGiaoDichBan     INTEGER NOT NULL DEFAULT 0,
    DoanhThuBan       REAL NOT NULL DEFAULT 0,
    SoGiaoDichDV      INTEGER NOT NULL DEFAULT 0,
    DoanhThuDV        REAL NOT NULL DEFAULT 0,
    TongDoanhThuNgay  REAL NOT NULL DEFAULT 0,
    UNIQUE (MaKy, Ngay)
);

-- ---------- Tham số & nhật ký thay đổi quy định ----------
CREATE TABLE THAMSO (
    TenThamSo  TEXT PRIMARY KEY,
    GiaTri     TEXT,
    MoTa       TEXT
);

CREATE TABLE NHATKYTHAYDOIQUYDINH (
    MaNhatKy         INTEGER PRIMARY KEY AUTOINCREMENT,
    LoaiQuyDinh      TEXT NOT NULL,
    MaDoiTuong       TEXT NOT NULL,
    GiaTriCu         TEXT,
    GiaTriMoi        TEXT NOT NULL,
    ThoiDiemCapNhat  TEXT NOT NULL,
    MaND_CapNhat     INTEGER REFERENCES NGUOIDUNG(MaND),
    GhiChu           TEXT
);

CREATE INDEX idx_pbh_ngay ON PHIEUBANHANG(NgayLap);
CREATE INDEX idx_pmh_ngay ON PHIEUMUAHANG(NgayLap);
CREATE INDEX idx_pdv_ngay ON PHIEUDICHVU(NgayLap);
CREATE INDEX idx_ttdv_ngay ON THUTIENDICHVU(NgayThu);

PRAGMA foreign_keys = ON;
