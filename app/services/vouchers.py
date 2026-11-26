"""Tầng Nghiệp vụ (Business Layer): Phiếu mua hàng, Phiếu bán hàng, Phiếu dịch vụ,
Thu tiền dịch vụ & Quản lý tình trạng (kèm kiểm tra khóa kỳ kế toán).
"""
from datetime import datetime

from .. import repositories as repo
from ..utils import BusinessError, format_vnd, parse_date, to_float, to_int

TT_CHO = "Chờ xử lý"
TT_HOAN_TAT = "Hoàn tất"
TT_HUY = "Đã hủy"
NGUON_QUAY = "Tại quầy"
NGUON_ONLINE = "Online"

DV_CHUA_GIAO = "Chưa giao"
DV_DA_GIAO = "Đã giao"


def _check_not_locked_period(conn, ngay_str):
    """Chặn tạo hoặc thay đổi chứng từ nếu kỳ kế toán tương ứng đã ở trạng thái 'Đã khóa'."""
    d = parse_date(ngay_str, "Ngày chứng từ")
    nam, thang = int(d[:4]), int(d[5:7])
    ky = repo.get_period(conn, thang, nam)
    if ky is not None and ky["TrangThai"] == "Đã khóa":
        raise BusinessError(
            f"Kỳ kế toán tháng {thang:02d}/{nam} đã khóa sổ, không được phép phát sinh hay sửa đổi chứng từ trong kỳ này."
        )


def _voucher_prefix(tag, ngay_str):
    d = parse_date(ngay_str, "Ngày chứng từ")
    return f"{tag}{d[:4]}{d[5:7]}"


# ------------------------------------------------------------------ PHIẾU MUA HÀNG
def tao_phieu_mua(conn, ma_ncc, ngay_lap, items, ghi_chu=None, ma_nv=None):
    if not ma_nv:
        raise BusinessError("Thiếu thông tin nhân viên lập phiếu.")
    ncc = repo.get_supplier(conn, ma_ncc)
    if ncc is None:
        raise BusinessError("Vui lòng chọn nhà cung cấp.")
    if ncc["TinhTrang"] != "Đang hợp tác":
        raise BusinessError(f"Nhà cung cấp “{ncc['TenNCC']}” đã ngừng hợp tác, không thể lập phiếu mua.")
    ngay_chuan = parse_date(ngay_lap, "Ngày lập")
    _check_not_locked_period(conn, ngay_chuan)

    lines = []
    for it in items:
        ma_sp = (it.get("MaSP") or "").strip()
        if not ma_sp:
            continue
        sp = repo.get_product(conn, ma_sp)
        if sp is None:
            raise BusinessError(f"Sản phẩm mã “{ma_sp}” không tồn tại.")
        if sp["TinhTrang"] != "Đang kinh doanh":
            raise BusinessError(f"Sản phẩm “{sp['TenSP']}” hiện đã ngừng kinh doanh.")
        sl = to_float(it.get("SoLuong"))
        dg = to_float(it.get("DonGia"))
        if sl is None or sl <= 0:
            raise BusinessError(f"“{sp['TenSP']}”: số lượng mua phải lớn hơn 0.")
        if dg is None or dg < 0:
            raise BusinessError(f"“{sp['TenSP']}”: đơn giá mua không hợp lệ.")
        lines.append((ma_sp, round(sl, 3), round(dg, 2)))

    if not lines:
        raise BusinessError("Phiếu mua hàng phải có ít nhất một dòng sản phẩm.")

    try:
        so_phieu = repo.next_code(conn, "PHIEUMUAHANG", "SoPhieuMua", _voucher_prefix("PM", ngay_chuan), width=3)
        repo.insert_purchase(conn, so_phieu, ngay_chuan, ma_ncc, ma_nv, (ghi_chu or "").strip() or None)
        for idx, (ma_sp, sl, dg) in enumerate(lines, start=1):
            repo.insert_purchase_line(conn, so_phieu, idx, ma_sp, sl, dg)
            repo.increase_stock_on_purchase(conn, ma_sp, sl, dg)
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def lay_danh_sach_phieu_mua(conn, q="", ma_ncc="", tu_ngay="", den_ngay=""):
    rows = repo.list_purchases(conn, q=q, ma_ncc=ma_ncc, tu_ngay=tu_ngay, den_ngay=den_ngay)
    tong = sum(r["TongTien"] for r in rows)
    return rows, tong


def lay_phieu_mua(conn, so_phieu):
    return repo.get_purchase(conn, so_phieu)


# ------------------------------------------------------------------ PHIẾU BÁN HÀNG
def tao_phieu_ban(
    conn,
    khach,
    items,
    ngay_lap,
    nguon=NGUON_QUAY,
    trang_thai=TT_HOAN_TAT,
    ghi_chu=None,
    ma_nv=None,
    pttt="Tiền mặt",
    so_tien_nhan=None,
):
    if pttt not in ("Tiền mặt", "Chuyển khoản"):
        raise BusinessError("Phương thức thanh toán phải là Tiền mặt hoặc Chuyển khoản.")
    if nguon == NGUON_QUAY and not ma_nv:
        raise BusinessError("Thiếu thông tin nhân viên lập phiếu bán hàng.")

    ngay_chuan = parse_date(ngay_lap, "Ngày lập")
    _check_not_locked_period(conn, ngay_chuan)
    # Giữ nguyên giờ:phút nếu có (VD đơn online), ngược lại lưu YYYY-MM-DD
    ngay_luu = ngay_lap.strip() if len(str(ngay_lap).strip()) > 10 else ngay_chuan

    gop = {}
    for it in items:
        ma_sp = (it.get("MaSP") or "").strip()
        if not ma_sp:
            continue
        sl = to_float(it.get("SoLuong"))
        if sl is None or sl <= 0:
            raise BusinessError("Số lượng bán phải lớn hơn 0.")
        gop[ma_sp] = round(gop.get(ma_sp, 0.0) + sl, 3)
    if not gop:
        raise BusinessError("Phiếu bán hàng phải có ít nhất một sản phẩm.")

    ten_kh = ((khach or {}).get("ten") or "").strip() or "Khách lẻ"
    sdt = ((khach or {}).get("sdt") or "").strip().replace(" ", "") or None
    dia_chi = ((khach or {}).get("dia_chi") or "").strip() or None

    try:
        lines = []
        for ma_sp, sl in gop.items():
            sp = repo.get_product(conn, ma_sp)
            if sp is None:
                raise BusinessError(f"Sản phẩm mã “{ma_sp}” không tồn tại.")
            if sp["TinhTrang"] != "Đang kinh doanh":
                raise BusinessError(f"Sản phẩm “{sp['TenSP']}” hiện đã ngừng kinh doanh.")
            if nguon == NGUON_ONLINE and not sp["HienThi"]:
                raise BusinessError(f"Sản phẩm “{sp['TenSP']}” hiện không mở bán trực tuyến.")
            if sp["SoLuongTon"] + 1e-9 < sl:
                raise BusinessError(
                    f"“{sp['TenSP']}” chỉ còn {sp['SoLuongTon']:g} {sp['TenDVT']} trong kho, không đủ để bán."
                )
            don_gia_ban = sp["DonGiaBan"]
            if don_gia_ban <= 0:
                raise BusinessError(f"“{sp['TenSP']}” chưa có đơn giá bán hợp lệ (chưa có đơn giá mua).")
            lines.append((ma_sp, sl, don_gia_ban, round(sl * don_gia_ban, 2)))

        tong_tien = round(sum(x[3] for x in lines), 2)
        if nguon == NGUON_QUAY:
            if pttt == "Tiền mặt":
                nhan = to_float(so_tien_nhan) if so_tien_nhan not in (None, "") else tong_tien
                if nhan is None or nhan + 1e-6 < tong_tien:
                    raise BusinessError(
                        f"Số tiền khách đưa ({format_vnd(nhan or 0)}) nhỏ hơn tổng tiền thanh toán ({format_vnd(tong_tien)})."
                    )
                nhan = round(nhan, 2)
            else:
                nhan = tong_tien
        else:
            nhan = tong_tien if trang_thai == TT_HOAN_TAT else 0.0

        so_phieu = repo.next_code(conn, "PHIEUBANHANG", "SoPhieuBan", _voucher_prefix("PB", ngay_chuan), width=3)
        repo.insert_sale(conn, {
            "SoPhieuBan": so_phieu,
            "NgayLap": ngay_luu,
            "TenKhachHang": ten_kh,
            "MaNV_Lap": ma_nv,
            "PhuongThucThanhToan": pttt,
            "TongTien": tong_tien,
            "SoTienNhan": nhan,
            "SoDienThoai": sdt,
            "DiaChi": dia_chi,
            "Nguon": nguon,
            "TrangThai": trang_thai,
            "GhiChu": (ghi_chu or "").strip() or None,
        })
        for idx, (ma_sp, sl, dg, _tt) in enumerate(lines, start=1):
            repo.insert_sale_line(conn, so_phieu, idx, ma_sp, sl, dg)
            if not repo.decrease_stock_atomic(conn, ma_sp, sl):
                raise BusinessError("Tồn kho vừa thay đổi bởi giao dịch khác, vui lòng kiểm tra lại.")
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def lay_danh_sach_phieu_ban(conn, q="", nguon="", trang_thai="", pttt="", tu_ngay="", den_ngay=""):
    rows = repo.list_sales(
        conn, q=q, nguon=nguon, trang_thai=trang_thai, pttt=pttt, tu_ngay=tu_ngay, den_ngay=den_ngay
    )
    tong = sum(r["TongTien"] for r in rows if r["TrangThai"] != TT_HUY)
    return rows, tong


def lay_phieu_ban(conn, so_phieu):
    return repo.get_sale(conn, so_phieu)


def hoan_tat_phieu_ban(conn, so_phieu, ma_nv):
    p, _ = repo.get_sale(conn, so_phieu)
    if p is None:
        raise BusinessError("Không tìm thấy phiếu bán hàng.")
    if p["TrangThai"] != TT_CHO:
        raise BusinessError("Chỉ xác nhận hoàn tất được đơn đang ở trạng thái Chờ xử lý.")
    _check_not_locked_period(conn, p["NgayLap"])
    repo.update_sale_complete(conn, so_phieu, ma_nv)
    conn.commit()


def huy_phieu_ban(conn, so_phieu):
    p, lines = repo.get_sale(conn, so_phieu)
    if p is None:
        raise BusinessError("Không tìm thấy phiếu bán hàng.")
    if p["TrangThai"] == TT_HUY:
        raise BusinessError("Phiếu bán hàng này đã được hủy trước đó.")
    _check_not_locked_period(conn, p["NgayLap"])
    try:
        for ct in lines:
            repo.restore_stock(conn, ct["MaSP"], ct["SoLuong"])
        repo.update_sale_cancel(conn, so_phieu)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ------------------------------------------------------------------ PHIẾU DỊCH VỤ & THU TIỀN & TIẾN ĐỘ
def tao_phieu_dich_vu(conn, khach, items, ngay_lap, ma_nv, hinh_thuc="Tiền mặt"):
    if not ma_nv:
        raise BusinessError("Thiếu thông tin nhân viên tiếp nhận dịch vụ.")
    ten_kh = ((khach or {}).get("ten") or "").strip()
    sdt = ((khach or {}).get("sdt") or "").strip().replace(" ", "")
    if not ten_kh:
        raise BusinessError("Vui lòng nhập họ tên khách hàng.")
    if not sdt:
        raise BusinessError("Vui lòng nhập số điện thoại liên hệ của khách hàng.")

    ngay_chuan = parse_date(ngay_lap, "Ngày lập")
    _check_not_locked_period(conn, ngay_chuan)
    if hinh_thuc not in ("Tiền mặt", "Chuyển khoản"):
        hinh_thuc = "Tiền mặt"

    ti_le = float(repo.get_tham_so(conn)["TiLeTraTruoc"])  # dạng thập phân 0..1 (VD: 0.5)

    lines = []
    for it in items:
        ma_dv = (it.get("MaDichVu") or "").strip()
        if not ma_dv:
            continue
        dv = repo.get_service(conn, ma_dv)
        if dv is None:
            raise BusinessError(f"Dịch vụ mã “{ma_dv}” không tồn tại.")
        if dv["TinhTrang"] != "Đang hoạt động":
            raise BusinessError(f"Dịch vụ “{dv['TenDichVu']}” hiện đã ngừng hoạt động.")
        sl = to_int(it.get("SoLuong"))
        cpr = to_float(it.get("ChiPhiRieng") or 0)
        tra = to_float(it.get("TraTruoc"))
        if not sl or sl <= 0:
            raise BusinessError(f"“{dv['TenDichVu']}”: số lượng dịch vụ phải là số nguyên dương.")
        if cpr is None or cpr < 0:
            raise BusinessError(f"“{dv['TenDichVu']}”: chi phí riêng không được âm.")
        if tra is None or tra < 0:
            raise BusinessError(f"“{dv['TenDichVu']}”: vui lòng nhập số tiền trả trước hợp lệ.")
        ngay_giao = parse_date(it.get("NgayGiaoDuKien"), f"“{dv['TenDichVu']}”: ngày giao dự kiến")
        if ngay_giao < ngay_chuan:
            raise BusinessError(f"“{dv['TenDichVu']}”: ngày giao dự kiến không được trước ngày lập phiếu.")

        dg_co_ban = round(float(dv["DonGiaCoBan"]), 2)
        cpr = round(cpr, 2)
        tra = round(tra, 2)
        thanh_tien = round(sl * (dg_co_ban + cpr), 2)
        toi_thieu = round(thanh_tien * ti_le, 2)
        if tra + 1e-6 < toi_thieu:
            raise BusinessError(
                f"“{dv['TenDichVu']}”: tiền trả trước phải đạt tối thiểu {format_vnd(toi_thieu)} "
                f"({round(ti_le * 100, 2):g}% thành tiền)."
            )
        if tra > thanh_tien + 1e-6:
            raise BusinessError(f"“{dv['TenDichVu']}”: tiền trả trước không được vượt quá thành tiền.")
        ghi_chu_dong = (it.get("GhiChu") or "").strip() or None
        lines.append((ma_dv, dg_co_ban, cpr, sl, tra, ngay_giao, ghi_chu_dong))

    if not lines:
        raise BusinessError("Phiếu dịch vụ phải có ít nhất một hạng mục dịch vụ.")

    try:
        so_phieu = repo.next_code(conn, "PHIEUDICHVU", "SoPhieuDV", _voucher_prefix("PDV", ngay_chuan), width=3)
        repo.insert_service_voucher(conn, so_phieu, ngay_chuan, ten_kh, sdt, ma_nv, ti_le)
        tong_tra = 0.0
        for idx, ln in enumerate(lines, start=1):
            repo.insert_service_line(conn, so_phieu, idx, *ln)
            tong_tra += ln[4]
        tong_tra = round(tong_tra, 2)
        if tong_tra > 0:
            ma_thu = repo.next_code(conn, "THUTIENDICHVU", "MaPhieuThuDV", _voucher_prefix("PTDV", ngay_chuan), width=3)
            repo.insert_service_receipt(
                conn, ma_thu, so_phieu, ngay_chuan, tong_tra,
                "Thu trả trước", hinh_thuc, ma_nv, "Thu tiền đặt trước khi tiếp nhận phiếu dịch vụ",
            )
        conn.commit()
        return so_phieu
    except Exception:
        conn.rollback()
        raise


def lay_danh_sach_phieu_dich_vu(conn, q="", tinh_trang="", tu_ngay="", den_ngay=""):
    rows = repo.list_service_vouchers(conn, q=q, tinh_trang=tinh_trang, tu_ngay=tu_ngay, den_ngay=den_ngay)
    tong = sum(r["TongTien"] for r in rows)
    return rows, tong


def lay_phieu_dich_vu(conn, so_phieu):
    return repo.get_service_voucher(conn, so_phieu)


def thu_tien_dich_vu(conn, so_phieu, so_tien, hinh_thuc="Tiền mặt", ma_nv=None, ghi_chu=None, ngay_thu=None):
    if not ma_nv:
        raise BusinessError("Thiếu thông tin nhân viên thu tiền.")
    p, _, _, _ = repo.get_service_voucher(conn, so_phieu)
    if p is None:
        raise BusinessError("Không tìm thấy phiếu dịch vụ.")
    so_tien_val = to_float(so_tien)
    if so_tien_val is None or so_tien_val <= 0:
        raise BusinessError("Số tiền thu phải lớn hơn 0.")
    if hinh_thuc not in ("Tiền mặt", "Chuyển khoản"):
        hinh_thuc = "Tiền mặt"

    con_phai_thu = round(p["TongTien"] - p["DaThu"], 2)
    if so_tien_val > con_phai_thu + 1e-6:
        raise BusinessError(
            f"Số tiền thu ({format_vnd(so_tien_val)}) vượt quá số tiền còn phải thu ({format_vnd(con_phai_thu)})."
        )

    ngay_str = ngay_thu or datetime.now().strftime("%Y-%m-%d %H:%M")
    _check_not_locked_period(conn, ngay_str)
    ma_thu = repo.next_code(conn, "THUTIENDICHVU", "MaPhieuThuDV", _voucher_prefix("PTDV", ngay_str), width=3)
    repo.insert_service_receipt(
        conn, ma_thu, so_phieu, ngay_str, round(so_tien_val, 2),
        "Thu phần còn lại", hinh_thuc, ma_nv, (ghi_chu or "").strip() or None,
    )
    conn.commit()
    return ma_thu


def cap_nhat_tinh_trang_dich_vu(
    conn, ma_chi_tiet, tinh_trang_moi, ma_nv, co_quyen_chuyen_nguoc=False, ly_do=None, ghi_chu=None
):
    ct = repo.get_service_line(conn, ma_chi_tiet)
    if ct is None:
        raise BusinessError("Không tìm thấy dòng dịch vụ cần cập nhật.")
    cu = ct["TinhTrang"]
    if tinh_trang_moi not in (DV_CHUA_GIAO, DV_DA_GIAO):
        raise BusinessError("Tình trạng mới không hợp lệ.")
    if cu == tinh_trang_moi:
        raise BusinessError(f"Hạng mục này hiện đã ở trạng thái “{tinh_trang_moi}”.")

    ly_do_s = (ly_do or "").strip() or None
    if cu == DV_DA_GIAO and tinh_trang_moi == DV_CHUA_GIAO:
        if not co_quyen_chuyen_nguoc:
            raise BusinessError("Bạn không có quyền chuyển ngược trạng thái từ “Đã giao” về “Chưa giao”.")
        if not ly_do_s:
            raise BusinessError("Bắt buộc phải nhập lý do khi chuyển ngược trạng thái từ “Đã giao” về “Chưa giao”.")

    ghi_chu_s = ghi_chu.strip() or None if ghi_chu is not None else None
    try:
        repo.update_service_line_status(conn, ma_chi_tiet, tinh_trang_moi, ghi_chu=ghi_chu_s)
        repo.insert_status_history(
            conn, ma_chi_tiet, ma_nv, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cu, tinh_trang_moi, ly_do_s
        )
        conn.commit()
        return ct["SoPhieuDV"]
    except Exception:
        conn.rollback()
        raise


def lay_bang_tien_do_dich_vu(conn, q="", tinh_trang=DV_CHUA_GIAO):
    return repo.list_service_status_items(conn, q=q, tinh_trang=tinh_trang)
