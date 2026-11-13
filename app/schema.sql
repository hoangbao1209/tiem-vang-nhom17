-- =============================================================
--  CSDL: Quản lý kinh doanh vàng bạc đá quý - Nhóm 17
--  (Đối chiếu với Chương 4 - Thiết kế dữ liệu, có thể đổi tên
--   bảng/cột cho khớp tài liệu của nhóm)
-- =============================================================
PRAGMA foreign_keys = OFF;

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
    TenSP       TEXT NOT NULL,
    MaLoaiSP    INTEGER NOT NULL REFERENCES LOAISANPHAM(MaLoaiSP),
    DonGiaMua   REAL NOT NULL DEFAULT 0 CHECK (DonGiaMua >= 0),   -- giá mua vào gần nhất
    SoLuongTon  INTEGER NOT NULL DEFAULT 0 CHECK (SoLuongTon >= 0),
    MoTa        TEXT,
    HinhAnh     TEXT,
    HienThi     INTEGER NOT NULL DEFAULT 1                       -- 1: hiện trên website
);

CREATE TABLE NHACUNGCAP (
    MaNCC        INTEGER PRIMARY KEY AUTOINCREMENT,
    TenNCC       TEXT NOT NULL,
    DiaChi       TEXT,
    SoDienThoai  TEXT
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
    PhanTramTraTruoc  REAL NOT NULL DEFAULT 50 CHECK (PhanTramTraTruoc BETWEEN 0 AND 100)
);

-- ---------- Phiếu mua hàng ----------
CREATE TABLE PHIEUMUAHANG (
    SoPhieu   INTEGER PRIMARY KEY AUTOINCREMENT,
    NgayLap   TEXT NOT NULL,
    MaNCC     INTEGER NOT NULL REFERENCES NHACUNGCAP(MaNCC),
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
    SoPhieu    INTEGER PRIMARY KEY AUTOINCREMENT,
    NgayLap    TEXT NOT NULL,
    MaKH       INTEGER NOT NULL REFERENCES KHACHHANG(MaKH),
    TongTien   REAL NOT NULL DEFAULT 0,
    Nguon      TEXT NOT NULL DEFAULT 'Tại quầy',   -- 'Tại quầy' | 'Online'
    TrangThai  TEXT NOT NULL DEFAULT 'Hoàn tất',   -- 'Chờ xử lý' | 'Hoàn tất' | 'Đã hủy'
    GhiChu     TEXT
);

CREATE TABLE CT_PHIEUBANHANG (
    MaCT       INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieu    INTEGER NOT NULL REFERENCES PHIEUBANHANG(SoPhieu) ON DELETE CASCADE,
    MaSP       INTEGER NOT NULL REFERENCES SANPHAM(MaSP),
    SoLuong    INTEGER NOT NULL CHECK (SoLuong > 0),
    DonGiaBan  REAL NOT NULL CHECK (DonGiaBan >= 0),
    ThanhTien  REAL NOT NULL
);

-- ---------- Phiếu dịch vụ ----------
CREATE TABLE PHIEUDICHVU (
    SoPhieu       INTEGER PRIMARY KEY AUTOINCREMENT,
    NgayLap       TEXT NOT NULL,
    MaKH          INTEGER NOT NULL REFERENCES KHACHHANG(MaKH),
    TongTien      REAL NOT NULL DEFAULT 0,
    TongTraTruoc  REAL NOT NULL DEFAULT 0,
    TongConLai    REAL NOT NULL DEFAULT 0,
    TinhTrang     TEXT NOT NULL DEFAULT 'Chưa hoàn thành'
);

CREATE TABLE CT_PHIEUDICHVU (
    MaCT            INTEGER PRIMARY KEY AUTOINCREMENT,
    SoPhieu         INTEGER NOT NULL REFERENCES PHIEUDICHVU(SoPhieu) ON DELETE CASCADE,
    MaLoaiDV        INTEGER NOT NULL REFERENCES LOAIDICHVU(MaLoaiDV),
    DonGiaDuocTinh  REAL NOT NULL,              -- = Đơn giá dịch vụ + Chi phí riêng
    ChiPhiRieng     REAL NOT NULL DEFAULT 0,
    SoLuong         INTEGER NOT NULL CHECK (SoLuong > 0),
    ThanhTien       REAL NOT NULL,
    TraTruoc        REAL NOT NULL,
    ConLai          REAL NOT NULL,
    NgayGiao        TEXT NOT NULL,
    TinhTrang       TEXT NOT NULL DEFAULT 'Chưa giao'
);

-- ---------- Hệ thống ----------
CREATE TABLE THAMSO (
    TenThamSo  TEXT PRIMARY KEY,
    GiaTri     TEXT,
    MoTa       TEXT
);

CREATE TABLE NGUOIDUNG (
    MaND         INTEGER PRIMARY KEY AUTOINCREMENT,
    TenDangNhap  TEXT NOT NULL UNIQUE,
    MatKhau      TEXT NOT NULL,
    HoTen        TEXT NOT NULL,
    VaiTro       TEXT NOT NULL DEFAULT 'nhanvien' CHECK (VaiTro IN ('admin', 'nhanvien'))
);

CREATE INDEX idx_pbh_ngay ON PHIEUBANHANG(NgayLap);
CREATE INDEX idx_pmh_ngay ON PHIEUMUAHANG(NgayLap);
CREATE INDEX idx_pdv_ngay ON PHIEUDICHVU(NgayLap);

PRAGMA foreign_keys = ON;
