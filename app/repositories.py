"""Tầng Truy cập Dữ liệu (Data Access Layer / Repositories).
Mọi câu lệnh SQL đều tập trung tại đây; tầng Presentation không bao giờ truy cập trực tiếp SQL.
"""

# ------------------------------------------------------------------ SINH MÃ TỰ ĐỘNG
def next_code(conn, table, pk_col, prefix, width=3):
    """Sinh mã dạng SP001, NCC001, DV001, NV001, PM202611001..."""
    row = conn.execute(
        f"SELECT {pk_col} FROM {table} WHERE {pk_col} LIKE ? ORDER BY {pk_col} DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    if row is None:
        return f"{prefix}{1:0{width}d}"
    suffix = row[0][len(prefix):]
    num = int(suffix) + 1 if suffix.isdigit() else 1
    return f"{prefix}{num:0{width}d}"


# ------------------------------------------------------------------ ĐƠN VỊ TÍNH & LOẠI SẢN PHẨM
def list_units(conn):
    return conn.execute(
        "SELECT d.*, (SELECT COUNT(*) FROM LOAISANPHAM l WHERE l.MaDVT = d.MaDVT) AS SoLoai "
        "FROM DONVITINH d ORDER BY d.MaDVT"
    ).fetchall()


def get_unit(conn, ma_dvt):
    return conn.execute("SELECT * FROM DONVITINH WHERE MaDVT = ?", (ma_dvt,)).fetchone()


def insert_unit(conn, ma_dvt, ten_dvt):
    conn.execute("INSERT INTO DONVITINH(MaDVT, TenDVT) VALUES (?, ?)", (ma_dvt, ten_dvt))


def update_unit(conn, ma_dvt, ten_dvt):
    conn.execute("UPDATE DONVITINH SET TenDVT = ? WHERE MaDVT = ?", (ten_dvt, ma_dvt))


def delete_unit(conn, ma_dvt):
    conn.execute("DELETE FROM DONVITINH WHERE MaDVT = ?", (ma_dvt,))


def count_categories_by_unit(conn, ma_dvt):
    return conn.execute("SELECT COUNT(*) FROM LOAISANPHAM WHERE MaDVT = ?", (ma_dvt,)).fetchone()[0]


def list_categories(conn):
    return conn.execute(
        "SELECT l.*, d.TenDVT, "
        "(SELECT COUNT(*) FROM SANPHAM sp WHERE sp.MaLoaiSP = l.MaLoaiSP) AS SoSP, "
        "(SELECT COUNT(*) FROM SANPHAM sp WHERE sp.MaLoaiSP = l.MaLoaiSP "
        " AND sp.HienThi = 1 AND sp.TinhTrang = 'Đang kinh doanh') AS SoSPDangBan, "
        "(SELECT sp.HinhAnh FROM SANPHAM sp WHERE sp.MaLoaiSP = l.MaLoaiSP "
        " AND sp.HienThi = 1 AND sp.TinhTrang = 'Đang kinh doanh' "
        " ORDER BY sp.MaSP LIMIT 1) AS HinhAnh "
        "FROM LOAISANPHAM l JOIN DONVITINH d ON d.MaDVT = l.MaDVT ORDER BY l.MaLoaiSP"
    ).fetchall()


def get_category(conn, ma_loai):
    return conn.execute(
        "SELECT l.*, d.TenDVT FROM LOAISANPHAM l JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE l.MaLoaiSP = ?",
        (ma_loai,),
    ).fetchone()


def insert_category(conn, ma_loai, ten_loai, ma_dvt, phan_tram):
    conn.execute(
        "INSERT INTO LOAISANPHAM(MaLoaiSP, TenLoaiSP, MaDVT, PhanTramLoiNhuan) VALUES (?, ?, ?, ?)",
        (ma_loai, ten_loai, ma_dvt, phan_tram),
    )


def update_category(conn, ma_loai, ten_loai, ma_dvt, phan_tram):
    conn.execute(
        "UPDATE LOAISANPHAM SET TenLoaiSP = ?, MaDVT = ?, PhanTramLoiNhuan = ? WHERE MaLoaiSP = ?",
        (ten_loai, ma_dvt, phan_tram, ma_loai),
    )


def delete_category(conn, ma_loai):
    conn.execute("DELETE FROM LOAISANPHAM WHERE MaLoaiSP = ?", (ma_loai,))


def count_products_by_category(conn, ma_loai):
    return conn.execute("SELECT COUNT(*) FROM SANPHAM WHERE MaLoaiSP = ?", (ma_loai,)).fetchone()[0]


# ------------------------------------------------------------------ SẢN PHẨM
PRODUCT_SELECT = """
SELECT sp.MaSP, sp.TenSP, sp.MaLoaiSP, sp.DonGiaMua, sp.SoLuongTon, sp.TinhTrang,
       sp.ChatLieu, sp.TuoiVang, sp.TrongLuong, sp.BaoHanh, sp.MoTa, sp.HinhAnh, sp.HienThi,
       l.TenLoaiSP, l.PhanTramLoiNhuan, d.MaDVT, d.TenDVT,
       ROUND(sp.DonGiaMua * (1.0 + l.PhanTramLoiNhuan), 0) AS DonGiaBan,
       CASE
         WHEN EXISTS (SELECT 1 FROM CT_PHIEUMUAHANG m WHERE m.MaSP = sp.MaSP)
           OR EXISTS (SELECT 1 FROM CT_PHIEUBANHANG b WHERE b.MaSP = sp.MaSP)
           OR EXISTS (SELECT 1 FROM CT_PHIEUKIEMKE k WHERE k.MaSP = sp.MaSP)
           OR EXISTS (SELECT 1 FROM BAOCAOTONKHO_THANG t WHERE t.MaSP = sp.MaSP)
         THEN 1 ELSE 0
       END AS DaPhatSinh
FROM SANPHAM sp
JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP
JOIN DONVITINH d   ON d.MaDVT = l.MaDVT
"""


def get_product(conn, ma_sp):
    return conn.execute(PRODUCT_SELECT + " WHERE sp.MaSP = ?", (ma_sp,)).fetchone()


def list_products(
    conn,
    q="",
    ma_loai="",
    tinh_trang="",
    only_visible=False,
    only_in_stock=False,
    stock_filter="",
    min_ton_warning=2,
    order_by="sp.MaSP ASC",
    limit=None,
):
    where, args = ["1=1"], []
    if q:
        where.append("(sp.MaSP LIKE ? OR sp.TenSP LIKE ? OR l.TenLoaiSP LIKE ? OR COALESCE(sp.ChatLieu, '') LIKE ?)")
        like = f"%{q}%"
        args += [like, like, like, like]
    if ma_loai:
        where.append("sp.MaLoaiSP = ?")
        args.append(ma_loai)
    if tinh_trang:
        where.append("sp.TinhTrang = ?")
        args.append(tinh_trang)
    if only_visible:
        where.append("sp.HienThi = 1 AND sp.TinhTrang = 'Đang kinh doanh'")
    if only_in_stock:
        where.append("sp.SoLuongTon > 0")
    if stock_filter == "het":
        where.append("sp.SoLuongTon <= 0")
    elif stock_filter == "sap_het":
        where.append("sp.SoLuongTon > 0 AND sp.SoLuongTon <= ?")
        args.append(min_ton_warning)
    elif stock_filter == "con":
        where.append("sp.SoLuongTon > 0")

    sql = PRODUCT_SELECT + " WHERE " + " AND ".join(where) + f" ORDER BY {order_by}"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql, args).fetchall()


def list_related_products(conn, ma_loai, exclude_ma_sp, limit=4):
    return conn.execute(
        PRODUCT_SELECT + " WHERE sp.HienThi = 1 AND sp.TinhTrang = 'Đang kinh doanh' "
        "AND sp.MaLoaiSP = ? AND sp.MaSP <> ? ORDER BY sp.MaSP ASC LIMIT ?",
        (ma_loai, exclude_ma_sp, limit),
    ).fetchall()


def insert_product(conn, data):
    conn.execute(
        "INSERT INTO SANPHAM(MaSP, TenSP, MaLoaiSP, DonGiaMua, SoLuongTon, TinhTrang, "
        "ChatLieu, TuoiVang, TrongLuong, BaoHanh, MoTa, HinhAnh, HienThi) "
        "VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data["MaSP"], data["TenSP"], data["MaLoaiSP"], data["DonGiaMua"],
            data["TinhTrang"], data["ChatLieu"], data["TuoiVang"], data["TrongLuong"],
            data["BaoHanh"], data["MoTa"], data["HinhAnh"], data["HienThi"],
        ),
    )


def update_product(conn, ma_sp, data):
    conn.execute(
        "UPDATE SANPHAM SET TenSP = ?, MaLoaiSP = ?, DonGiaMua = ?, TinhTrang = ?, "
        "ChatLieu = ?, TuoiVang = ?, TrongLuong = ?, BaoHanh = ?, MoTa = ?, "
        "HinhAnh = ?, HienThi = ? WHERE MaSP = ?",
        (
            data["TenSP"], data["MaLoaiSP"], data["DonGiaMua"], data["TinhTrang"],
            data["ChatLieu"], data["TuoiVang"], data["TrongLuong"], data["BaoHanh"],
            data["MoTa"], data["HinhAnh"], data["HienThi"], ma_sp,
        ),
    )


def update_product_status(conn, ma_sp, tinh_trang, hien_thi):
    conn.execute(
        "UPDATE SANPHAM SET TinhTrang = ?, HienThi = ? WHERE MaSP = ?",
        (tinh_trang, hien_thi, ma_sp),
    )


def delete_product(conn, ma_sp):
    conn.execute("DELETE FROM SANPHAM WHERE MaSP = ?", (ma_sp,))


def increase_stock_on_purchase(conn, ma_sp, so_luong, don_gia_mua):
    conn.execute(
        "UPDATE SANPHAM SET SoLuongTon = ROUND(SoLuongTon + ?, 3), DonGiaMua = ? WHERE MaSP = ?",
        (so_luong, don_gia_mua, ma_sp),
    )


def decrease_stock_atomic(conn, ma_sp, so_luong):
    cur = conn.execute(
        "UPDATE SANPHAM SET SoLuongTon = ROUND(SoLuongTon - ?, 3) "
        "WHERE MaSP = ? AND SoLuongTon + 1e-9 >= ?",
        (so_luong, ma_sp, so_luong),
    )
    return cur.rowcount == 1


def restore_stock(conn, ma_sp, so_luong):
    conn.execute(
        "UPDATE SANPHAM SET SoLuongTon = ROUND(SoLuongTon + ?, 3) WHERE MaSP = ?",
        (so_luong, ma_sp),
    )


# ------------------------------------------------------------------ NHÀ CUNG CẤP
def list_suppliers(conn, q="", tinh_trang=""):
    where, args = ["1=1"], []
    if q:
        where.append("(n.MaNCC LIKE ? OR n.TenNCC LIKE ? OR COALESCE(n.SoDienThoai, '') LIKE ? OR COALESCE(n.DiaChi, '') LIKE ?)")
        like = f"%{q}%"
        args += [like, like, like, like]
    if tinh_trang:
        where.append("n.TinhTrang = ?")
        args.append(tinh_trang)
    return conn.execute(
        "SELECT n.*, "
        "(SELECT COUNT(*) FROM PHIEUMUAHANG p WHERE p.MaNCC = n.MaNCC) AS SoPhieu, "
        "COALESCE((SELECT SUM(ROUND(c.SoLuong * c.DonGiaMua, 2)) "
        "          FROM CT_PHIEUMUAHANG c JOIN PHIEUMUAHANG p ON p.SoPhieuMua = c.SoPhieuMua "
        "          WHERE p.MaNCC = n.MaNCC), 0) AS TongMua "
        "FROM NHACUNGCAP n WHERE " + " AND ".join(where) + " ORDER BY n.MaNCC",
        args,
    ).fetchall()


def get_supplier(conn, ma_ncc):
    return conn.execute("SELECT * FROM NHACUNGCAP WHERE MaNCC = ?", (ma_ncc,)).fetchone()


def insert_supplier(conn, ma_ncc, ten, dia_chi, sdt, tinh_trang):
    conn.execute(
        "INSERT INTO NHACUNGCAP(MaNCC, TenNCC, DiaChi, SoDienThoai, TinhTrang) VALUES (?, ?, ?, ?, ?)",
        (ma_ncc, ten, dia_chi, sdt, tinh_trang),
    )


def update_supplier(conn, ma_ncc, ten, dia_chi, sdt, tinh_trang):
    conn.execute(
        "UPDATE NHACUNGCAP SET TenNCC = ?, DiaChi = ?, SoDienThoai = ?, TinhTrang = ? WHERE MaNCC = ?",
        (ten, dia_chi, sdt, tinh_trang, ma_ncc),
    )


def delete_supplier(conn, ma_ncc):
    conn.execute("DELETE FROM NHACUNGCAP WHERE MaNCC = ?", (ma_ncc,))


def count_purchases_by_supplier(conn, ma_ncc):
    return conn.execute("SELECT COUNT(*) FROM PHIEUMUAHANG WHERE MaNCC = ?", (ma_ncc,)).fetchone()[0]


# ------------------------------------------------------------------ DỊCH VỤ
def list_services(conn, q="", tinh_trang=""):
    where, args = ["1=1"], []
    if q:
        where.append("(d.MaDichVu LIKE ? OR d.TenDichVu LIKE ?)")
        args += [f"%{q}%", f"%{q}%"]
    if tinh_trang:
        where.append("d.TinhTrang = ?")
        args.append(tinh_trang)
    return conn.execute(
        "SELECT d.*, (SELECT COUNT(*) FROM CT_PHIEUDICHVU c WHERE c.MaDichVu = d.MaDichVu) AS SoLan "
        "FROM DICHVU d WHERE " + " AND ".join(where) + " ORDER BY d.MaDichVu",
        args,
    ).fetchall()


def get_service(conn, ma_dv):
    return conn.execute("SELECT * FROM DICHVU WHERE MaDichVu = ?", (ma_dv,)).fetchone()


def insert_service(conn, ma_dv, ten_dv, don_gia, tinh_trang):
    conn.execute(
        "INSERT INTO DICHVU(MaDichVu, TenDichVu, DonGiaCoBan, TinhTrang) VALUES (?, ?, ?, ?)",
        (ma_dv, ten_dv, don_gia, tinh_trang),
    )


def update_service(conn, ma_dv, ten_dv, don_gia, tinh_trang):
    conn.execute(
        "UPDATE DICHVU SET TenDichVu = ?, DonGiaCoBan = ?, TinhTrang = ? WHERE MaDichVu = ?",
        (ten_dv, don_gia, tinh_trang, ma_dv),
    )


def delete_service(conn, ma_dv):
    conn.execute("DELETE FROM DICHVU WHERE MaDichVu = ?", (ma_dv,))


def count_service_usage(conn, ma_dv):
    return conn.execute("SELECT COUNT(*) FROM CT_PHIEUDICHVU WHERE MaDichVu = ?", (ma_dv,)).fetchone()[0]


# ------------------------------------------------------------------ NGƯỜI DÙNG & THAM SỐ & NHẬT KÝ
def get_user_by_id(conn, ma_nv):
    return conn.execute("SELECT * FROM NGUOIDUNG WHERE MaNV = ?", (ma_nv,)).fetchone()


def get_user_by_username(conn, username):
    return conn.execute("SELECT * FROM NGUOIDUNG WHERE TenDangNhap = ?", (username,)).fetchone()


def list_users(conn):
    return conn.execute(
        "SELECT u.MaNV, u.TenNV, u.VaiTro, u.TenDangNhap, u.CoQuyenChuyenNguoc, u.TinhTrang, "
        "CASE WHEN EXISTS (SELECT 1 FROM PHIEUMUAHANG p WHERE p.MaNV_Lap = u.MaNV) "
        "  OR EXISTS (SELECT 1 FROM PHIEUBANHANG p WHERE p.MaNV_Lap = u.MaNV) "
        "  OR EXISTS (SELECT 1 FROM PHIEUDICHVU p WHERE p.MaNV_Lap = u.MaNV) "
        "  OR EXISTS (SELECT 1 FROM THUTIENDICHVU t WHERE t.MaNV_Thu = u.MaNV) "
        "  OR EXISTS (SELECT 1 FROM LICHSUTINHTRANG l WHERE l.MaNV = u.MaNV) "
        "  OR EXISTS (SELECT 1 FROM PHIEUKIEMKE k WHERE k.MaNV_KiemKe = u.MaNV OR k.MaNV_XacNhan = u.MaNV) "
        "  OR EXISTS (SELECT 1 FROM KYKETOAN ky WHERE ky.MaNV_Chot = u.MaNV) "
        "  OR EXISTS (SELECT 1 FROM NHATKYTHAYDOIQUYDINH n WHERE n.MaNV_CapNhat = u.MaNV) "
        "THEN 1 ELSE 0 END AS DaPhatSinh "
        "FROM NGUOIDUNG u ORDER BY u.MaNV"
    ).fetchall()


def insert_user(conn, ma_nv, ten_nv, vai_tro, username, pw_hash, co_quyen):
    conn.execute(
        "INSERT INTO NGUOIDUNG(MaNV, TenNV, VaiTro, TenDangNhap, MatKhau, CoQuyenChuyenNguoc, TinhTrang) "
        "VALUES (?, ?, ?, ?, ?, ?, 'Đang làm việc')",
        (ma_nv, ten_nv, vai_tro, username, pw_hash, co_quyen),
    )


def update_user_password(conn, ma_nv, pw_hash):
    conn.execute("UPDATE NGUOIDUNG SET MatKhau = ? WHERE MaNV = ?", (pw_hash, ma_nv))


def update_user_revert_perm(conn, ma_nv, val):
    conn.execute("UPDATE NGUOIDUNG SET CoQuyenChuyenNguoc = ? WHERE MaNV = ?", (val, ma_nv))


def update_user_status(conn, ma_nv, tinh_trang):
    conn.execute("UPDATE NGUOIDUNG SET TinhTrang = ? WHERE MaNV = ?", (tinh_trang, ma_nv))


def delete_user(conn, ma_nv):
    conn.execute("DELETE FROM NGUOIDUNG WHERE MaNV = ?", (ma_nv,))


def get_tham_so(conn):
    row = conn.execute("SELECT * FROM THAMSO WHERE MaThamSo = 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO THAMSO(MaThamSo, TiLeTraTruoc) VALUES (1, 0.5000)")
        row = conn.execute("SELECT * FROM THAMSO WHERE MaThamSo = 1").fetchone()
    return row


def update_ti_le_tra_truoc(conn, ti_le_decimal):
    conn.execute("UPDATE THAMSO SET TiLeTraTruoc = ? WHERE MaThamSo = 1", (ti_le_decimal,))


def insert_rule_log(conn, loai, ma_doi_tuong, gia_tri_cu, gia_tri_moi, thoi_diem, ma_nv, ghi_chu):
    conn.execute(
        "INSERT INTO NHATKYTHAYDOIQUYDINH(LoaiQuyDinh, MaDoiTuong, GiaTriCu, GiaTriMoi, "
        "ThoiDiemCapNhat, MaNV_CapNhat, GhiChu) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (loai, ma_doi_tuong, gia_tri_cu, gia_tri_moi, thoi_diem, ma_nv, ghi_chu),
    )


def list_rule_logs(conn, limit=30):
    return conn.execute(
        "SELECT l.*, u.TenNV AS NguoiCapNhat FROM NHATKYTHAYDOIQUYDINH l "
        "LEFT JOIN NGUOIDUNG u ON u.MaNV = l.MaNV_CapNhat "
        "ORDER BY l.MaNhatKy DESC LIMIT ?",
        (limit,),
    ).fetchall()


# ------------------------------------------------------------------ PHIẾU MUA HÀNG
def insert_purchase(conn, so_phieu, ngay_lap, ma_ncc, ma_nv, ghi_chu):
    conn.execute(
        "INSERT INTO PHIEUMUAHANG(SoPhieuMua, NgayLap, MaNCC, MaNV_Lap, GhiChu) VALUES (?, ?, ?, ?, ?)",
        (so_phieu, ngay_lap, ma_ncc, ma_nv, ghi_chu),
    )


def insert_purchase_line(conn, so_phieu, so_dong, ma_sp, so_luong, don_gia):
    conn.execute(
        "INSERT INTO CT_PHIEUMUAHANG(SoPhieuMua, SoDong, MaSP, SoLuong, DonGiaMua) "
        "VALUES (?, ?, ?, ?, ?)",
        (so_phieu, so_dong, ma_sp, so_luong, don_gia),
    )


def list_purchases(conn, q="", ma_ncc="", tu_ngay="", den_ngay=""):
    where, args = ["1=1"], []
    if q:
        where.append("(p.SoPhieuMua LIKE ? OR n.MaNCC LIKE ? OR n.TenNCC LIKE ?)")
        like = f"%{q}%"
        args += [like, like, like]
    if ma_ncc:
        where.append("p.MaNCC = ?")
        args.append(ma_ncc)
    if tu_ngay:
        where.append("substr(p.NgayLap, 1, 10) >= ?")
        args.append(tu_ngay)
    if den_ngay:
        where.append("substr(p.NgayLap, 1, 10) <= ?")
        args.append(den_ngay)
    return conn.execute(
        "SELECT p.*, n.TenNCC, n.SoDienThoai, u.TenNV AS NguoiLap, "
        "(SELECT COUNT(*) FROM CT_PHIEUMUAHANG c WHERE c.SoPhieuMua = p.SoPhieuMua) AS SoMatHang, "
        "COALESCE((SELECT SUM(ROUND(c.SoLuong * c.DonGiaMua, 2)) "
        "          FROM CT_PHIEUMUAHANG c WHERE c.SoPhieuMua = p.SoPhieuMua), 0) AS TongTien "
        "FROM PHIEUMUAHANG p "
        "JOIN NHACUNGCAP n ON n.MaNCC = p.MaNCC "
        "LEFT JOIN NGUOIDUNG u ON u.MaNV = p.MaNV_Lap "
        "WHERE " + " AND ".join(where) + " ORDER BY p.NgayLap DESC, p.SoPhieuMua DESC",
        args,
    ).fetchall()


def get_purchase(conn, so_phieu):
    p = conn.execute(
        "SELECT p.*, n.TenNCC, n.DiaChi, n.SoDienThoai, u.TenNV AS NguoiLap, "
        "COALESCE((SELECT SUM(ROUND(c.SoLuong * c.DonGiaMua, 2)) "
        "          FROM CT_PHIEUMUAHANG c WHERE c.SoPhieuMua = p.SoPhieuMua), 0) AS TongTien "
        "FROM PHIEUMUAHANG p "
        "JOIN NHACUNGCAP n ON n.MaNCC = p.MaNCC "
        "LEFT JOIN NGUOIDUNG u ON u.MaNV = p.MaNV_Lap "
        "WHERE p.SoPhieuMua = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, []
    lines = conn.execute(
        "SELECT ct.*, ROUND(ct.SoLuong * ct.DonGiaMua, 2) AS ThanhTien, "
        "sp.TenSP, l.TenLoaiSP, d.TenDVT "
        "FROM CT_PHIEUMUAHANG ct "
        "JOIN SANPHAM sp ON sp.MaSP = ct.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE ct.SoPhieuMua = ? ORDER BY ct.SoDong",
        (so_phieu,),
    ).fetchall()
    return p, lines


# ------------------------------------------------------------------ PHIẾU BÁN HÀNG
def insert_sale(conn, data):
    conn.execute(
        "INSERT INTO PHIEUBANHANG(SoPhieuBan, NgayLap, TenKhachHang, MaNV_Lap, "
        "PhuongThucThanhToan, TongTien, SoTienNhan, SoDienThoai, DiaChi, Nguon, TrangThai, GhiChu) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data["SoPhieuBan"], data["NgayLap"], data["TenKhachHang"], data["MaNV_Lap"],
            data["PhuongThucThanhToan"], data["TongTien"], data["SoTienNhan"],
            data["SoDienThoai"], data["DiaChi"], data["Nguon"], data["TrangThai"], data["GhiChu"],
        ),
    )


def insert_sale_line(conn, so_phieu, so_dong, ma_sp, so_luong, don_gia_ban):
    conn.execute(
        "INSERT INTO CT_PHIEUBANHANG(SoPhieuBan, SoDong, MaSP, SoLuong, DonGiaBan) "
        "VALUES (?, ?, ?, ?, ?)",
        (so_phieu, so_dong, ma_sp, so_luong, don_gia_ban),
    )


def list_sales(conn, q="", nguon="", trang_thai="", pttt="", tu_ngay="", den_ngay="", limit=None):
    where, args = ["1=1"], []
    if q:
        where.append("(p.SoPhieuBan LIKE ? OR COALESCE(p.TenKhachHang, '') LIKE ? OR COALESCE(p.SoDienThoai, '') LIKE ?)")
        like = f"%{q}%"
        args += [like, like, like]
    if nguon:
        where.append("p.Nguon = ?")
        args.append(nguon)
    if trang_thai:
        where.append("p.TrangThai = ?")
        args.append(trang_thai)
    if pttt:
        where.append("p.PhuongThucThanhToan = ?")
        args.append(pttt)
    if tu_ngay:
        where.append("substr(p.NgayLap, 1, 10) >= ?")
        args.append(tu_ngay)
    if den_ngay:
        where.append("substr(p.NgayLap, 1, 10) <= ?")
        args.append(den_ngay)
    sql = (
        "SELECT p.*, CASE WHEN p.SoTienNhan > p.TongTien THEN ROUND(p.SoTienNhan - p.TongTien, 2) ELSE 0 END AS TienThua, "
        "u.TenNV AS NguoiLap, "
        "(SELECT COUNT(*) FROM CT_PHIEUBANHANG c WHERE c.SoPhieuBan = p.SoPhieuBan) AS SoMatHang "
        "FROM PHIEUBANHANG p "
        "LEFT JOIN NGUOIDUNG u ON u.MaNV = p.MaNV_Lap "
        "WHERE " + " AND ".join(where) + " ORDER BY p.NgayLap DESC, p.SoPhieuBan DESC"
    )
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql, args).fetchall()


def get_sale(conn, so_phieu):
    p = conn.execute(
        "SELECT p.*, CASE WHEN p.SoTienNhan > p.TongTien THEN ROUND(p.SoTienNhan - p.TongTien, 2) ELSE 0 END AS TienThua, "
        "u.TenNV AS NguoiLap "
        "FROM PHIEUBANHANG p "
        "LEFT JOIN NGUOIDUNG u ON u.MaNV = p.MaNV_Lap "
        "WHERE p.SoPhieuBan = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, []
    lines = conn.execute(
        "SELECT ct.*, ROUND(ct.SoLuong * ct.DonGiaBan, 2) AS ThanhTien, "
        "sp.TenSP, sp.HinhAnh, l.TenLoaiSP, d.TenDVT "
        "FROM CT_PHIEUBANHANG ct "
        "JOIN SANPHAM sp ON sp.MaSP = ct.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE ct.SoPhieuBan = ? ORDER BY ct.SoDong",
        (so_phieu,),
    ).fetchall()
    return p, lines


def update_sale_complete(conn, so_phieu, ma_nv):
    conn.execute(
        "UPDATE PHIEUBANHANG SET TrangThai = 'Hoàn tất', SoTienNhan = TongTien, "
        "MaNV_Lap = COALESCE(MaNV_Lap, ?) WHERE SoPhieuBan = ?",
        (ma_nv, so_phieu),
    )


def update_sale_cancel(conn, so_phieu):
    conn.execute("UPDATE PHIEUBANHANG SET TrangThai = 'Đã hủy' WHERE SoPhieuBan = ?", (so_phieu,))


# ------------------------------------------------------------------ PHIẾU DỊCH VỤ, THU TIỀN & LỊCH SỬ
def insert_service_voucher(conn, so_phieu, ngay_lap, ten_kh, sdt, ma_nv, ti_le):
    conn.execute(
        "INSERT INTO PHIEUDICHVU(SoPhieuDV, NgayLap, TenKhachHang, SoDienThoai, MaNV_Lap, TiLeTraTruocApDung) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (so_phieu, ngay_lap, ten_kh, sdt, ma_nv, ti_le),
    )


def insert_service_line(conn, so_phieu, so_dong, ma_dv, dg_dv, chi_phi, sl, tra_truoc, ngay_giao, ghi_chu=None):
    conn.execute(
        "INSERT INTO CT_PHIEUDICHVU(SoPhieuDV, SoDong, MaDichVu, DonGiaDichVu, ChiPhiRieng, "
        "SoLuong, TraTruoc, NgayGiaoDuKien, TinhTrang, GhiChu) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Chưa giao', ?)",
        (so_phieu, so_dong, ma_dv, dg_dv, chi_phi, sl, tra_truoc, ngay_giao, ghi_chu),
    )


def insert_service_receipt(conn, ma_thu, so_phieu, ngay_thu, so_tien, loai_thu, hinh_thuc, ma_nv, ghi_chu):
    conn.execute(
        "INSERT INTO THUTIENDICHVU(MaPhieuThuDV, SoPhieuDV, NgayThu, SoTienThu, LoaiThu, "
        "HinhThucThanhToan, MaNV_Thu, GhiChu) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (ma_thu, so_phieu, ngay_thu, so_tien, loai_thu, hinh_thuc, ma_nv, ghi_chu),
    )


def list_service_vouchers(conn, q="", tinh_trang="", tu_ngay="", den_ngay="", limit=None):
    base_sql = """
    SELECT p.*, u.TenNV AS NguoiLap,
      (SELECT COUNT(*) FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV) AS SoDV,
      COALESCE((SELECT SUM(c.SoLuong * (c.DonGiaDichVu + c.ChiPhiRieng))
                FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV), 0) AS TongTien,
      COALESCE((SELECT SUM(c.TraTruoc)
                FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV), 0) AS TongTraTruoc,
      COALESCE((SELECT SUM(t.SoTienThu)
                FROM THUTIENDICHVU t WHERE t.SoPhieuDV = p.SoPhieuDV), 0) AS DaThu,
      CASE
        WHEN (SELECT COUNT(*) FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV) > 0
         AND NOT EXISTS (SELECT 1 FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV AND c.TinhTrang <> 'Đã giao')
        THEN 'Hoàn thành'
        ELSE 'Chưa hoàn thành'
      END AS TinhTrang
    FROM PHIEUDICHVU p
    LEFT JOIN NGUOIDUNG u ON u.MaNV = p.MaNV_Lap
    """
    where, args = ["1=1"], []
    if q:
        where.append("(p.SoPhieuDV LIKE ? OR p.TenKhachHang LIKE ? OR p.SoDienThoai LIKE ?)")
        like = f"%{q}%"
        args += [like, like, like]
    if tu_ngay:
        where.append("substr(p.NgayLap, 1, 10) >= ?")
        args.append(tu_ngay)
    if den_ngay:
        where.append("substr(p.NgayLap, 1, 10) <= ?")
        args.append(den_ngay)

    sql = f"SELECT *, (TongTien - TongTraTruoc) AS TongConLai FROM ({base_sql} WHERE " + " AND ".join(where) + ") sub"
    if tinh_trang:
        sql += " WHERE sub.TinhTrang = ?"
        args.append(tinh_trang)
    sql += " ORDER BY sub.NgayLap DESC, sub.SoPhieuDV DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql, args).fetchall()


def get_service_voucher(conn, so_phieu):
    p = conn.execute(
        "SELECT p.*, u.TenNV AS NguoiLap, "
        "COALESCE((SELECT SUM(c.SoLuong * (c.DonGiaDichVu + c.ChiPhiRieng)) "
        "          FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV), 0) AS TongTien, "
        "COALESCE((SELECT SUM(c.TraTruoc) FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV), 0) AS TongTraTruoc, "
        "COALESCE((SELECT SUM(t.SoTienThu) FROM THUTIENDICHVU t WHERE t.SoPhieuDV = p.SoPhieuDV), 0) AS DaThu, "
        "CASE "
        "  WHEN (SELECT COUNT(*) FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV) > 0 "
        "   AND NOT EXISTS (SELECT 1 FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV AND c.TinhTrang <> 'Đã giao') "
        "  THEN 'Hoàn thành' ELSE 'Chưa hoàn thành' "
        "END AS TinhTrang "
        "FROM PHIEUDICHVU p LEFT JOIN NGUOIDUNG u ON u.MaNV = p.MaNV_Lap "
        "WHERE p.SoPhieuDV = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, [], [], []
    lines = conn.execute(
        "SELECT ct.*, d.TenDichVu, "
        "(ct.DonGiaDichVu + ct.ChiPhiRieng) AS DonGiaDuocTinh, "
        "(ct.SoLuong * (ct.DonGiaDichVu + ct.ChiPhiRieng)) AS ThanhTien, "
        "(ct.SoLuong * (ct.DonGiaDichVu + ct.ChiPhiRieng) - ct.TraTruoc) AS ConLai "
        "FROM CT_PHIEUDICHVU ct JOIN DICHVU d ON d.MaDichVu = ct.MaDichVu "
        "WHERE ct.SoPhieuDV = ? ORDER BY ct.SoDong",
        (so_phieu,),
    ).fetchall()
    receipts = conn.execute(
        "SELECT t.*, u.TenNV AS NguoiThu FROM THUTIENDICHVU t "
        "LEFT JOIN NGUOIDUNG u ON u.MaNV = t.MaNV_Thu "
        "WHERE t.SoPhieuDV = ? ORDER BY t.NgayThu, t.MaPhieuThuDV",
        (so_phieu,),
    ).fetchall()
    logs = conn.execute(
        "SELECT h.*, d.TenDichVu, u.TenNV AS NguoiThucHien "
        "FROM LICHSUTINHTRANG h "
        "JOIN CT_PHIEUDICHVU ct ON ct.MaChiTiet = h.MaChiTiet "
        "JOIN DICHVU d ON d.MaDichVu = ct.MaDichVu "
        "LEFT JOIN NGUOIDUNG u ON u.MaNV = h.MaNV "
        "WHERE ct.SoPhieuDV = ? ORDER BY h.MaLichSu DESC",
        (so_phieu,),
    ).fetchall()
    return p, lines, receipts, logs


def get_service_line(conn, ma_chi_tiet):
    return conn.execute("SELECT * FROM CT_PHIEUDICHVU WHERE MaChiTiet = ?", (ma_chi_tiet,)).fetchone()


def update_service_line_status(conn, ma_chi_tiet, tinh_trang_moi, ghi_chu=None):
    if ghi_chu is not None:
        conn.execute(
            "UPDATE CT_PHIEUDICHVU SET TinhTrang = ?, GhiChu = ? WHERE MaChiTiet = ?",
            (tinh_trang_moi, ghi_chu, ma_chi_tiet),
        )
    else:
        conn.execute(
            "UPDATE CT_PHIEUDICHVU SET TinhTrang = ? WHERE MaChiTiet = ?",
            (tinh_trang_moi, ma_chi_tiet),
        )


def insert_status_history(conn, ma_chi_tiet, ma_nv, thoi_diem, cu, moi, ly_do):
    conn.execute(
        "INSERT INTO LICHSUTINHTRANG(MaChiTiet, MaNV, ThoiDiemCapNhat, TinhTrangCu, TinhTrangMoi, LyDo) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ma_chi_tiet, ma_nv, thoi_diem, cu, moi, ly_do),
    )


def list_service_status_items(conn, q="", tinh_trang=""):
    where, args = ["1=1"], []
    if tinh_trang:
        where.append("ct.TinhTrang = ?")
        args.append(tinh_trang)
    if q:
        where.append("(p.SoPhieuDV LIKE ? OR p.TenKhachHang LIKE ? OR p.SoDienThoai LIKE ? OR d.TenDichVu LIKE ?)")
        like = f"%{q}%"
        args += [like, like, like, like]
    return conn.execute(
        "SELECT ct.*, p.NgayLap, p.TenKhachHang, p.SoDienThoai, d.TenDichVu, "
        "(ct.SoLuong * (ct.DonGiaDichVu + ct.ChiPhiRieng)) AS ThanhTien, "
        "(ct.SoLuong * (ct.DonGiaDichVu + ct.ChiPhiRieng) - ct.TraTruoc) AS ConLai "
        "FROM CT_PHIEUDICHVU ct "
        "JOIN PHIEUDICHVU p ON p.SoPhieuDV = ct.SoPhieuDV "
        "JOIN DICHVU d ON d.MaDichVu = ct.MaDichVu "
        "WHERE " + " AND ".join(where) + " ORDER BY ct.NgayGiaoDuKien ASC, ct.MaChiTiet DESC",
        args,
    ).fetchall()


# ------------------------------------------------------------------ KIỂM KÊ KHO
def insert_stocktake(conn, so_phieu, ngay_kk, ma_nv, ghi_chu):
    conn.execute(
        "INSERT INTO PHIEUKIEMKE(SoPhieuKK, NgayKiemKe, MaNV_KiemKe, TrangThaiXacNhan, GhiChu) "
        "VALUES (?, ?, ?, 'Chờ xác nhận', ?)",
        (so_phieu, ngay_kk, ma_nv, ghi_chu),
    )


def insert_stocktake_line(conn, so_phieu, ma_sp, ton_ht, ton_tt, chenh_lech, ly_do):
    conn.execute(
        "INSERT INTO CT_PHIEUKIEMKE(SoPhieuKK, MaSP, TonHeThong, TonThucTe, ChenhLech, LyDoChenhLech) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (so_phieu, ma_sp, ton_ht, ton_tt, chenh_lech, ly_do),
    )


def list_stocktakes(conn):
    return conn.execute(
        "SELECT p.*, u1.TenNV AS NguoiKiemKe, u2.TenNV AS NguoiXacNhan, "
        "(SELECT COUNT(*) FROM CT_PHIEUKIEMKE c WHERE c.SoPhieuKK = p.SoPhieuKK) AS SoSP, "
        "(SELECT COUNT(*) FROM CT_PHIEUKIEMKE c WHERE c.SoPhieuKK = p.SoPhieuKK AND ABS(c.ChenhLech) > 1e-9) AS SoChenhLech "
        "FROM PHIEUKIEMKE p "
        "LEFT JOIN NGUOIDUNG u1 ON u1.MaNV = p.MaNV_KiemKe "
        "LEFT JOIN NGUOIDUNG u2 ON u2.MaNV = p.MaNV_XacNhan "
        "ORDER BY p.NgayKiemKe DESC, p.SoPhieuKK DESC"
    ).fetchall()


def get_stocktake(conn, so_phieu):
    p = conn.execute(
        "SELECT p.*, u1.TenNV AS NguoiKiemKe, u2.TenNV AS NguoiXacNhan "
        "FROM PHIEUKIEMKE p "
        "LEFT JOIN NGUOIDUNG u1 ON u1.MaNV = p.MaNV_KiemKe "
        "LEFT JOIN NGUOIDUNG u2 ON u2.MaNV = p.MaNV_XacNhan "
        "WHERE p.SoPhieuKK = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, []
    lines = conn.execute(
        "SELECT ct.*, sp.TenSP, l.TenLoaiSP, d.TenDVT "
        "FROM CT_PHIEUKIEMKE ct "
        "JOIN SANPHAM sp ON sp.MaSP = ct.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE ct.SoPhieuKK = ? ORDER BY sp.MaSP",
        (so_phieu,),
    ).fetchall()
    return p, lines


def confirm_stocktake(conn, so_phieu, ma_nv_xac_nhan, ngay_xac_nhan):
    conn.execute(
        "UPDATE PHIEUKIEMKE SET TrangThaiXacNhan = 'Đã xác nhận', MaNV_XacNhan = ?, NgayXacNhan = ? "
        "WHERE SoPhieuKK = ?",
        (ma_nv_xac_nhan, ngay_xac_nhan, so_phieu),
    )


# ------------------------------------------------------------------ KỲ KẾ TOÁN & BÁO CÁO
def get_period(conn, thang, nam):
    return conn.execute(
        "SELECT k.*, u.TenNV AS NguoiChot FROM KYKETOAN k "
        "LEFT JOIN NGUOIDUNG u ON u.MaNV = k.MaNV_Chot "
        "WHERE k.Thang = ? AND k.Nam = ?",
        (thang, nam),
    ).fetchone()


def list_periods(conn):
    return conn.execute(
        "SELECT k.*, u.TenNV AS NguoiChot FROM KYKETOAN k "
        "LEFT JOIN NGUOIDUNG u ON u.MaNV = k.MaNV_Chot "
        "ORDER BY k.Nam DESC, k.Thang DESC"
    ).fetchall()


def get_closed_inventory_rows(conn, ma_ky):
    return conn.execute(
        "SELECT b.MaSP, sp.TenSP, l.TenLoaiSP, d.TenDVT, "
        "b.TonDau, b.SoLuongMua AS MuaVao, b.SoLuongBan AS BanRa, b.TonCuoi "
        "FROM BAOCAOTONKHO_THANG b "
        "JOIN SANPHAM sp ON sp.MaSP = b.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE b.MaKy = ? ORDER BY l.MaLoaiSP, sp.MaSP",
        (ma_ky,),
    ).fetchall()


def query_live_inventory_movements(conn, start_iso, end_iso):
    sql = """
    SELECT sp.MaSP, sp.TenSP, sp.SoLuongTon, l.TenLoaiSP, d.TenDVT,
      COALESCE((SELECT SUM(c.SoLuong) FROM CT_PHIEUMUAHANG c JOIN PHIEUMUAHANG p ON p.SoPhieuMua = c.SoPhieuMua
                WHERE c.MaSP = sp.MaSP AND substr(p.NgayLap, 1, 10) >= :s AND substr(p.NgayLap, 1, 10) < :e), 0) AS MuaTrong,
      COALESCE((SELECT SUM(c.SoLuong) FROM CT_PHIEUMUAHANG c JOIN PHIEUMUAHANG p ON p.SoPhieuMua = c.SoPhieuMua
                WHERE c.MaSP = sp.MaSP AND substr(p.NgayLap, 1, 10) >= :e), 0) AS MuaSau,
      COALESCE((SELECT SUM(c.SoLuong) FROM CT_PHIEUBANHANG c JOIN PHIEUBANHANG p ON p.SoPhieuBan = c.SoPhieuBan
                WHERE c.MaSP = sp.MaSP AND p.TrangThai <> 'Đã hủy'
                  AND substr(p.NgayLap, 1, 10) >= :s AND substr(p.NgayLap, 1, 10) < :e), 0) AS BanTrong,
      COALESCE((SELECT SUM(c.SoLuong) FROM CT_PHIEUBANHANG c JOIN PHIEUBANHANG p ON p.SoPhieuBan = c.SoPhieuBan
                WHERE c.MaSP = sp.MaSP AND p.TrangThai <> 'Đã hủy'
                  AND substr(p.NgayLap, 1, 10) >= :e), 0) AS BanSau
    FROM SANPHAM sp
    JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP
    JOIN DONVITINH d ON d.MaDVT = l.MaDVT
    ORDER BY l.MaLoaiSP, sp.MaSP
    """
    return conn.execute(sql, {"s": start_iso, "e": end_iso}).fetchall()


def get_closed_revenue_rows(conn, ma_ky):
    return conn.execute(
        "SELECT * FROM BAOCAODOANHTHU_NGAY WHERE MaKy = ? ORDER BY Ngay ASC", (ma_ky,)
    ).fetchall()


def query_live_sales_by_day(conn, start_iso, end_iso):
    return conn.execute(
        "SELECT substr(NgayLap, 1, 10) AS Ngay, COUNT(*) AS SoGD, SUM(TongTien) AS DoanhThu "
        "FROM PHIEUBANHANG WHERE TrangThai <> 'Đã hủy' "
        "AND substr(NgayLap, 1, 10) >= ? AND substr(NgayLap, 1, 10) < ? "
        "GROUP BY Ngay ORDER BY Ngay ASC",
        (start_iso, end_iso),
    ).fetchall()


def query_live_service_revenue_by_day(conn, start_iso, end_iso):
    return conn.execute(
        "SELECT substr(NgayThu, 1, 10) AS Ngay, COUNT(*) AS SoGD, SUM(SoTienThu) AS DoanhThu "
        "FROM THUTIENDICHVU WHERE substr(NgayThu, 1, 10) >= ? AND substr(NgayThu, 1, 10) < ? "
        "GROUP BY Ngay ORDER BY Ngay ASC",
        (start_iso, end_iso),
    ).fetchall()


def query_top_selling_products(conn, start_iso, end_iso, limit=5):
    return conn.execute(
        "SELECT sp.MaSP, sp.TenSP, d.TenDVT, SUM(c.SoLuong) AS SoLuong, "
        "SUM(ROUND(c.SoLuong * c.DonGiaBan, 2)) AS DoanhThu "
        "FROM CT_PHIEUBANHANG c "
        "JOIN PHIEUBANHANG p ON p.SoPhieuBan = c.SoPhieuBan "
        "JOIN SANPHAM sp ON sp.MaSP = c.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE p.TrangThai <> 'Đã hủy' AND substr(p.NgayLap, 1, 10) >= ? AND substr(p.NgayLap, 1, 10) < ? "
        "GROUP BY sp.MaSP ORDER BY DoanhThu DESC LIMIT ?",
        (start_iso, end_iso, limit),
    ).fetchall()


def insert_period_closed(conn, thang, nam, ngay_chot, ma_nv, ghi_chu=None):
    cur = conn.execute(
        "INSERT INTO KYKETOAN(Thang, Nam, TrangThai, NgayChot, MaNV_Chot, GhiChu) "
        "VALUES (?, ?, 'Đã chốt', ?, ?, ?)",
        (thang, nam, ngay_chot, ma_nv, ghi_chu),
    )
    return cur.lastrowid


def lock_period(conn, ma_ky, ngay_khoa):
    conn.execute(
        "UPDATE KYKETOAN SET TrangThai = 'Đã khóa', NgayKhoa = ? WHERE MaKy = ?",
        (ngay_khoa, ma_ky),
    )


def insert_inventory_snapshot(conn, ma_ky, ma_sp, ton_dau, mua, ban, ton_cuoi):
    conn.execute(
        "INSERT INTO BAOCAOTONKHO_THANG(MaKy, MaSP, TonDau, SoLuongMua, SoLuongBan, TonCuoi) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ma_ky, ma_sp, ton_dau, mua, ban, ton_cuoi),
    )


def insert_revenue_snapshot(conn, ma_ky, ngay, so_ban, dt_ban, so_dv, dt_dv):
    conn.execute(
        "INSERT INTO BAOCAODOANHTHU_NGAY(MaKy, Ngay, SoGiaoDichBan, DoanhThuBan, "
        "SoGiaoDichDV, DoanhThuDV, TongDoanhThuNgay) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ma_ky, ngay, so_ban, dt_ban, so_dv, dt_dv, dt_ban + dt_dv),
    )


# ------------------------------------------------------------------ TỔNG QUAN & KHÁCH HÀNG TỔNG HỢP
def query_dashboard_stats(conn, ym):
    dt_ban = conn.execute(
        "SELECT COALESCE(SUM(TongTien), 0) FROM PHIEUBANHANG "
        "WHERE TrangThai <> 'Đã hủy' AND substr(NgayLap, 1, 7) = ?",
        (ym,),
    ).fetchone()[0]
    dt_dv = conn.execute(
        "SELECT COALESCE(SUM(SoTienThu), 0) FROM THUTIENDICHVU WHERE substr(NgayThu, 1, 7) = ?",
        (ym,),
    ).fetchone()[0]
    don_cho = conn.execute(
        "SELECT COUNT(*) FROM PHIEUBANHANG WHERE TrangThai = 'Chờ xử lý'"
    ).fetchone()[0]
    dv_chua_xong = conn.execute(
        "SELECT COUNT(*) FROM PHIEUDICHVU p "
        "WHERE EXISTS (SELECT 1 FROM CT_PHIEUDICHVU c WHERE c.SoPhieuDV = p.SoPhieuDV AND c.TinhTrang <> 'Đã giao')"
    ).fetchone()[0]
    tong_sp = conn.execute(
        "SELECT COUNT(*) FROM SANPHAM WHERE TinhTrang = 'Đang kinh doanh'"
    ).fetchone()[0]
    return {
        "dt_ban": dt_ban,
        "dt_dv": dt_dv,
        "don_cho": don_cho,
        "dv_chua_xong": dv_chua_xong,
        "tong_sp": tong_sp,
    }


def query_customer_directory(conn, q=""):
    """Tổng hợp lịch sử khách hàng trực tiếp từ Phiếu bán hàng và Phiếu dịch vụ (không cần bảng thừa)."""
    sql = """
    SELECT TenKhachHang, SoDienThoai,
           SUM(SoDonBan) AS SoDonBan,
           SUM(TongMua) AS TongMua,
           SUM(SoPhieuDV) AS SoPhieuDV,
           MAX(LanCuoi) AS LanCuoi
    FROM (
        SELECT COALESCE(NULLIF(TRIM(TenKhachHang), ''), 'Khách lẻ') AS TenKhachHang,
               COALESCE(SoDienThoai, '') AS SoDienThoai,
               1 AS SoDonBan,
               CASE WHEN TrangThai <> 'Đã hủy' THEN TongTien ELSE 0 END AS TongMua,
               0 AS SoPhieuDV,
               NgayLap AS LanCuoi
        FROM PHIEUBANHANG
        UNION ALL
        SELECT TenKhachHang, SoDienThoai,
               0 AS SoDonBan, 0 AS TongMua, 1 AS SoPhieuDV, NgayLap AS LanCuoi
        FROM PHIEUDICHVU
    ) t
    WHERE (? = '' OR t.TenKhachHang LIKE ? OR t.SoDienThoai LIKE ?)
    GROUP BY TenKhachHang, SoDienThoai
    ORDER BY TongMua DESC, LanCuoi DESC
    """
    like = f"%{q}%"
    return conn.execute(sql, (q, like, like)).fetchall()
