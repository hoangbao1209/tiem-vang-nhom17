"""Tầng Nghiệp vụ (Business Layer): Lập & xác nhận Phiếu kiểm kê kho.
Đảm bảo không làm thay đổi SANPHAM.SoLuongTon khi lưu/xác nhận phiếu kiểm kê.
"""
from datetime import datetime

from .. import repositories as repo
from ..utils import BusinessError, parse_date, to_float


def tao_phieu_kiem_ke(conn, ngay_kiem_ke, items, ma_nv, ghi_chu=None):
    if not ma_nv:
        raise BusinessError("Thiếu thông tin người thực hiện kiểm kê.")
    ngay = parse_date(ngay_kiem_ke, "Ngày kiểm kê")
    seen = set()
    lines = []
    for it in items:
        ma_sp = (it.get("MaSP") or "").strip()
        if not ma_sp or ma_sp in seen:
            continue
        seen.add(ma_sp)
        sp = repo.get_product(conn, ma_sp)
        if sp is None:
            raise BusinessError(f"Sản phẩm mã “{ma_sp}” không tồn tại.")
        thuc_te = to_float(it.get("TonThucTe"))
        if thuc_te is None or thuc_te < 0:
            raise BusinessError(f"“{sp['TenSP']}”: số lượng tồn thực tế không hợp lệ (phải ≥ 0).")
        thuc_te = round(thuc_te, 3)
        he_thong = round(float(sp["SoLuongTon"]), 3)
        chenh_lech = round(thuc_te - he_thong, 3)
        ly_do = (it.get("LyDoChenhLech") or "").strip()
        if abs(chenh_lech) > 1e-9 and not ly_do:
            raise BusinessError(
                f"“{sp['TenSP']}” có chênh lệch ({chenh_lech:+g}), bắt buộc phải nhập lý do chênh lệch."
            )
        lines.append((ma_sp, he_thong, thuc_te, chenh_lech, ly_do or None))

    if not lines:
        raise BusinessError("Phiếu kiểm kê phải có ít nhất một sản phẩm.")

    try:
        prefix = f"KK{ngay[:4]}{ngay[5:7]}"
        so_phieu = repo.next_code(conn, "PHIEUKIEMKE", "SoPhieuKK", prefix, width=3)
        repo.insert_stocktake(conn, so_phieu, ngay, ma_nv, (ghi_chu or "").strip() or None)
        for ln in lines:
            repo.insert_stocktake_line(conn, so_phieu, *ln)
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def xac_nhan_kiem_ke(conn, so_phieu_kk, ma_nv_xac_nhan, is_manager=False):
    p, _ = repo.get_stocktake(conn, so_phieu_kk)
    if p is None:
        raise BusinessError("Không tìm thấy phiếu kiểm kê kho.")
    if p["TrangThaiXacNhan"] == "Đã xác nhận":
        raise BusinessError("Phiếu kiểm kê này đã được xác nhận trước đó.")
    if not is_manager:
        raise BusinessError("Chỉ Quản lý mới có quyền xác nhận phiếu kiểm kê kho.")
    if p["MaNV_KiemKe"] == ma_nv_xac_nhan:
        raise BusinessError("Người xác nhận phiếu kiểm kê phải khác nhân viên thực hiện kiểm kê.")
    repo.confirm_stocktake(conn, so_phieu_kk, ma_nv_xac_nhan, datetime.now().strftime("%Y-%m-%d %H:%M"))
    conn.commit()


def lay_danh_sach_kiem_ke(conn):
    return repo.list_stocktakes(conn)


def lay_phieu_kiem_ke(conn, so_phieu_kk):
    return repo.get_stocktake(conn, so_phieu_kk)
