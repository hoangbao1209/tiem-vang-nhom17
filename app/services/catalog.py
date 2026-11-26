"""Tầng Nghiệp vụ (Business Layer): Quản lý danh mục dùng chung & Tra cứu tồn kho.
Bao gồm: Đơn vị tính, Loại sản phẩm (% lợi nhuận), Sản phẩm, Nhà cung cấp, Dịch vụ.
"""
import sqlite3
from datetime import datetime

from .. import repositories as repo
from ..utils import BusinessError, to_float

SORTS_SHOP = {
    "moi": "sp.MaSP DESC",
    "gia-tang": "DonGiaBan ASC",
    "gia-giam": "DonGiaBan DESC",
    "ten": "sp.TenSP ASC",
}
SORT_LABELS = [
    ("moi", "Mới nhất"),
    ("gia-tang", "Giá tăng dần"),
    ("gia-giam", "Giá giảm dần"),
    ("ten", "Tên A → Z"),
]


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------ ĐƠN VỊ TÍNH
def lay_danh_sach_dvt(conn):
    return repo.list_units(conn)


def luu_don_vi_tinh(conn, ma_dvt, ten_dvt, ma_nv):
    ten = (ten_dvt or "").strip()
    if not ten:
        raise BusinessError("Tên đơn vị tính không được để trống.")
    ma = (ma_dvt or "").strip().upper()
    try:
        if ma:
            old = repo.get_unit(conn, ma)
            if old is None:
                raise BusinessError(f"Không tìm thấy đơn vị tính mã {ma}.")
            repo.update_unit(conn, ma, ten)
            if old["TenDVT"] != ten:
                repo.insert_rule_log(
                    conn, "Đơn vị tính", ma, old["TenDVT"], ten, _now_str(), ma_nv, "Cập nhật tên đơn vị tính"
                )
        else:
            ma = repo.next_code(conn, "DONVITINH", "MaDVT", "DVT", width=2)
            repo.insert_unit(conn, ma, ten)
            repo.insert_rule_log(
                conn, "Đơn vị tính", ma, None, ten, _now_str(), ma_nv, "Thêm mới đơn vị tính"
            )
        conn.commit()
        return ma
    except sqlite3.IntegrityError:
        conn.rollback()
        raise BusinessError(f"Đơn vị tính “{ten}” đã tồn tại trong hệ thống.")


def xoa_don_vi_tinh(conn, ma_dvt):
    if repo.count_categories_by_unit(conn, ma_dvt) > 0:
        raise BusinessError("Đơn vị tính đang được sử dụng bởi loại sản phẩm, không thể xóa.")
    repo.delete_unit(conn, ma_dvt)
    conn.commit()


# ------------------------------------------------------------------ LOẠI SẢN PHẨM
def lay_danh_sach_loai_sp(conn):
    return repo.list_categories(conn)


def lay_loai_sp(conn, ma_loai):
    return repo.get_category(conn, ma_loai) if ma_loai else None


def luu_loai_san_pham(conn, ma_loai, ten_loai, ma_dvt, phan_tram_pct, ma_nv):
    """Nhận phan_tram_pct ở dạng % (VD: 15), lưu thập phân (0.15) theo thiết kế bảng LOAISANPHAM."""
    ten = (ten_loai or "").strip()
    if not ten:
        raise BusinessError("Tên loại sản phẩm không được để trống.")
    if not ma_dvt or repo.get_unit(conn, ma_dvt) is None:
        raise BusinessError("Vui lòng chọn đơn vị tính hợp lệ.")
    pt_val = to_float(phan_tram_pct)
    if pt_val is None or pt_val < 0 or pt_val > 500:
        raise BusinessError("Tỷ lệ phần trăm lợi nhuận phải từ 0% đến 500%.")
    pt_decimal = round(pt_val / 100.0, 6)
    ma = (ma_loai or "").strip().upper()
    try:
        if ma:
            old = repo.get_category(conn, ma)
            if old is None:
                raise BusinessError(f"Không tìm thấy loại sản phẩm mã {ma}.")
            repo.update_category(conn, ma, ten, ma_dvt, pt_decimal)
            old_desc = f"{old['TenLoaiSP']} | ĐVT: {old['MaDVT']} | Lợi nhuận: {round(old['PhanTramLoiNhuan']*100, 2):g}%"
            new_desc = f"{ten} | ĐVT: {ma_dvt} | Lợi nhuận: {pt_val:g}%"
            if old_desc != new_desc:
                repo.insert_rule_log(
                    conn, "Loại sản phẩm", ma, old_desc, new_desc, _now_str(), ma_nv,
                    "Cập nhật thông tin / tỷ lệ lợi nhuận loại sản phẩm",
                )
        else:
            ma = repo.next_code(conn, "LOAISANPHAM", "MaLoaiSP", "LSP", width=2)
            repo.insert_category(conn, ma, ten, ma_dvt, pt_decimal)
            repo.insert_rule_log(
                conn, "Loại sản phẩm", ma, None, f"{ten} ({pt_val:g}%)", _now_str(), ma_nv,
                "Thêm mới loại sản phẩm",
            )
        conn.commit()
        return ma
    except sqlite3.IntegrityError:
        conn.rollback()
        raise BusinessError(f"Loại sản phẩm “{ten}” đã tồn tại.")


def xoa_loai_san_pham(conn, ma_loai):
    if repo.count_products_by_category(conn, ma_loai) > 0:
        raise BusinessError("Loại sản phẩm đã có sản phẩm liên kết, không thể xóa.")
    repo.delete_category(conn, ma_loai)
    conn.commit()


# ------------------------------------------------------------------ SẢN PHẨM & TRA CỨU TỒN KHO
def lay_san_pham(conn, ma_sp):
    return repo.get_product(conn, ma_sp)


def tra_cuu_san_pham_cua_hang(conn, q="", ma_loai="", sort="moi", con_hang=False):
    order_by = SORTS_SHOP.get(sort, SORTS_SHOP["moi"])
    return repo.list_products(
        conn, q=q, ma_loai=ma_loai, only_visible=True, only_in_stock=con_hang, order_by=order_by
    )


def lay_san_pham_noi_bat(conn, limit=8):
    return repo.list_products(
        conn, only_visible=True, only_in_stock=True, order_by="sp.MaSP DESC", limit=limit
    )


def lay_san_pham_lien_quan(conn, ma_loai, exclude_ma_sp, limit=4):
    return repo.list_related_products(conn, ma_loai, exclude_ma_sp, limit=limit)


def tra_cuu_san_pham_quan_ly(conn, q="", ma_loai="", tinh_trang="", stock_filter="", min_ton=2):
    return repo.list_products(
        conn, q=q, ma_loai=ma_loai, tinh_trang=tinh_trang,
        stock_filter=stock_filter, min_ton_warning=min_ton, order_by="sp.MaSP ASC",
    )


def lay_san_pham_dang_kinh_doanh(conn, only_in_stock=False):
    return repo.list_products(
        conn, tinh_trang="Đang kinh doanh", only_in_stock=only_in_stock, order_by="sp.MaSP ASC"
    )


def luu_san_pham(conn, ma_sp_hien_tai, form_data, uploaded_image=None):
    ma_nhap = (form_data.get("MaSP") or "").strip().upper()
    ten = (form_data.get("TenSP") or "").strip()
    ma_loai = (form_data.get("MaLoaiSP") or "").strip()
    don_gia_mua = to_float(form_data.get("DonGiaMua"), 0)
    tinh_trang = form_data.get("TinhTrang") or "Đang kinh doanh"
    if tinh_trang not in ("Đang kinh doanh", "Ngừng kinh doanh"):
        tinh_trang = "Đang kinh doanh"

    if not ten:
        raise BusinessError("Vui lòng nhập tên sản phẩm.")
    if not ma_loai or repo.get_category(conn, ma_loai) is None:
        raise BusinessError("Vui lòng chọn loại sản phẩm hợp lệ.")
    if don_gia_mua is None or don_gia_mua < 0:
        raise BusinessError("Đơn giá mua phải là số không âm.")

    hien_thi = 1 if (form_data.get("HienThi") == "1" and tinh_trang == "Đang kinh doanh") else 0
    existing = repo.get_product(conn, ma_sp_hien_tai) if ma_sp_hien_tai else None
    hinh_chon = (form_data.get("HinhAnhChon") or "").strip()
    hinh = uploaded_image or hinh_chon or (existing["HinhAnh"] if existing else "img/products/gem.svg")

    payload = {
        "TenSP": ten,
        "MaLoaiSP": ma_loai,
        "DonGiaMua": round(don_gia_mua, 2),
        "TinhTrang": tinh_trang,
        "ChatLieu": (form_data.get("ChatLieu") or "").strip() or None,
        "TuoiVang": (form_data.get("TuoiVang") or "").strip() or None,
        "TrongLuong": (form_data.get("TrongLuong") or "").strip() or None,
        "BaoHanh": (form_data.get("BaoHanh") or "").strip() or "Bảo hành làm sạch & đánh bóng miễn phí trọn đời",
        "MoTa": (form_data.get("MoTa") or "").strip() or None,
        "HinhAnh": hinh,
        "HienThi": hien_thi,
    }

    try:
        if existing is None:
            ma_moi = ma_nhap or repo.next_code(conn, "SANPHAM", "MaSP", "SP", width=3)
            if repo.get_product(conn, ma_moi) is not None:
                raise BusinessError(f"Mã sản phẩm “{ma_moi}” đã tồn tại, vui lòng nhập mã khác.")
            payload["MaSP"] = ma_moi
            repo.insert_product(conn, payload)
            conn.commit()
            return ma_moi, False
        else:
            repo.update_product(conn, existing["MaSP"], payload)
            conn.commit()
            return existing["MaSP"], True
    except sqlite3.IntegrityError:
        conn.rollback()
        raise BusinessError("Mã sản phẩm đã tồn tại hoặc dữ liệu không hợp lệ.")


def doi_trang_thai_san_pham(conn, ma_sp):
    sp = repo.get_product(conn, ma_sp)
    if sp is None:
        raise BusinessError("Không tìm thấy sản phẩm.")
    moi = "Ngừng kinh doanh" if sp["TinhTrang"] == "Đang kinh doanh" else "Đang kinh doanh"
    hien_thi = 0 if moi == "Ngừng kinh doanh" else 1
    repo.update_product_status(conn, ma_sp, moi, hien_thi)
    conn.commit()
    return sp["TenSP"], moi


def xoa_san_pham(conn, ma_sp):
    sp = repo.get_product(conn, ma_sp)
    if sp is None:
        raise BusinessError("Không tìm thấy sản phẩm.")
    if sp["DaPhatSinh"]:
        raise BusinessError(
            f"Sản phẩm “{sp['TenSP']}” đã phát sinh chứng từ mua/bán/kiểm kê nên không thể xóa vật lý. "
            "Vui lòng chuyển sang trạng thái “Ngừng kinh doanh” để bảo toàn dữ liệu lịch sử."
        )
    repo.delete_product(conn, ma_sp)
    conn.commit()
    return sp["TenSP"]


# ------------------------------------------------------------------ NHÀ CUNG CẤP
def lay_danh_sach_ncc(conn, q="", tinh_trang=""):
    return repo.list_suppliers(conn, q=q, tinh_trang=tinh_trang)


def luu_nha_cung_cap(conn, ma_ncc, ten, dia_chi, sdt, tinh_trang):
    ten = (ten or "").strip()
    if not ten:
        raise BusinessError("Vui lòng nhập tên nhà cung cấp.")
    tt = tinh_trang if tinh_trang in ("Đang hợp tác", "Ngừng hợp tác") else "Đang hợp tác"
    ma = (ma_ncc or "").strip().upper()
    if ma and repo.get_supplier(conn, ma) is not None:
        repo.update_supplier(conn, ma, ten, (dia_chi or "").strip() or None, (sdt or "").strip() or None, tt)
    else:
        ma = ma or repo.next_code(conn, "NHACUNGCAP", "MaNCC", "NCC", width=3)
        if repo.get_supplier(conn, ma) is not None:
            raise BusinessError(f"Mã nhà cung cấp “{ma}” đã tồn tại.")
        repo.insert_supplier(conn, ma, ten, (dia_chi or "").strip() or None, (sdt or "").strip() or None, tt)
    conn.commit()
    return ma


def xoa_nha_cung_cap(conn, ma_ncc):
    ncc = repo.get_supplier(conn, ma_ncc)
    if ncc is None:
        raise BusinessError("Không tìm thấy nhà cung cấp.")
    if repo.count_purchases_by_supplier(conn, ma_ncc) > 0:
        raise BusinessError(
            f"Nhà cung cấp “{ncc['TenNCC']}” đã xuất hiện trong phiếu mua hàng nên không thể xóa vật lý. "
            "Hãy chuyển sang trạng thái “Ngừng hợp tác”."
        )
    repo.delete_supplier(conn, ma_ncc)
    conn.commit()
    return ncc["TenNCC"]


# ------------------------------------------------------------------ DỊCH VỤ
def lay_danh_sach_dich_vu(conn, q="", tinh_trang=""):
    return repo.list_services(conn, q=q, tinh_trang=tinh_trang)


def luu_dich_vu(conn, ma_dv, ten_dv, don_gia, tinh_trang, ma_nv):
    ten = (ten_dv or "").strip()
    dg = to_float(don_gia)
    if not ten:
        raise BusinessError("Tên dịch vụ không được để trống.")
    if dg is None or dg < 0:
        raise BusinessError("Đơn giá cơ bản phải là số không âm.")
    tt = tinh_trang if tinh_trang in ("Đang hoạt động", "Ngừng hoạt động") else "Đang hoạt động"
    ma = (ma_dv or "").strip().upper()
    try:
        if ma and repo.get_service(conn, ma) is not None:
            old = repo.get_service(conn, ma)
            repo.update_service(conn, ma, ten, round(dg, 2), tt)
            old_desc = f"{old['TenDichVu']} | {old['DonGiaCoBan']:,.0f} ₫ | {old['TinhTrang']}"
            new_desc = f"{ten} | {dg:,.0f} ₫ | {tt}"
            if old_desc != new_desc:
                repo.insert_rule_log(
                    conn, "Dịch vụ", ma, old_desc, new_desc, _now_str(), ma_nv,
                    "Cập nhật tên / đơn giá cơ bản dịch vụ (chỉ áp dụng cho phiếu mới)",
                )
        else:
            ma = ma or repo.next_code(conn, "DICHVU", "MaDichVu", "DV", width=3)
            if repo.get_service(conn, ma) is not None:
                raise BusinessError(f"Mã dịch vụ “{ma}” đã tồn tại.")
            repo.insert_service(conn, ma, ten, round(dg, 2), tt)
            repo.insert_rule_log(
                conn, "Dịch vụ", ma, None, f"{ten} | {dg:,.0f} ₫", _now_str(), ma_nv,
                "Thêm mới dịch vụ",
            )
        conn.commit()
        return ma
    except sqlite3.IntegrityError:
        conn.rollback()
        raise BusinessError(f"Dịch vụ “{ten}” đã tồn tại trong danh sách.")


def xoa_dich_vu(conn, ma_dv):
    dv = repo.get_service(conn, ma_dv)
    if dv is None:
        raise BusinessError("Không tìm thấy dịch vụ.")
    if repo.count_service_usage(conn, ma_dv) > 0:
        raise BusinessError(
            f"Dịch vụ “{dv['TenDichVu']}” đã phát sinh trong phiếu dịch vụ nên không thể xóa vật lý. "
            "Hãy chuyển sang trạng thái “Ngừng hoạt động”."
        )
    repo.delete_service(conn, ma_dv)
    conn.commit()
    return dv["TenDichVu"]
