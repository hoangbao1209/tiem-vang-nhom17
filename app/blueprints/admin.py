"""Phân hệ quản lý cửa hàng: phiếu mua/bán/dịch vụ, danh mục, báo cáo, quy định."""
import os
import sqlite3
import uuid
from datetime import date

from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template,
                   request, url_for)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from ..auth import admin_required, is_admin, login_required
from ..db import get_db
from ..services.catalog import PRODUCT_SELECT, get_product
from ..services.reports import bao_cao_doanh_thu, bao_cao_ton_kho
from ..services.settings import PARAM_LABELS, get_params, set_param
from ..services.vouchers import (NGUON_QUAY, PDV_CHUA_XONG, TT_CHO, TT_HOAN_TAT, TT_HUY,
                                 giao_dich_vu, hoan_tat_phieu_ban, huy_phieu_ban,
                                 lay_phieu_ban, lay_phieu_dich_vu, lay_phieu_mua,
                                 tao_phieu_ban, tao_phieu_dich_vu, tao_phieu_mua)
from ..utils import BusinessError, rows_from_form, to_float, to_int, validate_ngay_lap

bp = Blueprint("admin", __name__, url_prefix="/quan-ly")

STOCK_IMAGES = [
    ("img/products/gold-bar.svg", "Vàng miếng / Nhẫn tròn"),
    ("img/products/ring.svg", "Nhẫn"),
    ("img/products/necklace.svg", "Dây chuyền"),
    ("img/products/earring.svg", "Bông tai"),
    ("img/products/bracelet.svg", "Lắc / Vòng tay"),
    ("img/products/gem.svg", "Đá quý / Kim cương"),
    ("img/products/silver.svg", "Trang sức bạc"),
]


def _save_uploaded_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in current_app.config["ALLOWED_IMAGE_EXT"]:
        raise BusinessError("Định dạng ảnh không hợp lệ (chỉ nhận png, jpg, jpeg, gif, webp).")
    new_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], new_name)
    file_storage.save(dest)
    return f"uploads/{new_name}"


# ------------------------------------------------------------------ TỔNG QUAN
@bp.route("/")
@login_required
def dashboard():
    db = get_db()
    today = date.today()
    ym = f"{today.year:04d}-{today.month:02d}"
    params = get_params(db)
    min_ton = to_int(params.get("SoLuongTonToiThieu"), 2) or 2

    dt_ban = db.execute(
        "SELECT COALESCE(SUM(TongTien), 0) FROM PHIEUBANHANG WHERE TrangThai <> ? AND substr(NgayLap, 1, 7) = ?",
        (TT_HUY, ym),
    ).fetchone()[0]
    dt_dv = db.execute(
        "SELECT COALESCE(SUM(TongTien), 0) FROM PHIEUDICHVU WHERE substr(NgayLap, 1, 7) = ?",
        (ym,),
    ).fetchone()[0]
    don_cho = db.execute(
        "SELECT COUNT(*) FROM PHIEUBANHANG WHERE TrangThai = ?", (TT_CHO,)
    ).fetchone()[0]
    dv_chua_xong = db.execute(
        "SELECT COUNT(*) FROM PHIEUDICHVU WHERE TinhTrang = ?", (PDV_CHUA_XONG,)
    ).fetchone()[0]

    low_stock = db.execute(
        PRODUCT_SELECT + " WHERE sp.SoLuongTon <= ? ORDER BY sp.SoLuongTon ASC, sp.MaSP ASC LIMIT 8",
        (min_ton,),
    ).fetchall()
    pending_orders = db.execute(
        "SELECT p.*, k.TenKH, k.SoDienThoai FROM PHIEUBANHANG p "
        "JOIN KHACHHANG k ON k.MaKH = p.MaKH WHERE p.TrangThai = ? ORDER BY p.SoPhieu DESC LIMIT 6",
        (TT_CHO,),
    ).fetchall()
    recent_sales = db.execute(
        "SELECT p.*, k.TenKH FROM PHIEUBANHANG p JOIN KHACHHANG k ON k.MaKH = p.MaKH "
        "ORDER BY p.SoPhieu DESC LIMIT 6"
    ).fetchall()
    recent_services = db.execute(
        "SELECT p.*, k.TenKH FROM PHIEUDICHVU p JOIN KHACHHANG k ON k.MaKH = p.MaKH "
        "ORDER BY p.SoPhieu DESC LIMIT 6"
    ).fetchall()

    return render_template(
        "admin/dashboard.html",
        thang=today.month,
        nam=today.year,
        dt_ban=dt_ban,
        dt_dv=dt_dv,
        don_cho=don_cho,
        dv_chua_xong=dv_chua_xong,
        min_ton=min_ton,
        low_stock=low_stock,
        pending_orders=pending_orders,
        recent_sales=recent_sales,
        recent_services=recent_services,
    )


# ------------------------------------------------------------------ BM1: PHIẾU MUA HÀNG
@bp.route("/phieu-mua")
@login_required
def purchases():
    db = get_db()
    q = request.args.get("q", "").strip()
    tu_ngay = request.args.get("tu_ngay", "").strip()
    den_ngay = request.args.get("den_ngay", "").strip()

    where, args = ["1=1"], []
    if q:
        where.append("(n.TenNCC LIKE ? OR CAST(p.SoPhieu AS TEXT) = ?)")
        args += [f"%{q}%", q]
    if tu_ngay:
        where.append("substr(p.NgayLap, 1, 10) >= ?")
        args.append(tu_ngay)
    if den_ngay:
        where.append("substr(p.NgayLap, 1, 10) <= ?")
        args.append(den_ngay)

    rows = db.execute(
        "SELECT p.*, n.TenNCC, n.SoDienThoai, "
        "(SELECT COUNT(*) FROM CT_PHIEUMUAHANG c WHERE c.SoPhieu = p.SoPhieu) AS SoMatHang "
        "FROM PHIEUMUAHANG p JOIN NHACUNGCAP n ON n.MaNCC = p.MaNCC "
        "WHERE " + " AND ".join(where) + " ORDER BY p.SoPhieu DESC",
        args,
    ).fetchall()
    tong = sum(r["TongTien"] for r in rows)
    return render_template("admin/purchases.html", rows=rows, tong=tong,
                           q=q, tu_ngay=tu_ngay, den_ngay=den_ngay)


@bp.route("/phieu-mua/lap", methods=["GET", "POST"])
@login_required
def purchase_create():
    db = get_db()
    suppliers = db.execute("SELECT * FROM NHACUNGCAP ORDER BY TenNCC").fetchall()
    products = db.execute(PRODUCT_SELECT + " ORDER BY sp.TenSP").fetchall()

    if request.method == "POST":
        ma_ncc = to_int(request.form.get("MaNCC"))
        ngay_lap = request.form.get("NgayLap", "")
        ghi_chu = request.form.get("GhiChu", "").strip()
        items = rows_from_form(request.form, ["MaSP", "SoLuong", "DonGia"])
        try:
            ngay_lap = validate_ngay_lap(ngay_lap)
            so_phieu = tao_phieu_mua(db, ma_ncc, ngay_lap, items, ghi_chu)
        except BusinessError as e:
            flash(str(e), "error")
        else:
            flash(f"Đã lập phiếu mua hàng #{so_phieu} và cập nhật tồn kho.", "success")
            return redirect(url_for("admin.purchase_detail", so_phieu=so_phieu))

    return render_template("admin/purchase_form.html", suppliers=suppliers, products=products)


@bp.route("/phieu-mua/<int:so_phieu>")
@login_required
def purchase_detail(so_phieu):
    p, lines = lay_phieu_mua(get_db(), so_phieu)
    if p is None:
        abort(404)
    return render_template("admin/purchase_detail.html", p=p, lines=lines)


# ------------------------------------------------------------------ BM2: PHIẾU BÁN HÀNG
@bp.route("/phieu-ban")
@login_required
def sales():
    db = get_db()
    q = request.args.get("q", "").strip()
    nguon = request.args.get("nguon", "").strip()
    trang_thai = request.args.get("trang_thai", "").strip()
    tu_ngay = request.args.get("tu_ngay", "").strip()
    den_ngay = request.args.get("den_ngay", "").strip()

    where, args = ["1=1"], []
    if q:
        where.append("(k.TenKH LIKE ? OR k.SoDienThoai LIKE ? OR CAST(p.SoPhieu AS TEXT) = ?)")
        args += [f"%{q}%", f"%{q}%", q]
    if nguon:
        where.append("p.Nguon = ?")
        args.append(nguon)
    if trang_thai:
        where.append("p.TrangThai = ?")
        args.append(trang_thai)
    if tu_ngay:
        where.append("substr(p.NgayLap, 1, 10) >= ?")
        args.append(tu_ngay)
    if den_ngay:
        where.append("substr(p.NgayLap, 1, 10) <= ?")
        args.append(den_ngay)

    rows = db.execute(
        "SELECT p.*, k.TenKH, k.SoDienThoai, "
        "(SELECT COUNT(*) FROM CT_PHIEUBANHANG c WHERE c.SoPhieu = p.SoPhieu) AS SoMatHang "
        "FROM PHIEUBANHANG p JOIN KHACHHANG k ON k.MaKH = p.MaKH "
        "WHERE " + " AND ".join(where) + " ORDER BY p.SoPhieu DESC",
        args,
    ).fetchall()
    tong = sum(r["TongTien"] for r in rows if r["TrangThai"] != TT_HUY)
    return render_template("admin/sales.html", rows=rows, tong=tong,
                           q=q, nguon=nguon, trang_thai=trang_thai,
                           tu_ngay=tu_ngay, den_ngay=den_ngay)


@bp.route("/phieu-ban/lap", methods=["GET", "POST"])
@login_required
def sale_create():
    db = get_db()
    products = db.execute(PRODUCT_SELECT + " WHERE sp.SoLuongTon > 0 ORDER BY sp.TenSP").fetchall()
    customers = db.execute("SELECT * FROM KHACHHANG ORDER BY TenKH").fetchall()

    if request.method == "POST":
        khach = {
            "ten": request.form.get("TenKH", ""),
            "sdt": request.form.get("SoDienThoai", ""),
            "dia_chi": request.form.get("DiaChi", ""),
        }
        ngay_lap = request.form.get("NgayLap", "")
        ghi_chu = request.form.get("GhiChu", "").strip()
        items = rows_from_form(request.form, ["MaSP", "SoLuong"])
        try:
            ngay_lap = validate_ngay_lap(ngay_lap)
            so_phieu = tao_phieu_ban(db, khach, items, ngay_lap,
                                     nguon=NGUON_QUAY, trang_thai=TT_HOAN_TAT, ghi_chu=ghi_chu)
        except BusinessError as e:
            flash(str(e), "error")
        else:
            flash(f"Đã lập phiếu bán hàng #{so_phieu}.", "success")
            return redirect(url_for("admin.sale_detail", so_phieu=so_phieu))

    return render_template("admin/sale_form.html", products=products, customers=customers)


@bp.route("/phieu-ban/<int:so_phieu>")
@login_required
def sale_detail(so_phieu):
    p, lines = lay_phieu_ban(get_db(), so_phieu)
    if p is None:
        abort(404)
    return render_template("admin/sale_detail.html", p=p, lines=lines)


@bp.route("/phieu-ban/<int:so_phieu>/hoan-tat", methods=["POST"])
@login_required
def sale_complete(so_phieu):
    try:
        hoan_tat_phieu_ban(get_db(), so_phieu)
        flash(f"Đã xác nhận hoàn tất đơn hàng #{so_phieu}.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("admin.sale_detail", so_phieu=so_phieu))


@bp.route("/phieu-ban/<int:so_phieu>/huy", methods=["POST"])
@login_required
def sale_cancel(so_phieu):
    try:
        huy_phieu_ban(get_db(), so_phieu)
        flash(f"Đã hủy phiếu #{so_phieu} và hoàn lại tồn kho.", "info")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("admin.sale_detail", so_phieu=so_phieu))


# ------------------------------------------------------------------ BM3: PHIẾU DỊCH VỤ
@bp.route("/phieu-dich-vu")
@login_required
def services_vouchers():
    db = get_db()
    q = request.args.get("q", "").strip()
    tinh_trang = request.args.get("tinh_trang", "").strip()
    tu_ngay = request.args.get("tu_ngay", "").strip()
    den_ngay = request.args.get("den_ngay", "").strip()

    where, args = ["1=1"], []
    if q:
        where.append("(k.TenKH LIKE ? OR k.SoDienThoai LIKE ? OR CAST(p.SoPhieu AS TEXT) = ?)")
        args += [f"%{q}%", f"%{q}%", q]
    if tinh_trang:
        where.append("p.TinhTrang = ?")
        args.append(tinh_trang)
    if tu_ngay:
        where.append("substr(p.NgayLap, 1, 10) >= ?")
        args.append(tu_ngay)
    if den_ngay:
        where.append("substr(p.NgayLap, 1, 10) <= ?")
        args.append(den_ngay)

    rows = db.execute(
        "SELECT p.*, k.TenKH, k.SoDienThoai, "
        "(SELECT COUNT(*) FROM CT_PHIEUDICHVU c WHERE c.SoPhieu = p.SoPhieu) AS SoDV "
        "FROM PHIEUDICHVU p JOIN KHACHHANG k ON k.MaKH = p.MaKH "
        "WHERE " + " AND ".join(where) + " ORDER BY p.SoPhieu DESC",
        args,
    ).fetchall()
    tong = sum(r["TongTien"] for r in rows)
    return render_template("admin/services_vouchers.html", rows=rows, tong=tong,
                           q=q, tinh_trang=tinh_trang, tu_ngay=tu_ngay, den_ngay=den_ngay)


@bp.route("/phieu-dich-vu/lap", methods=["GET", "POST"])
@login_required
def service_create():
    db = get_db()
    service_types = db.execute("SELECT * FROM LOAIDICHVU ORDER BY TenLoaiDV").fetchall()
    customers = db.execute("SELECT * FROM KHACHHANG ORDER BY TenKH").fetchall()

    if request.method == "POST":
        khach = {
            "ten": request.form.get("TenKH", ""),
            "sdt": request.form.get("SoDienThoai", ""),
            "dia_chi": request.form.get("DiaChi", ""),
        }
        ngay_lap = request.form.get("NgayLap", "")
        items = rows_from_form(
            request.form, ["MaLoaiDV", "ChiPhiRieng", "SoLuong", "TraTruoc", "NgayGiao"]
        )
        try:
            ngay_lap = validate_ngay_lap(ngay_lap)
            so_phieu = tao_phieu_dich_vu(db, khach, items, ngay_lap)
        except BusinessError as e:
            flash(str(e), "error")
        else:
            flash(f"Đã lập phiếu dịch vụ #{so_phieu}.", "success")
            return redirect(url_for("admin.service_detail", so_phieu=so_phieu))

    return render_template("admin/service_form.html", service_types=service_types, customers=customers)


@bp.route("/phieu-dich-vu/<int:so_phieu>")
@login_required
def service_detail(so_phieu):
    p, lines = lay_phieu_dich_vu(get_db(), so_phieu)
    if p is None:
        abort(404)
    return render_template("admin/service_detail.html", p=p, lines=lines)


@bp.route("/phieu-dich-vu/giao/<int:ma_ct>", methods=["POST"])
@login_required
def service_deliver_line(ma_ct):
    try:
        so_phieu = giao_dich_vu(get_db(), ma_ct)
        flash("Đã cập nhật giao dịch vụ.", "success")
        return redirect(url_for("admin.service_detail", so_phieu=so_phieu))
    except BusinessError as e:
        flash(str(e), "error")
        return redirect(request.referrer or url_for("admin.services_vouchers"))


# ------------------------------------------------------------------ BM4: BÁO CÁO TỒN KHO & DOANH THU
@bp.route("/bao-cao-ton-kho")
@login_required
def report_inventory():
    today = date.today()
    thang = to_int(request.args.get("thang"), today.month) or today.month
    nam = to_int(request.args.get("nam"), today.year) or today.year
    thang = min(max(thang, 1), 12)
    rows = bao_cao_ton_kho(get_db(), thang, nam)
    return render_template("admin/report_inventory.html", rows=rows, thang=thang, nam=nam)


@bp.route("/bao-cao-doanh-thu")
@login_required
def report_revenue():
    today = date.today()
    thang = to_int(request.args.get("thang"), today.month) or today.month
    nam = to_int(request.args.get("nam"), today.year) or today.year
    thang = min(max(thang, 1), 12)
    days, top = bao_cao_doanh_thu(get_db(), thang, nam)
    tong_ban = sum(d["BanHang"] for d in days)
    tong_dv = sum(d["DichVu"] for d in days)
    return render_template("admin/report_revenue.html", days=days, top=top,
                           thang=thang, nam=nam, tong_ban=tong_ban, tong_dv=tong_dv)


# ------------------------------------------------------------------ QUẢN LÝ SẢN PHẨM
@bp.route("/san-pham")
@login_required
def products_admin():
    db = get_db()
    q = request.args.get("q", "").strip()
    loai = to_int(request.args.get("loai"))
    where, args = ["1=1"], []
    if q:
        where.append("sp.TenSP LIKE ?")
        args.append(f"%{q}%")
    if loai:
        where.append("sp.MaLoaiSP = ?")
        args.append(loai)
    rows = db.execute(
        PRODUCT_SELECT + " WHERE " + " AND ".join(where) + " ORDER BY sp.MaSP DESC", args
    ).fetchall()
    categories = db.execute("SELECT * FROM LOAISANPHAM ORDER BY TenLoaiSP").fetchall()
    return render_template("admin/products.html", rows=rows, categories=categories, q=q, loai=loai)


@bp.route("/san-pham/them", methods=["GET", "POST"])
@bp.route("/san-pham/<int:ma_sp>/sua", methods=["GET", "POST"])
@login_required
def product_edit(ma_sp=None):
    db = get_db()
    sp = get_product(db, ma_sp) if ma_sp else None
    if ma_sp and sp is None:
        abort(404)
    categories = db.execute(
        "SELECT l.*, d.TenDVT FROM LOAISANPHAM l JOIN DONVITINH d ON d.MaDVT = l.MaDVT ORDER BY l.TenLoaiSP"
    ).fetchall()

    if request.method == "POST":
        ten = request.form.get("TenSP", "").strip()
        ma_loai = to_int(request.form.get("MaLoaiSP"))
        don_gia_mua = to_float(request.form.get("DonGiaMua"), 0)
        mo_ta = request.form.get("MoTa", "").strip()
        hien_thi = 1 if request.form.get("HienThi") == "1" else 0
        hinh_chon = request.form.get("HinhAnhChon", "").strip()

        try:
            if not ten:
                raise BusinessError("Vui lòng nhập tên sản phẩm.")
            if not ma_loai:
                raise BusinessError("Vui lòng chọn loại sản phẩm.")
            if don_gia_mua is None or don_gia_mua < 0:
                raise BusinessError("Đơn giá mua không hợp lệ.")
            uploaded = _save_uploaded_image(request.files.get("HinhAnhFile"))
            hinh = uploaded or hinh_chon or (sp["HinhAnh"] if sp else "img/products/gem.svg")

            if sp is None:
                db.execute(
                    "INSERT INTO SANPHAM(TenSP, MaLoaiSP, DonGiaMua, SoLuongTon, MoTa, HinhAnh, HienThi) "
                    "VALUES (?, ?, ?, 0, ?, ?, ?)",
                    (ten, ma_loai, don_gia_mua, mo_ta, hinh, hien_thi),
                )
                db.commit()
                flash(f"Đã thêm sản phẩm “{ten}”. (Nhập hàng qua Phiếu mua hàng để tăng tồn kho.)", "success")
            else:
                db.execute(
                    "UPDATE SANPHAM SET TenSP = ?, MaLoaiSP = ?, DonGiaMua = ?, MoTa = ?, "
                    "HinhAnh = ?, HienThi = ? WHERE MaSP = ?",
                    (ten, ma_loai, don_gia_mua, mo_ta, hinh, hien_thi, ma_sp),
                )
                db.commit()
                flash(f"Đã cập nhật sản phẩm “{ten}”.", "success")
            return redirect(url_for("admin.products_admin"))
        except BusinessError as e:
            flash(str(e), "error")

    return render_template("admin/product_form.html", sp=sp, categories=categories, stock_images=STOCK_IMAGES)


@bp.route("/san-pham/<int:ma_sp>/xoa", methods=["POST"])
@login_required
def product_delete(ma_sp):
    db = get_db()
    try:
        db.execute("DELETE FROM SANPHAM WHERE MaSP = ?", (ma_sp,))
        db.commit()
        flash("Đã xóa sản phẩm.", "success")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("Sản phẩm đã phát sinh phiếu mua/bán nên không thể xóa (bạn có thể tắt Hiển thị).", "error")
    return redirect(url_for("admin.products_admin"))


# ------------------------------------------------------------------ LOẠI SẢN PHẨM & ĐƠN VỊ TÍNH (QĐ1)
@bp.route("/loai-san-pham", methods=["GET", "POST"])
@login_required
def categories_admin():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "save_unit":
                ma = to_int(request.form.get("MaDVT"))
                ten = request.form.get("TenDVT", "").strip()
                if not ten:
                    raise BusinessError("Tên đơn vị tính không được để trống.")
                if ma:
                    db.execute("UPDATE DONVITINH SET TenDVT = ? WHERE MaDVT = ?", (ten, ma))
                else:
                    db.execute("INSERT INTO DONVITINH(TenDVT) VALUES (?)", (ten,))
                db.commit()
                flash("Đã lưu đơn vị tính.", "success")
            elif action == "delete_unit":
                ma = to_int(request.form.get("MaDVT"))
                db.execute("DELETE FROM DONVITINH WHERE MaDVT = ?", (ma,))
                db.commit()
                flash("Đã xóa đơn vị tính.", "success")
            elif action == "save_cat":
                ma = to_int(request.form.get("MaLoaiSP"))
                ten = request.form.get("TenLoaiSP", "").strip()
                ma_dvt = to_int(request.form.get("MaDVT"))
                pt = to_float(request.form.get("PhanTramLoiNhuan"))
                if not ten or not ma_dvt or pt is None or pt < 0:
                    raise BusinessError("Vui lòng nhập đầy đủ tên loại, ĐVT và % lợi nhuận (≥ 0).")
                if ma:
                    db.execute(
                        "UPDATE LOAISANPHAM SET TenLoaiSP = ?, MaDVT = ?, PhanTramLoiNhuan = ? WHERE MaLoaiSP = ?",
                        (ten, ma_dvt, pt, ma),
                    )
                else:
                    db.execute(
                        "INSERT INTO LOAISANPHAM(TenLoaiSP, MaDVT, PhanTramLoiNhuan) VALUES (?, ?, ?)",
                        (ten, ma_dvt, pt),
                    )
                db.commit()
                flash("Đã lưu loại sản phẩm.", "success")
            elif action == "delete_cat":
                ma = to_int(request.form.get("MaLoaiSP"))
                db.execute("DELETE FROM LOAISANPHAM WHERE MaLoaiSP = ?", (ma,))
                db.commit()
                flash("Đã xóa loại sản phẩm.", "success")
        except BusinessError as e:
            flash(str(e), "error")
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Tên bị trùng hoặc mục này đang được sử dụng nên không thể xóa.", "error")
        return redirect(url_for("admin.categories_admin"))

    categories = db.execute(
        "SELECT l.*, d.TenDVT, (SELECT COUNT(*) FROM SANPHAM sp WHERE sp.MaLoaiSP = l.MaLoaiSP) AS SoSP "
        "FROM LOAISANPHAM l JOIN DONVITINH d ON d.MaDVT = l.MaDVT ORDER BY l.MaLoaiSP"
    ).fetchall()
    units = db.execute(
        "SELECT d.*, (SELECT COUNT(*) FROM LOAISANPHAM l WHERE l.MaDVT = d.MaDVT) AS SoLoai "
        "FROM DONVITINH d ORDER BY d.MaDVT"
    ).fetchall()
    return render_template("admin/categories.html", categories=categories, units=units)


# ------------------------------------------------------------------ LOẠI DỊCH VỤ (QĐ3)
@bp.route("/loai-dich-vu", methods=["GET", "POST"])
@login_required
def service_types_admin():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "save":
                ma = to_int(request.form.get("MaLoaiDV"))
                ten = request.form.get("TenLoaiDV", "").strip()
                dg = to_float(request.form.get("DonGia"))
                pt = to_float(request.form.get("PhanTramTraTruoc"), 50)
                if not ten or dg is None or dg < 0 or pt is None or not (0 <= pt <= 100):
                    raise BusinessError("Vui lòng nhập tên dịch vụ, đơn giá (≥ 0) và % trả trước (0–100%).")
                if ma:
                    db.execute(
                        "UPDATE LOAIDICHVU SET TenLoaiDV = ?, DonGia = ?, PhanTramTraTruoc = ? WHERE MaLoaiDV = ?",
                        (ten, dg, pt, ma),
                    )
                else:
                    db.execute(
                        "INSERT INTO LOAIDICHVU(TenLoaiDV, DonGia, PhanTramTraTruoc) VALUES (?, ?, ?)",
                        (ten, dg, pt),
                    )
                db.commit()
                flash("Đã lưu loại dịch vụ.", "success")
            elif action == "delete":
                ma = to_int(request.form.get("MaLoaiDV"))
                db.execute("DELETE FROM LOAIDICHVU WHERE MaLoaiDV = ?", (ma,))
                db.commit()
                flash("Đã xóa loại dịch vụ.", "success")
        except BusinessError as e:
            flash(str(e), "error")
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Tên dịch vụ bị trùng hoặc đã phát sinh phiếu dịch vụ.", "error")
        return redirect(url_for("admin.service_types_admin"))

    rows = db.execute(
        "SELECT l.*, (SELECT COUNT(*) FROM CT_PHIEUDICHVU c WHERE c.MaLoaiDV = l.MaLoaiDV) AS SoLan "
        "FROM LOAIDICHVU l ORDER BY l.MaLoaiDV"
    ).fetchall()
    return render_template("admin/service_types.html", rows=rows)


# ------------------------------------------------------------------ NHÀ CUNG CẤP & KHÁCH HÀNG
@bp.route("/nha-cung-cap", methods=["GET", "POST"])
@login_required
def suppliers_admin():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "save":
                ma = to_int(request.form.get("MaNCC"))
                ten = request.form.get("TenNCC", "").strip()
                sdt = request.form.get("SoDienThoai", "").strip()
                dc = request.form.get("DiaChi", "").strip()
                if not ten:
                    raise BusinessError("Vui lòng nhập tên nhà cung cấp.")
                if ma:
                    db.execute("UPDATE NHACUNGCAP SET TenNCC=?, SoDienThoai=?, DiaChi=? WHERE MaNCC=?",
                               (ten, sdt, dc, ma))
                else:
                    db.execute("INSERT INTO NHACUNGCAP(TenNCC, SoDienThoai, DiaChi) VALUES (?, ?, ?)",
                               (ten, sdt, dc))
                db.commit()
                flash("Đã lưu nhà cung cấp.", "success")
            elif action == "delete":
                ma = to_int(request.form.get("MaNCC"))
                db.execute("DELETE FROM NHACUNGCAP WHERE MaNCC = ?", (ma,))
                db.commit()
                flash("Đã xóa nhà cung cấp.", "success")
        except BusinessError as e:
            flash(str(e), "error")
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Nhà cung cấp đã có phiếu mua hàng nên không thể xóa.", "error")
        return redirect(url_for("admin.suppliers_admin"))

    rows = db.execute(
        "SELECT n.*, (SELECT COUNT(*) FROM PHIEUMUAHANG p WHERE p.MaNCC = n.MaNCC) AS SoPhieu, "
        "COALESCE((SELECT SUM(TongTien) FROM PHIEUMUAHANG p WHERE p.MaNCC = n.MaNCC), 0) AS TongMua "
        "FROM NHACUNGCAP n ORDER BY n.MaNCC"
    ).fetchall()
    return render_template("admin/suppliers.html", rows=rows)


@bp.route("/khach-hang", methods=["GET", "POST"])
@login_required
def customers_admin():
    db = get_db()
    if request.method == "POST":
        ma = to_int(request.form.get("MaKH"))
        ten = request.form.get("TenKH", "").strip()
        sdt = request.form.get("SoDienThoai", "").strip()
        dc = request.form.get("DiaChi", "").strip()
        email = request.form.get("Email", "").strip()
        if not ten:
            flash("Tên khách hàng không được để trống.", "error")
        elif ma:
            db.execute("UPDATE KHACHHANG SET TenKH=?, SoDienThoai=?, DiaChi=?, Email=? WHERE MaKH=?",
                       (ten, sdt, dc, email, ma))
            db.commit()
            flash("Đã cập nhật khách hàng.", "success")
        else:
            db.execute("INSERT INTO KHACHHANG(TenKH, SoDienThoai, DiaChi, Email) VALUES (?, ?, ?, ?)",
                       (ten, sdt, dc, email))
            db.commit()
            flash("Đã thêm khách hàng.", "success")
        return redirect(url_for("admin.customers_admin"))

    q = request.args.get("q", "").strip()
    where, args = ["1=1"], []
    if q:
        where.append("(k.TenKH LIKE ? OR k.SoDienThoai LIKE ?)")
        args += [f"%{q}%", f"%{q}%"]
    rows = db.execute(
        "SELECT k.*, "
        "(SELECT COUNT(*) FROM PHIEUBANHANG p WHERE p.MaKH = k.MaKH AND p.TrangThai <> ?) AS SoDonBan, "
        "COALESCE((SELECT SUM(TongTien) FROM PHIEUBANHANG p WHERE p.MaKH = k.MaKH AND p.TrangThai <> ?), 0) AS TongMua, "
        "(SELECT COUNT(*) FROM PHIEUDICHVU d WHERE d.MaKH = k.MaKH) AS SoPhieuDV "
        "FROM KHACHHANG k WHERE " + " AND ".join(where) + " ORDER BY k.MaKH DESC",
        [TT_HUY, TT_HUY] + args,
    ).fetchall()
    return render_template("admin/customers.html", rows=rows, q=q)


# ------------------------------------------------------------------ QUY ĐỊNH & TÀI KHOẢN
@bp.route("/quy-dinh", methods=["GET", "POST"])
@admin_required
def settings_admin():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "save_params":
                for key, _ in PARAM_LABELS:
                    val = request.form.get(key, "").strip()
                    set_param(db, key, val)
                db.commit()
                flash("Đã cập nhật thông tin & quy định cửa hàng.", "success")
            elif action == "add_user":
                u = request.form.get("TenDangNhap", "").strip()
                pw = request.form.get("MatKhau", "")
                ho_ten = request.form.get("HoTen", "").strip()
                vai_tro = request.form.get("VaiTro", "nhanvien")
                if not u or not pw or not ho_ten or vai_tro not in ("admin", "nhanvien"):
                    raise BusinessError("Vui lòng nhập đầy đủ thông tin tài khoản.")
                db.execute(
                    "INSERT INTO NGUOIDUNG(TenDangNhap, MatKhau, HoTen, VaiTro) VALUES (?, ?, ?, ?)",
                    (u, generate_password_hash(pw), ho_ten, vai_tro),
                )
                db.commit()
                flash(f"Đã tạo tài khoản “{u}”.", "success")
            elif action == "delete_user":
                ma = to_int(request.form.get("MaND"))
                if ma == g.user["MaND"]:
                    raise BusinessError("Không thể tự xóa tài khoản đang đăng nhập.")
                db.execute("DELETE FROM NGUOIDUNG WHERE MaND = ?", (ma,))
                db.commit()
                flash("Đã xóa tài khoản.", "success")
        except BusinessError as e:
            flash(str(e), "error")
        except sqlite3.IntegrityError:
            db.rollback()
            flash("Tên đăng nhập đã tồn tại.", "error")
        return redirect(url_for("admin.settings_admin"))

    params = get_params(db)
    users = db.execute("SELECT MaND, TenDangNhap, HoTen, VaiTro FROM NGUOIDUNG ORDER BY MaND").fetchall()
    return render_template("admin/settings.html", params=params, param_labels=PARAM_LABELS,
                           users=users, is_admin=is_admin())
