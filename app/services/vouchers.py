"""Nghiệp vụ lập phiếu MUA HÀNG / BÁN HÀNG / DỊCH VỤ kèm kiểm tra quy định."""
from datetime import datetime

from ..utils import BusinessError, format_vnd, parse_date, to_float, to_int
from .catalog import get_product
from .settings import get_params

TT_CHO = "Chờ xử lý"
TT_HOAN_TAT = "Hoàn tất"
TT_HUY = "Đã hủy"
NGUON_QUAY = "Tại quầy"
NGUON_ONLINE = "Online"

DV_CHUA_GIAO = "Chưa giao"
DV_DA_GIAO = "Đã giao"
PDV_CHUA_XONG = "Chưa hoàn thành"
PDV_XONG = "Hoàn thành"


# ------------------------------------------------------------------ khách hàng
def lay_hoac_tao_khach_hang(conn, ten, sdt=None, dia_chi=None, email=None):
    ten = (ten or "").strip() or "Khách lẻ"
    sdt = (sdt or "").strip().replace(" ", "")
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
def tao_phieu_mua(conn, ma_ncc, ngay_lap, items, ghi_chu=None, ma_nd=None):
    ncc = conn.execute("SELECT * FROM NHACUNGCAP WHERE MaNCC = ?", (ma_ncc,)).fetchone()
    if ncc is None:
        raise BusinessError("Vui lòng chọn nhà cung cấp.")
    if ncc["TinhTrang"] != "Đang hợp tác":
        raise BusinessError(f"Nhà cung cấp “{ncc['TenNCC']}” đã ngừng hợp tác.")
    ngay_lap = parse_date(ngay_lap, "Ngày lập")

    lines = []
    for it in items:
        ma_sp = to_int(it.get("MaSP"))
        if not ma_sp:
            continue
        sp = conn.execute("SELECT TenSP, TinhTrang FROM SANPHAM WHERE MaSP = ?", (ma_sp,)).fetchone()
        if sp is None:
            raise BusinessError(f"Sản phẩm mã {ma_sp} không tồn tại.")
        if sp["TinhTrang"] != "Đang kinh doanh":
            raise BusinessError(f"“{sp['TenSP']}” hiện đã ngừng kinh doanh.")
        sl = to_int(it.get("SoLuong"))
        dg = to_float(it.get("DonGia"))
        if not sl or sl <= 0:
            raise BusinessError(f"“{sp['TenSP']}”: số lượng phải là số nguyên dương.")
        if dg is None or dg < 0:
            raise BusinessError(f"“{sp['TenSP']}”: đơn giá mua không hợp lệ.")
        lines.append((ma_sp, sl, dg, round(sl * dg, 2)))
    if not lines:
        raise BusinessError("Phiếu mua hàng phải có ít nhất một sản phẩm.")

    try:
        cur = conn.execute(
            "INSERT INTO PHIEUMUAHANG(NgayLap, MaNCC, MaND_Lap, TongTien, GhiChu) VALUES (?, ?, ?, ?, ?)",
            (ngay_lap, ma_ncc, ma_nd, sum(x[3] for x in lines), ghi_chu or None),
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
        "SELECT p.*, n.TenNCC, n.DiaChi, n.SoDienThoai, u.HoTen AS NguoiLap "
        "FROM PHIEUMUAHANG p "
        "JOIN NHACUNGCAP n ON n.MaNCC = p.MaNCC "
        "LEFT JOIN NGUOIDUNG u ON u.MaND = p.MaND_Lap "
        "WHERE p.SoPhieu = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, []
    lines = conn.execute(
        "SELECT ct.*, sp.TenSP, sp.MaCode, l.TenLoaiSP, d.TenDVT FROM CT_PHIEUMUAHANG ct "
        "JOIN SANPHAM sp ON sp.MaSP = ct.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE ct.SoPhieu = ? ORDER BY ct.MaCT",
        (so_phieu,),
    ).fetchall()
    return p, lines


# ------------------------------------------------------------------ PHIẾU BÁN HÀNG
def tao_phieu_ban(
    conn,
    khach,
    items,
    ngay_lap,
    nguon=NGUON_QUAY,
    trang_thai=TT_HOAN_TAT,
    ghi_chu=None,
    ma_nd=None,
    pttt="Tiền mặt",
    so_tien_nhan=None,
):
    if pttt not in ("Tiền mặt", "Chuyển khoản"):
        raise BusinessError("Phương thức thanh toán phải là Tiền mặt hoặc Chuyển khoản.")

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
            if sp["TinhTrang"] != "Đang kinh doanh":
                raise BusinessError(f"“{sp['TenSP']}” hiện đã ngừng kinh doanh.")
            if nguon == NGUON_ONLINE and not sp["HienThi"]:
                raise BusinessError(f"“{sp['TenSP']}” hiện không kinh doanh trực tuyến.")
            if sp["SoLuongTon"] < sl:
                raise BusinessError(
                    f"“{sp['TenSP']}” chỉ còn {sp['SoLuongTon']} {sp['TenDVT']} trong kho."
                )
            if sp["DonGiaBan"] <= 0:
                raise BusinessError(f"“{sp['TenSP']}” chưa có giá bán.")
            lines.append((ma_sp, sl, sp["DonGiaBan"], round(sl * sp["DonGiaBan"], 2)))

        tong_tien = sum(x[3] for x in lines)
        if nguon == NGUON_QUAY:
            if pttt == "Tiền mặt":
                nhan = to_float(so_tien_nhan) if so_tien_nhan not in (None, "") else tong_tien
                if nhan is None or nhan < tong_tien:
                    raise BusinessError("Số tiền khách đưa không được nhỏ hơn tổng tiền thanh toán.")
                thua = nhan - tong_tien
            else:
                nhan = tong_tien
                thua = 0.0
        else:
            nhan = tong_tien if trang_thai == TT_HOAN_TAT else 0.0
            thua = 0.0

        cur = conn.execute(
            "INSERT INTO PHIEUBANHANG(NgayLap, MaKH, MaND_Lap, PhuongThucThanhToan, "
            "TongTien, SoTienNhan, TienThua, Nguon, TrangThai, GhiChu) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ngay_lap, ma_kh, ma_nd, pttt, tong_tien, nhan, thua, nguon, trang_thai, ghi_chu or None),
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
                raise BusinessError("Số lượng tồn kho vừa thay đổi, vui lòng kiểm tra lại.")
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def hoan_tat_phieu_ban(conn, so_phieu):
    p = conn.execute("SELECT TrangThai, TongTien FROM PHIEUBANHANG WHERE SoPhieu = ?", (so_phieu,)).fetchone()
    if p is None:
        raise BusinessError("Không tìm thấy phiếu bán hàng.")
    if p["TrangThai"] != TT_CHO:
        raise BusinessError("Chỉ xác nhận được đơn đang chờ xử lý.")
    conn.execute(
        "UPDATE PHIEUBANHANG SET TrangThai = ?, SoTienNhan = TongTien, TienThua = 0 WHERE SoPhieu = ?",
        (TT_HOAN_TAT, so_phieu),
    )
    conn.commit()


def huy_phieu_ban(conn, so_phieu):
    p = conn.execute("SELECT TrangThai FROM PHIEUBANHANG WHERE SoPhieu = ?", (so_phieu,)).fetchone()
    if p is None:
        raise BusinessError("Không tìm thấy phiếu bán hàng.")
    if p["TrangThai"] == TT_HUY:
        raise BusinessError("Phiếu này đã bị hủy trước đó.")
    try:
        rows = conn.execute("SELECT MaSP, SoLuong FROM CT_PHIEUBANHANG WHERE SoPhieu = ?", (so_phieu,)).fetchall()
        for ct in rows:
            conn.execute(
                "UPDATE SANPHAM SET SoLuongTon = SoLuongTon + ? WHERE MaSP = ?",
                (ct["SoLuong"], ct["MaSP"]),
            )
        conn.execute("UPDATE PHIEUBANHANG SET TrangThai = ? WHERE SoPhieu = ?", (TT_HUY, so_phieu))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def lay_phieu_ban(conn, so_phieu):
    p = conn.execute(
        "SELECT p.*, k.TenKH, k.SoDienThoai, k.DiaChi, k.Email, u.HoTen AS NguoiLap "
        "FROM PHIEUBANHANG p "
        "JOIN KHACHHANG k ON k.MaKH = p.MaKH "
        "LEFT JOIN NGUOIDUNG u ON u.MaND = p.MaND_Lap "
        "WHERE p.SoPhieu = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, []
    lines = conn.execute(
        "SELECT ct.*, sp.TenSP, sp.MaCode, sp.HinhAnh, l.TenLoaiSP, d.TenDVT FROM CT_PHIEUBANHANG ct "
        "JOIN SANPHAM sp ON sp.MaSP = ct.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE ct.SoPhieu = ? ORDER BY ct.MaCT",
        (so_phieu,),
    ).fetchall()
    return p, lines


# ------------------------------------------------------------------ PHIẾU DỊCH VỤ
def tao_phieu_dich_vu(conn, khach, items, ngay_lap, ma_nd=None, hinh_thuc="Tiền mặt"):
    ngay_lap = parse_date(ngay_lap, "Ngày lập")
    if hinh_thuc not in ("Tiền mặt", "Chuyển khoản"):
        hinh_thuc = "Tiền mặt"
    ti_le_he_thong = to_float(get_params(conn).get("TiLeTraTruocToiThieu"), 50)
    if ti_le_he_thong is None:
        ti_le_he_thong = 50.0

    lines = []
    for it in items:
        ma = to_int(it.get("MaLoaiDV"))
        if not ma:
            continue
        loai = conn.execute("SELECT * FROM LOAIDICHVU WHERE MaLoaiDV = ?", (ma,)).fetchone()
        if loai is None:
            raise BusinessError(f"Dịch vụ mã {ma} không tồn tại.")
        if loai["TinhTrang"] != "Đang hoạt động":
            raise BusinessError(f"Dịch vụ “{loai['TenLoaiDV']}” hiện đã ngừng hoạt động.")
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
        ngay_giao = parse_date(it.get("NgayGiao"), f"“{ten}”: ngày giao dự kiến")
        if ngay_giao < ngay_lap:
            raise BusinessError(f"“{ten}”: ngày giao dự kiến không được trước ngày lập phiếu.")

        dgdt = loai["DonGia"] + cpr
        tt = dgdt * sl
        toi_thieu = tt * ti_le_he_thong / 100.0
        if tra + 1e-6 < toi_thieu:
            raise BusinessError(
                f"“{ten}”: tiền trả trước tối thiểu là {format_vnd(toi_thieu)} "
                f"({ti_le_he_thong:g}% thành tiền)."
            )
        if tra > tt + 1e-6:
            raise BusinessError(f"“{ten}”: tiền trả trước không được vượt quá thành tiền.")
        lines.append((ma, dgdt, cpr, sl, tt, tra, tt - tra, ngay_giao))
    if not lines:
        raise BusinessError("Phiếu dịch vụ phải có ít nhất một dịch vụ.")

    try:
        ma_kh = lay_hoac_tao_khach_hang(conn, **khach)
        tong_tien = sum(x[4] for x in lines)
        tong_tra = sum(x[5] for x in lines)
        tong_con = sum(x[6] for x in lines)
        cur = conn.execute(
            "INSERT INTO PHIEUDICHVU(NgayLap, MaKH, MaND_Lap, TiLeTraTruocApDung, "
            "TongTien, TongTraTruoc, TongConLai, TinhTrang) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ngay_lap, ma_kh, ma_nd, ti_le_he_thong, tong_tien, tong_tra, tong_con, PDV_CHUA_XONG),
        )
        so_phieu = cur.lastrowid
        for ln in lines:
            conn.execute(
                "INSERT INTO CT_PHIEUDICHVU(SoPhieu, MaLoaiDV, DonGiaDuocTinh, ChiPhiRieng, SoLuong, "
                "ThanhTien, TraTruoc, ConLai, NgayGiao, TinhTrang) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (so_phieu, *ln, DV_CHUA_GIAO),
            )
        if tong_tra > 0:
            conn.execute(
                "INSERT INTO THUTIENDICHVU(SoPhieuDV, NgayThu, SoTienThu, LoaiThu, HinhThucThanhToan, MaND_Thu, GhiChu) "
                "VALUES (?, ?, ?, 'Thu trả trước', ?, ?, 'Thu tiền đặt trước khi lập phiếu')",
                (so_phieu, ngay_lap, tong_tra, hinh_thuc, ma_nd),
            )
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def thu_tien_dich_vu(conn, so_phieu, so_tien, hinh_thuc="Tiền mặt", ma_nd=None, ghi_chu=None, ngay_thu=None):
    p = conn.execute("SELECT TongTien FROM PHIEUDICHVU WHERE SoPhieu = ?", (so_phieu,)).fetchone()
    if p is None:
        raise BusinessError("Không tìm thấy phiếu dịch vụ.")
    so_tien = to_float(so_tien)
    if so_tien is None or so_tien <= 0:
        raise BusinessError("Số tiền thu phải lớn hơn 0.")
    if hinh_thuc not in ("Tiền mặt", "Chuyển khoản"):
        hinh_thuc = "Tiền mặt"
    da_thu = conn.execute(
        "SELECT COALESCE(SUM(SoTienThu), 0) FROM THUTIENDICHVU WHERE SoPhieuDV = ?", (so_phieu,)
    ).fetchone()[0]
    con_no = p["TongTien"] - da_thu
    if so_tien > con_no + 1e-6:
        raise BusinessError(f"Số tiền thu không được vượt quá số tiền còn phải thu ({format_vnd(con_no)}).")
    ngay = ngay_thu or datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        "INSERT INTO THUTIENDICHVU(SoPhieuDV, NgayThu, SoTienThu, LoaiThu, HinhThucThanhToan, MaND_Thu, GhiChu) "
        "VALUES (?, ?, ?, 'Thu phần còn lại', ?, ?, ?)",
        (so_phieu, ngay, so_tien, hinh_thuc, ma_nd, ghi_chu or None),
    )
    conn.commit()


def cap_nhat_tinh_trang_dich_vu(conn, ma_ct, tinh_trang_moi, ma_nd=None, co_quyen_chuyen_nguoc=False, ly_do=None, ghi_chu=None):
    ct = conn.execute("SELECT SoPhieu, TinhTrang FROM CT_PHIEUDICHVU WHERE MaCT = ?", (ma_ct,)).fetchone()
    if ct is None:
        raise BusinessError("Không tìm thấy hạng mục dịch vụ.")
    cu = ct["TinhTrang"]
    if tinh_trang_moi not in (DV_CHUA_GIAO, DV_DA_GIAO):
        raise BusinessError("Tình trạng mới không hợp lệ.")
    if cu == tinh_trang_moi:
        raise BusinessError(f"Hạng mục này hiện đã ở trạng thái “{tinh_trang_moi}”.")

    if cu == DV_DA_GIAO and tinh_trang_moi == DV_CHUA_GIAO:
        if not co_quyen_chuyen_nguoc:
            raise BusinessError("Bạn không có quyền chuyển ngược trạng thái từ Đã giao về Chưa giao.")
        if not (ly_do or "").strip():
            raise BusinessError("Vui lòng nhập lý do khi chuyển ngược trạng thái về Chưa giao.")

    try:
        if ghi_chu is not None:
            conn.execute(
                "UPDATE CT_PHIEUDICHVU SET TinhTrang = ?, GhiChu = ? WHERE MaCT = ?",
                (tinh_trang_moi, ghi_chu.strip() or None, ma_ct),
            )
        else:
            conn.execute("UPDATE CT_PHIEUDICHVU SET TinhTrang = ? WHERE MaCT = ?", (tinh_trang_moi, ma_ct))

        conn.execute(
            "INSERT INTO LICHSUTINHTRANG(MaCT, MaND, ThoiDiemCapNhat, TinhTrangCu, TinhTrangMoi, LyDo) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ma_ct, ma_nd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cu, tinh_trang_moi, (ly_do or "").strip() or None),
        )
        con = conn.execute(
            "SELECT COUNT(*) FROM CT_PHIEUDICHVU WHERE SoPhieu = ? AND TinhTrang <> ?",
            (ct["SoPhieu"], DV_DA_GIAO),
        ).fetchone()[0]
        conn.execute(
            "UPDATE PHIEUDICHVU SET TinhTrang = ? WHERE SoPhieu = ?",
            (PDV_XONG if con == 0 else PDV_CHUA_XONG, ct["SoPhieu"]),
        )
        conn.commit()
        return ct["SoPhieu"]
    except Exception:
        conn.rollback()
        raise


def giao_dich_vu(conn, ma_ct, ma_nd=None):
    return cap_nhat_tinh_trang_dich_vu(conn, ma_ct, DV_DA_GIAO, ma_nd=ma_nd)


def lay_phieu_dich_vu(conn, so_phieu):
    p = conn.execute(
        "SELECT p.*, k.TenKH, k.SoDienThoai, k.DiaChi, u.HoTen AS NguoiLap "
        "FROM PHIEUDICHVU p "
        "JOIN KHACHHANG k ON k.MaKH = p.MaKH "
        "LEFT JOIN NGUOIDUNG u ON u.MaND = p.MaND_Lap "
        "WHERE p.SoPhieu = ?",
        (so_phieu,),
    ).fetchone()
    if p is None:
        return None, [], [], 0
    lines = conn.execute(
        "SELECT ct.*, l.TenLoaiDV, l.DonGia AS DonGiaDichVu FROM CT_PHIEUDICHVU ct "
        "JOIN LOAIDICHVU l ON l.MaLoaiDV = ct.MaLoaiDV WHERE ct.SoPhieu = ? ORDER BY ct.MaCT",
        (so_phieu,),
    ).fetchall()
    receipts = conn.execute(
        "SELECT t.*, u.HoTen AS NguoiThu FROM THUTIENDICHVU t "
        "LEFT JOIN NGUOIDUNG u ON u.MaND = t.MaND_Thu "
        "WHERE t.SoPhieuDV = ? ORDER BY t.MaPhieuThu",
        (so_phieu,),
    ).fetchall()
    da_thu = sum(r["SoTienThu"] for r in receipts)
    return p, lines, receipts, da_thu
