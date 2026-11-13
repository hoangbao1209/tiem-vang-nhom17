"""Nghiệp vụ lập phiếu MUA HÀNG / BÁN HÀNG / DỊCH VỤ kèm kiểm tra quy định.

Các hàm nhận vào `conn` (kết nối SQLite) để dùng được cả trong web lẫn script seed.
Mỗi hàm chạy trong 1 transaction: lỗi ở bất kỳ dòng nào -> rollback toàn bộ phiếu.
"""
from ..utils import BusinessError, format_vnd, parse_date, to_float, to_int
from .catalog import get_product

# Trạng thái phiếu bán
TT_CHO = "Chờ xử lý"
TT_HOAN_TAT = "Hoàn tất"
TT_HUY = "Đã hủy"
NGUON_QUAY = "Tại quầy"
NGUON_ONLINE = "Online"

# Tình trạng dịch vụ
DV_CHUA_GIAO = "Chưa giao"
DV_DA_GIAO = "Đã giao"
PDV_CHUA_XONG = "Chưa hoàn thành"
PDV_XONG = "Hoàn thành"


# ------------------------------------------------------------------ khách hàng
def lay_hoac_tao_khach_hang(conn, ten, sdt, dia_chi=None, email=None):
    """Tìm khách theo số điện thoại; chưa có thì tạo mới."""
    ten = (ten or "").strip()
    sdt = (sdt or "").strip().replace(" ", "")
    if not ten:
        raise BusinessError("Vui lòng nhập tên khách hàng.")
    if sdt:
        kh = conn.execute("SELECT MaKH FROM KHACHHANG WHERE SoDienThoai = ?", (sdt,)).fetchone()
        if kh:
            conn.execute(
                "UPDATE KHACHHANG SET TenKH = ?, "
                "DiaChi = COALESCE(NULLIF(?, ''), DiaChi), Email = COALESCE(NULLIF(?, ''), Email) "
                "WHERE MaKH = ?",
                (ten, dia_chi or "", email or "", kh["MaKH"]),
            )
            return kh["MaKH"]
    cur = conn.execute(
        "INSERT INTO KHACHHANG(TenKH, SoDienThoai, DiaChi, Email) VALUES (?, ?, ?, ?)",
        (ten, sdt or None, dia_chi or None, email or None),
    )
    return cur.lastrowid


# ------------------------------------------------------------------ PHIẾU MUA HÀNG
def tao_phieu_mua(conn, ma_ncc, ngay_lap, items, ghi_chu=None):
    """items: [{MaSP, SoLuong, DonGia}].
    QĐ: số lượng > 0, đơn giá >= 0. Nhập hàng làm TĂNG tồn kho và cập nhật
    đơn giá mua (giá mua gần nhất) của sản phẩm.
    """
    if not ma_ncc or not conn.execute("SELECT 1 FROM NHACUNGCAP WHERE MaNCC = ?", (ma_ncc,)).fetchone():
        raise BusinessError("Vui lòng chọn nhà cung cấp.")
    ngay_lap = parse_date(ngay_lap, "Ngày lập")

    lines = []
    for it in items:
        ma_sp = to_int(it.get("MaSP"))
        if not ma_sp:
            continue
        sp = conn.execute("SELECT TenSP FROM SANPHAM WHERE MaSP = ?", (ma_sp,)).fetchone()
        if sp is None:
            raise BusinessError(f"Sản phẩm mã {ma_sp} không tồn tại.")
        sl = to_int(it.get("SoLuong"))
        dg = to_float(it.get("DonGia"))
        if not sl or sl <= 0:
            raise BusinessError(f"“{sp['TenSP']}”: số lượng phải là số nguyên dương.")
        if dg is None or dg < 0:
            raise BusinessError(f"“{sp['TenSP']}”: đơn giá mua không hợp lệ.")
        lines.append((ma_sp, sl, dg, sl * dg))
    if not lines:
        raise BusinessError("Phiếu mua hàng phải có ít nhất một sản phẩm.")

    try:
        cur = conn.execute(
            "INSERT INTO PHIEUMUAHANG(NgayLap, MaNCC, TongTien, GhiChu) VALUES (?, ?, ?, ?)",
            (ngay_lap, ma_ncc, sum(x[3] for x in lines), ghi_chu or None),
        )
        so_phieu = cur.lastrowid
        for ma_sp, sl, dg, tt in lines:
            conn.execute(
                "INSERT INTO CT_PHIEUMUAHANG(SoPhieu, MaSP, SoLuong, DonGia, ThanhTien) VALUES (?, ?, ?, ?, ?)",
                (so_phieu, ma_sp, sl, dg, tt),
            )
            conn.execute(
                "UPDATE SANPHAM SET SoLuongTon = SoLuongTon + ?, DonGiaMua = ? WHERE MaSP = ?",
                (sl, dg, ma_sp),
            )
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def lay_phieu_mua(conn, so_phieu):
    p = conn.execute(
        "SELECT p.*, n.TenNCC, n.DiaChi, n.SoDienThoai FROM PHIEUMUAHANG p "
        "JOIN NHACUNGCAP n ON n.MaNCC = p.MaNCC WHERE p.SoPhieu = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, []
    lines = conn.execute(
        "SELECT ct.*, sp.TenSP, l.TenLoaiSP, d.TenDVT FROM CT_PHIEUMUAHANG ct "
        "JOIN SANPHAM sp ON sp.MaSP = ct.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE ct.SoPhieu = ? ORDER BY ct.MaCT",
        (so_phieu,),
    ).fetchall()
    return p, lines


# ------------------------------------------------------------------ PHIẾU BÁN HÀNG
def tao_phieu_ban(conn, khach, items, ngay_lap, nguon=NGUON_QUAY, trang_thai=TT_HOAN_TAT, ghi_chu=None):
    """khach: {ten, sdt, dia_chi, email}; items: [{MaSP, SoLuong}].
    QĐ: Đơn giá bán = Đơn giá mua × (1 + % lợi nhuận loại SP) (tính ở server);
        số lượng bán không vượt quá số lượng tồn. Bán hàng làm GIẢM tồn kho.
    """
    gop = {}
    for it in items:
        ma_sp = to_int(it.get("MaSP"))
        if not ma_sp:
            continue
        sl = to_int(it.get("SoLuong"))
        if not sl or sl <= 0:
            raise BusinessError("Số lượng bán phải là số nguyên dương.")
        gop[ma_sp] = gop.get(ma_sp, 0) + sl
    if not gop:
        raise BusinessError("Phiếu bán hàng phải có ít nhất một sản phẩm.")

    try:
        ma_kh = lay_hoac_tao_khach_hang(conn, **khach)
        lines = []
        for ma_sp, sl in gop.items():
            sp = get_product(conn, ma_sp)
            if sp is None:
                raise BusinessError(f"Sản phẩm mã {ma_sp} không tồn tại.")
            if nguon == NGUON_ONLINE and not sp["HienThi"]:
                raise BusinessError(f"“{sp['TenSP']}” hiện không còn kinh doanh.")
            if sp["SoLuongTon"] < sl:
                raise BusinessError(
                    f"“{sp['TenSP']}” chỉ còn {sp['SoLuongTon']} {sp['TenDVT']} trong kho.")
            if sp["DonGiaBan"] <= 0:
                raise BusinessError(f"“{sp['TenSP']}” chưa có giá bán (chưa nhập hàng).")
            lines.append((ma_sp, sl, sp["DonGiaBan"], sl * sp["DonGiaBan"]))

        cur = conn.execute(
            "INSERT INTO PHIEUBANHANG(NgayLap, MaKH, TongTien, Nguon, TrangThai, GhiChu) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ngay_lap, ma_kh, sum(x[3] for x in lines), nguon, trang_thai, ghi_chu or None),
        )
        so_phieu = cur.lastrowid
        for ma_sp, sl, dg, tt in lines:
            conn.execute(
                "INSERT INTO CT_PHIEUBANHANG(SoPhieu, MaSP, SoLuong, DonGiaBan, ThanhTien) "
                "VALUES (?, ?, ?, ?, ?)",
                (so_phieu, ma_sp, sl, dg, tt),
            )
            r = conn.execute(
                "UPDATE SANPHAM SET SoLuongTon = SoLuongTon - ? WHERE MaSP = ? AND SoLuongTon >= ?",
                (sl, ma_sp, sl),
            )
            if r.rowcount != 1:
                raise BusinessError("Tồn kho vừa thay đổi, vui lòng thử lại.")
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def hoan_tat_phieu_ban(conn, so_phieu):
    p = conn.execute("SELECT TrangThai FROM PHIEUBANHANG WHERE SoPhieu = ?", (so_phieu,)).fetchone()
    if p is None:
        raise BusinessError("Không tìm thấy phiếu bán hàng.")
    if p["TrangThai"] != TT_CHO:
        raise BusinessError("Chỉ xác nhận được đơn đang chờ xử lý.")
    conn.execute("UPDATE PHIEUBANHANG SET TrangThai = ? WHERE SoPhieu = ?", (TT_HOAN_TAT, so_phieu))
    conn.commit()


def huy_phieu_ban(conn, so_phieu):
    """Hủy phiếu -> hoàn lại số lượng tồn kho."""
    p = conn.execute("SELECT TrangThai FROM PHIEUBANHANG WHERE SoPhieu = ?", (so_phieu,)).fetchone()
    if p is None:
        raise BusinessError("Không tìm thấy phiếu bán hàng.")
    if p["TrangThai"] == TT_HUY:
        raise BusinessError("Phiếu này đã bị hủy trước đó.")
    try:
        rows = conn.execute("SELECT MaSP, SoLuong FROM CT_PHIEUBANHANG WHERE SoPhieu = ?", (so_phieu,)).fetchall()
        for ct in rows:
            conn.execute("UPDATE SANPHAM SET SoLuongTon = SoLuongTon + ? WHERE MaSP = ?",
                         (ct["SoLuong"], ct["MaSP"]))
        conn.execute("UPDATE PHIEUBANHANG SET TrangThai = ? WHERE SoPhieu = ?", (TT_HUY, so_phieu))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def lay_phieu_ban(conn, so_phieu):
    p = conn.execute(
        "SELECT p.*, k.TenKH, k.SoDienThoai, k.DiaChi, k.Email FROM PHIEUBANHANG p "
        "JOIN KHACHHANG k ON k.MaKH = p.MaKH WHERE p.SoPhieu = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, []
    lines = conn.execute(
        "SELECT ct.*, sp.TenSP, sp.HinhAnh, l.TenLoaiSP, d.TenDVT FROM CT_PHIEUBANHANG ct "
        "JOIN SANPHAM sp ON sp.MaSP = ct.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE ct.SoPhieu = ? ORDER BY ct.MaCT",
        (so_phieu,),
    ).fetchall()
    return p, lines


# ------------------------------------------------------------------ PHIẾU DỊCH VỤ
def tao_phieu_dich_vu(conn, khach, items, ngay_lap):
    """items: [{MaLoaiDV, SoLuong, ChiPhiRieng, TraTruoc, NgayGiao}].
    QĐ: Đơn giá được tính = Đơn giá dịch vụ + Chi phí riêng
        Thành tiền = Đơn giá được tính × Số lượng
        Trả trước >= Thành tiền × % trả trước tối thiểu của loại dịch vụ
        Còn lại = Thành tiền - Trả trước ; Ngày giao >= Ngày lập
    """
    ngay_lap = parse_date(ngay_lap, "Ngày lập")
    lines = []
    for it in items:
        ma = to_int(it.get("MaLoaiDV"))
        if not ma:
            continue
        loai = conn.execute("SELECT * FROM LOAIDICHVU WHERE MaLoaiDV = ?", (ma,)).fetchone()
        if loai is None:
            raise BusinessError(f"Loại dịch vụ mã {ma} không tồn tại.")
        ten = loai["TenLoaiDV"]
        sl = to_int(it.get("SoLuong"))
        cpr = to_float(it.get("ChiPhiRieng") or 0)
        tra = to_float(it.get("TraTruoc"))
        if not sl or sl <= 0:
            raise BusinessError(f"“{ten}”: số lượng phải là số nguyên dương.")
        if cpr is None or cpr < 0:
            raise BusinessError(f"“{ten}”: chi phí riêng không hợp lệ.")
        if tra is None or tra < 0:
            raise BusinessError(f"“{ten}”: vui lòng nhập số tiền trả trước hợp lệ.")
        ngay_giao = parse_date(it.get("NgayGiao"), f"“{ten}”: ngày giao")
        if ngay_giao < ngay_lap:
            raise BusinessError(f"“{ten}”: ngày giao không được trước ngày lập phiếu.")

        dgdt = loai["DonGia"] + cpr
        tt = dgdt * sl
        toi_thieu = tt * loai["PhanTramTraTruoc"] / 100
        if tra + 1e-6 < toi_thieu:
            raise BusinessError(
                f"“{ten}”: trả trước tối thiểu {format_vnd(toi_thieu)} "
                f"({loai['PhanTramTraTruoc']:g}% thành tiền).")
        if tra > tt + 1e-6:
            raise BusinessError(f"“{ten}”: tiền trả trước không được vượt quá thành tiền.")
        lines.append((ma, dgdt, cpr, sl, tt, tra, tt - tra, ngay_giao))
    if not lines:
        raise BusinessError("Phiếu dịch vụ phải có ít nhất một dịch vụ.")

    try:
        ma_kh = lay_hoac_tao_khach_hang(conn, **khach)
        cur = conn.execute(
            "INSERT INTO PHIEUDICHVU(NgayLap, MaKH, TongTien, TongTraTruoc, TongConLai, TinhTrang) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ngay_lap, ma_kh, sum(x[4] for x in lines), sum(x[5] for x in lines),
             sum(x[6] for x in lines), PDV_CHUA_XONG),
        )
        so_phieu = cur.lastrowid
        for ln in lines:
            conn.execute(
                "INSERT INTO CT_PHIEUDICHVU(SoPhieu, MaLoaiDV, DonGiaDuocTinh, ChiPhiRieng, SoLuong, "
                "ThanhTien, TraTruoc, ConLai, NgayGiao, TinhTrang) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (so_phieu, *ln, DV_CHUA_GIAO),
            )
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def giao_dich_vu(conn, ma_ct):
    """Đánh dấu 1 dòng dịch vụ đã giao; giao hết -> phiếu 'Hoàn thành'."""
    ct = conn.execute("SELECT SoPhieu, TinhTrang FROM CT_PHIEUDICHVU WHERE MaCT = ?", (ma_ct,)).fetchone()
    if ct is None:
        raise BusinessError("Không tìm thấy dòng dịch vụ.")
    if ct["TinhTrang"] == DV_DA_GIAO:
        raise BusinessError("Dịch vụ này đã được giao.")
    try:
        conn.execute("UPDATE CT_PHIEUDICHVU SET TinhTrang = ? WHERE MaCT = ?", (DV_DA_GIAO, ma_ct))
        con = conn.execute(
            "SELECT COUNT(*) FROM CT_PHIEUDICHVU WHERE SoPhieu = ? AND TinhTrang <> ?",
            (ct["SoPhieu"], DV_DA_GIAO),
        ).fetchone()[0]
        conn.execute("UPDATE PHIEUDICHVU SET TinhTrang = ? WHERE SoPhieu = ?",
                     (PDV_XONG if con == 0 else PDV_CHUA_XONG, ct["SoPhieu"]))
        conn.commit()
        return ct["SoPhieu"]
    except Exception:
        conn.rollback()
        raise


def lay_phieu_dich_vu(conn, so_phieu):
    p = conn.execute(
        "SELECT p.*, k.TenKH, k.SoDienThoai, k.DiaChi FROM PHIEUDICHVU p "
        "JOIN KHACHHANG k ON k.MaKH = p.MaKH WHERE p.SoPhieu = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, []
    lines = conn.execute(
        "SELECT ct.*, l.TenLoaiDV, l.DonGia AS DonGiaDichVu FROM CT_PHIEUDICHVU ct "
        "JOIN LOAIDICHVU l ON l.MaLoaiDV = ct.MaLoaiDV WHERE ct.SoPhieu = ? ORDER BY ct.MaCT",
        (so_phieu,),
    ).fetchall()
    return p, lines
