"""Nghiệp vụ kiểm kê kho (lập phiếu đối chiếu tồn hệ thống & tồn thực tế)."""
from datetime import datetime

from ..utils import BusinessError, parse_date, to_int


def tao_phieu_kiem_ke(conn, ngay_kiem_ke, items, ma_nd, ghi_chu=None):
    ngay = parse_date(ngay_kiem_ke, "Ngày kiểm kê")
    seen = set()
    lines = []
    for it in items:
        ma_sp = to_int(it.get("MaSP"))
        if not ma_sp or ma_sp in seen:
            continue
        seen.add(ma_sp)
        sp = conn.execute("SELECT TenSP, SoLuongTon FROM SANPHAM WHERE MaSP = ?", (ma_sp,)).fetchone()
        if sp is None:
            raise BusinessError(f"Sản phẩm mã {ma_sp} không tồn tại.")
        thuc_te = to_int(it.get("TonThucTe"))
        if thuc_te is None or thuc_te < 0:
            raise BusinessError(f"“{sp['TenSP']}”: số lượng tồn thực tế không hợp lệ.")
        he_thong = sp["SoLuongTon"]
        chenh_lech = thuc_te - he_thong
        ly_do = (it.get("LyDoChenhLech") or "").strip()
        if chenh_lech != 0 and not ly_do:
            raise BusinessError(
                f"“{sp['TenSP']}” có chênh lệch ({chenh_lech:+d}), vui lòng nhập lý do chênh lệch."
            )
        lines.append((ma_sp, he_thong, thuc_te, chenh_lech, ly_do or None))

    if not lines:
        raise BusinessError("Phiếu kiểm kê phải có ít nhất một sản phẩm.")

    try:
        cur = conn.execute(
            "INSERT INTO PHIEUKIEMKE(NgayKiemKe, MaND_KiemKe, TrangThaiXacNhan, GhiChu) "
            "VALUES (?, ?, 'Chờ xác nhận', ?)",
            (ngay, ma_nd, (ghi_chu or "").strip() or None),
        )
        so_phieu = cur.lastrowid
        for ln in lines:
            conn.execute(
                "INSERT INTO CT_PHIEUKIEMKE(SoPhieuKK, MaSP, TonHeThong, TonThucTe, ChenhLech, LyDoChenhLech) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (so_phieu, *ln),
            )
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def xac_nhan_kiem_ke(conn, so_phieu_kk, ma_nd_xac_nhan, is_admin=False):
    p = conn.execute("SELECT * FROM PHIEUKIEMKE WHERE SoPhieuKK = ?", (so_phieu_kk,)).fetchone()
    if p is None:
        raise BusinessError("Không tìm thấy phiếu kiểm kê.")
    if p["TrangThaiXacNhan"] == "Đã xác nhận":
        raise BusinessError("Phiếu kiểm kê này đã được xác nhận trước đó.")
    if not is_admin:
        raise BusinessError("Chỉ quản trị viên mới có quyền xác nhận phiếu kiểm kê.")
    if p["MaND_KiemKe"] == ma_nd_xac_nhan:
        raise BusinessError("Người xác nhận phải khác người thực hiện kiểm kê.")
    conn.execute(
        "UPDATE PHIEUKIEMKE SET TrangThaiXacNhan = 'Đã xác nhận', MaND_XacNhan = ?, NgayXacNhan = ? "
        "WHERE SoPhieuKK = ?",
        (ma_nd_xac_nhan, datetime.now().strftime("%Y-%m-%d %H:%M"), so_phieu_kk),
    )
    conn.commit()


def lay_phieu_kiem_ke(conn, so_phieu_kk):
    p = conn.execute(
        "SELECT p.*, u1.HoTen AS NguoiKiemKe, u2.HoTen AS NguoiXacNhan "
        "FROM PHIEUKIEMKE p "
        "LEFT JOIN NGUOIDUNG u1 ON u1.MaND = p.MaND_KiemKe "
        "LEFT JOIN NGUOIDUNG u2 ON u2.MaND = p.MaND_XacNhan "
        "WHERE p.SoPhieuKK = ?",
        (so_phieu_kk,),
    ).fetchone()
    if p is None:
        return None, []
    lines = conn.execute(
        "SELECT ct.*, sp.TenSP, sp.MaCode, l.TenLoaiSP, d.TenDVT "
        "FROM CT_PHIEUKIEMKE ct "
        "JOIN SANPHAM sp ON sp.MaSP = ct.MaSP "
        "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
        "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
        "WHERE ct.SoPhieuKK = ? ORDER BY sp.MaSP",
        (so_phieu_kk,),
    ).fetchall()
    return p, lines
