"""Tầng Điều khiển Quản lý Cửa hàng (Presentation Controller – KHÔNG chứa SQL trực tiếp)."""
import os
import uuid
from datetime import date

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from ..auth import can_revert_service, is_manager, login_required, manager_required
from ..db import get_db
from ..services import catalog as cat_svc
from ..services import inventory as inv_svc
from ..services import reports as rep_svc
from ..services import settings as set_svc
from ..services import vouchers as vou_svc
from ..utils import BusinessError, format_pct_num, rows_from_form, to_int, validate_ngay_lap

bp = Blueprint("admin", __name__, url_prefix="/quan-ly")

STOCK_IMAGES = [
    ("img/products/gold-bar.jpg", "Vàng miếng 999.9 ép vỉ"),
    ("img/products/gold-bullion-set.jpg", "Bộ vàng miếng & đồng xu tích lũy"),
    ("img/products/ring-plain-gold.jpg", "Nhẫn tròn trơn vàng 999.9"),
    ("img/products/ring-gold.jpg", "Nhẫn trang sức vàng 18K"),
    ("img/products/ring-solitaire.jpg", "Nhẫn cưới kim cương Halo"),
    ("img/products/ring-diamond.jpg", "Nhẫn nữ Solitaire kim cương"),
    ("img/products/ring-ruby.jpg", "Nhẫn nam vàng đính đá Ruby"),
    ("img/products/necklace-gold.jpg", "Dây chuyền vàng 18K mặt đá"),
    ("img/products/gold-display.jpg", "Dây chuyền & Vòng vàng 24K"),
    ("img/products/earring-pearl.jpg", "Trang sức ngọc trai Akoya"),
    ("img/products/earring-gold.jpg", "Bông tai kim cương vàng 18K"),
    ("img/products/bracelet-gold.jpg", "Lắc tay vàng 18K chế tác tinh xảo"),
    ("img/products/bracelet-box.jpg", "Vòng kiềng tay cưới hộp nhung"),
    ("img/products/hero-showcase.jpg", "Bộ kim cương thiên nhiên GIA"),
    ("img/products/gem-sapphire.jpg", "Đá Sapphire xanh hoàng gia"),
    ("img/products/jewelry-luxury.jpg", "Trang sức bạc Ý / Bạch kim tối giản"),
    ("img/products/silver-set.jpg", "Dây chuyền bạc 925 Halo"),
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


# ------------------------------------------------------------------ 1. TỔNG QUAN
@bp.route("/")
@login_required
def dashboard():
    min_ton = current_app.config["STORE_INFO"].get("NguongCanhBaoTon", 2)
    data = rep_svc.lay_du_lieu_tong_quan(get_db(), min_ton=min_ton)
    return render_template("admin/dashboard.html", **data)


# ------------------------------------------------------------------ 2. PHIẾU MUA HÀNG
@bp.route("/phieu-mua")
@login_required
def purchases():
    db = get_db()
    q = request.args.get("q", "").strip()
    ma_ncc = request.args.get("ma_ncc", "").strip()
    tu_ngay = request.args.get("tu_ngay", "").strip()
    den_ngay = request.args.get("den_ngay", "").strip()
    rows, tong = vou_svc.lay_danh_sach_phieu_mua(db, q=q, ma_ncc=ma_ncc, tu_ngay=tu_ngay, den_ngay=den_ngay)
    suppliers = cat_svc.lay_danh_sach_ncc(db)
    return render_template(
        "admin/purchases.html",
        rows=rows,
        tong=tong,
        suppliers=suppliers,
        q=q,
        ma_ncc=ma_ncc,
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
    )


@bp.route("/phieu-mua/lap", methods=["GET", "POST"])
@login_required
def purchase_create():
    db = get_db()
    suppliers = cat_svc.lay_danh_sach_ncc(db, tinh_trang="Đang hợp tác")
    products = cat_svc.lay_san_pham_dang_kinh_doanh(db)

    if request.method == "POST":
        ma_ncc = (request.form.get("MaNCC") or "").strip()
        ngay_lap = request.form.get("NgayLap", "")
        ghi_chu = request.form.get("GhiChu", "").strip()
        items = rows_from_form(request.form, ["MaSP", "SoLuong", "DonGia"])
        try:
            ngay_lap = validate_ngay_lap(ngay_lap)
            so_phieu = vou_svc.tao_phieu_mua(db, ma_ncc, ngay_lap, items, ghi_chu=ghi_chu, ma_nv=g.user["MaNV"])
        except BusinessError as e:
            flash(str(e), "error")
        else:
            flash(f"Đã lập phiếu mua hàng {so_phieu} và cập nhật tăng tồn kho.", "success")
            return redirect(url_for("admin.purchase_detail", so_phieu=so_phieu))

    return render_template("admin/purchase_form.html", suppliers=suppliers, products=products)


@bp.route("/phieu-mua/<so_phieu>")
@login_required
def purchase_detail(so_phieu):
    p, lines = vou_svc.lay_phieu_mua(get_db(), so_phieu)
    if p is None:
        abort(404)
    return render_template("admin/purchase_detail.html", p=p, lines=lines)


# ------------------------------------------------------------------ 3. PHIẾU BÁN HÀNG
@bp.route("/phieu-ban")
@login_required
def sales():
    q = request.args.get("q", "").strip()
    nguon = request.args.get("nguon", "").strip()
    trang_thai = request.args.get("trang_thai", "").strip()
    pttt = request.args.get("pttt", "").strip()
    tu_ngay = request.args.get("tu_ngay", "").strip()
    den_ngay = request.args.get("den_ngay", "").strip()

    rows, tong = vou_svc.lay_danh_sach_phieu_ban(
        get_db(), q=q, nguon=nguon, trang_thai=trang_thai, pttt=pttt, tu_ngay=tu_ngay, den_ngay=den_ngay
    )
    return render_template(
        "admin/sales.html",
        rows=rows,
        tong=tong,
        q=q,
        nguon=nguon,
        trang_thai=trang_thai,
        pttt=pttt,
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
    )


@bp.route("/phieu-ban/lap", methods=["GET", "POST"])
@login_required
def sale_create():
    db = get_db()
    products = cat_svc.lay_san_pham_dang_kinh_doanh(db, only_in_stock=True)
    customers = rep_svc.lay_danh_sach_khach_hang(db)

    if request.method == "POST":
        khach = {
            "ten": request.form.get("TenKH", ""),
            "sdt": request.form.get("SoDienThoai", ""),
            "dia_chi": request.form.get("DiaChi", ""),
        }
        ngay_lap = request.form.get("NgayLap", "")
        ghi_chu = request.form.get("GhiChu", "").strip()
        pttt = request.form.get("PhuongThucThanhToan", "Tiền mặt")
        so_tien_nhan = request.form.get("SoTienNhan", "")
        items = rows_from_form(request.form, ["MaSP", "SoLuong"])
        try:
            ngay_lap = validate_ngay_lap(ngay_lap)
            so_phieu = vou_svc.tao_phieu_ban(
                db,
                khach,
                items,
                ngay_lap,
                nguon=vou_svc.NGUON_QUAY,
                trang_thai=vou_svc.TT_HOAN_TAT,
                ghi_chu=ghi_chu,
                ma_nv=g.user["MaNV"],
                pttt=pttt,
                so_tien_nhan=so_tien_nhan,
            )
        except BusinessError as e:
            flash(str(e), "error")
        else:
            flash(f"Đã lập phiếu bán hàng {so_phieu} và cập nhật tồn kho.", "success")
            return redirect(url_for("admin.sale_detail", so_phieu=so_phieu))

    return render_template("admin/sale_form.html", products=products, customers=customers)


@bp.route("/phieu-ban/<so_phieu>")
@login_required
def sale_detail(so_phieu):
    p, lines = vou_svc.lay_phieu_ban(get_db(), so_phieu)
    if p is None:
        abort(404)
    return render_template("admin/sale_detail.html", p=p, lines=lines)


@bp.route("/phieu-ban/<so_phieu>/hoan-tat", methods=["POST"])
@login_required
def sale_complete(so_phieu):
    try:
        vou_svc.hoan_tat_phieu_ban(get_db(), so_phieu, g.user["MaNV"])
        flash(f"Đã xác nhận hoàn tất đơn hàng {so_phieu}.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("admin.sale_detail", so_phieu=so_phieu))


@bp.route("/phieu-ban/<so_phieu>/huy", methods=["POST"])
@login_required
def sale_cancel(so_phieu):
    try:
        vou_svc.huy_phieu_ban(get_db(), so_phieu)
        flash(f"Đã hủy phiếu bán hàng {so_phieu} và hoàn lại số lượng tồn kho.", "info")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("admin.sale_detail", so_phieu=so_phieu))


# ------------------------------------------------------------------ 4. PHIẾU DỊCH VỤ & TIẾN ĐỘ
@bp.route("/phieu-dich-vu")
@login_required
def services_vouchers():
    q = request.args.get("q", "").strip()
    tinh_trang = request.args.get("tinh_trang", "").strip()
    tu_ngay = request.args.get("tu_ngay", "").strip()
    den_ngay = request.args.get("den_ngay", "").strip()
    rows, tong = vou_svc.lay_danh_sach_phieu_dich_vu(
        get_db(), q=q, tinh_trang=tinh_trang, tu_ngay=tu_ngay, den_ngay=den_ngay
    )
    return render_template(
        "admin/services_vouchers.html",
        rows=rows,
        tong=tong,
        q=q,
        tinh_trang=tinh_trang,
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
    )


@bp.route("/phieu-dich-vu/tien-do")
@login_required
def service_status_board():
    tt = request.args.get("tinh_trang", vou_svc.DV_CHUA_GIAO).strip()
    q = request.args.get("q", "").strip()
    rows = vou_svc.lay_bang_tien_do_dich_vu(get_db(), q=q, tinh_trang=tt)
    return render_template(
        "admin/service_status.html",
        rows=rows,
        tt=tt,
        q=q,
        can_revert=can_revert_service(),
    )


@bp.route("/phieu-dich-vu/lap", methods=["GET", "POST"])
@login_required
def service_create():
    db = get_db()
    service_types = cat_svc.lay_danh_sach_dich_vu(db, tinh_trang="Đang hoạt động")
    customers = rep_svc.lay_danh_sach_khach_hang(db)
    ti_le_pct = format_pct_num(set_svc.lay_tham_so(db)["TiLeTraTruoc"])

    if request.method == "POST":
        khach = {
            "ten": request.form.get("TenKH", ""),
            "sdt": request.form.get("SoDienThoai", ""),
        }
        ngay_lap = request.form.get("NgayLap", "")
        hinh_thuc = request.form.get("HinhThucThanhToan", "Tiền mặt")
        items = rows_from_form(
            request.form, ["MaDichVu", "ChiPhiRieng", "SoLuong", "TraTruoc", "NgayGiaoDuKien", "GhiChu"]
        )
        try:
            ngay_lap = validate_ngay_lap(ngay_lap)
            so_phieu = vou_svc.tao_phieu_dich_vu(
                db, khach, items, ngay_lap, ma_nv=g.user["MaNV"], hinh_thuc=hinh_thuc
            )
        except BusinessError as e:
            flash(str(e), "error")
        else:
            flash(f"Đã lập phiếu dịch vụ {so_phieu} và ghi nhận phiếu thu tiền đặt trước.", "success")
            return redirect(url_for("admin.service_detail", so_phieu=so_phieu))

    return render_template(
        "admin/service_form.html",
        service_types=service_types,
        customers=customers,
        ti_le_tra_truoc=ti_le_pct,
    )


@bp.route("/phieu-dich-vu/<so_phieu>")
@login_required
def service_detail(so_phieu):
    p, lines, receipts, logs = vou_svc.lay_phieu_dich_vu(get_db(), so_phieu)
    if p is None:
        abort(404)
    return render_template(
        "admin/service_detail.html",
        p=p,
        lines=lines,
        receipts=receipts,
        logs=logs,
        can_revert=can_revert_service(),
    )


@bp.route("/phieu-dich-vu/cap-nhat/<int:ma_chi_tiet>", methods=["POST"])
@login_required
def service_deliver_line(ma_chi_tiet):
    tinh_trang_moi = request.form.get("TinhTrangMoi", vou_svc.DV_DA_GIAO)
    ly_do = request.form.get("LyDo", "")
    ghi_chu = request.form.get("GhiChu")
    try:
        so_phieu = vou_svc.cap_nhat_tinh_trang_dich_vu(
            get_db(),
            ma_chi_tiet,
            tinh_trang_moi,
            ma_nv=g.user["MaNV"],
            co_quyen_chuyen_nguoc=can_revert_service(),
            ly_do=ly_do,
            ghi_chu=ghi_chu,
        )
        flash(f"Đã cập nhật tình trạng dịch vụ sang “{tinh_trang_moi}”.", "success")
        return redirect(request.referrer or url_for("admin.service_detail", so_phieu=so_phieu))
    except BusinessError as e:
        flash(str(e), "error")
        return redirect(request.referrer or url_for("admin.services_vouchers"))


@bp.route("/phieu-dich-vu/<so_phieu>/thu-tien", methods=["POST"])
@login_required
def service_collect_payment(so_phieu):
    so_tien = request.form.get("SoTienThu")
    hinh_thuc = request.form.get("HinhThucThanhToan", "Tiền mặt")
    ghi_chu = request.form.get("GhiChu", "").strip()
    try:
        ma_thu = vou_svc.thu_tien_dich_vu(
            get_db(), so_phieu, so_tien, hinh_thuc=hinh_thuc, ma_nv=g.user["MaNV"], ghi_chu=ghi_chu
        )
        flash(f"Đã lập phiếu thu {ma_thu} ghi nhận thanh toán dịch vụ.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.service_detail", so_phieu=so_phieu))


# ------------------------------------------------------------------ 5. TRA CỨU TỒN KHO & KIỂM KÊ KHO
@bp.route("/ton-kho")
@login_required
def inventory_lookup():
    db = get_db()
    q = request.args.get("q", "").strip()
    loai = request.args.get("loai", "").strip()
    tinh_trang = request.args.get("tinh_trang", "").strip()
    muc_ton = request.args.get("muc_ton", "").strip()
    min_ton = current_app.config["STORE_INFO"].get("NguongCanhBaoTon", 2)

    rows = cat_svc.tra_cuu_san_pham_quan_ly(
        db, q=q, ma_loai=loai, tinh_trang=tinh_trang, stock_filter=muc_ton, min_ton=min_ton
    )
    categories = cat_svc.lay_danh_sach_loai_sp(db)
    tong_gia_tri_von = sum(r["SoLuongTon"] * r["DonGiaMua"] for r in rows)
    return render_template(
        "admin/inventory_lookup.html",
        rows=rows,
        categories=categories,
        q=q,
        loai=loai,
        tinh_trang=tinh_trang,
        muc_ton=muc_ton,
        min_ton=min_ton,
        tong_gia_tri_von=tong_gia_tri_von,
    )


@bp.route("/kiem-ke")
@login_required
def stocktakes():
    rows = inv_svc.lay_danh_sach_kiem_ke(get_db())
    return render_template("admin/stocktakes.html", rows=rows)


@bp.route("/kiem-ke/lap", methods=["GET", "POST"])
@login_required
def stocktake_create():
    db = get_db()
    products = cat_svc.tra_cuu_san_pham_quan_ly(db)
    if request.method == "POST":
        ngay = request.form.get("NgayKiemKe", "")
        ghi_chu = request.form.get("GhiChu", "").strip()
        items = rows_from_form(request.form, ["MaSP", "TonThucTe", "LyDoChenhLech"])
        try:
            ngay = validate_ngay_lap(ngay, "Ngày kiểm kê")
            so_kk = inv_svc.tao_phieu_kiem_ke(db, ngay, items, ma_nv=g.user["MaNV"], ghi_chu=ghi_chu)
        except BusinessError as e:
            flash(str(e), "error")
        else:
            flash(f"Đã lưu phiếu kiểm kê kho {so_kk}.", "success")
            return redirect(url_for("admin.stocktake_detail", so_phieu_kk=so_kk))
    return render_template("admin/stocktake_form.html", products=products)


@bp.route("/kiem-ke/<so_phieu_kk>")
@login_required
def stocktake_detail(so_phieu_kk):
    p, lines = inv_svc.lay_phieu_kiem_ke(get_db(), so_phieu_kk)
    if p is None:
        abort(404)
    return render_template("admin/stocktake_detail.html", p=p, lines=lines)


@bp.route("/kiem-ke/<so_phieu_kk>/xac-nhan", methods=["POST"])
@manager_required
def stocktake_confirm(so_phieu_kk):
    try:
        inv_svc.xac_nhan_kiem_ke(get_db(), so_phieu_kk, g.user["MaNV"], is_manager=True)
        flash(f"Đã xác nhận biên bản kiểm kê {so_phieu_kk}.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.stocktake_detail", so_phieu_kk=so_phieu_kk))


# ------------------------------------------------------------------ 6. BÁO CÁO & CHỐT / KHÓA KỲ
@bp.route("/bao-cao-ton-kho")
@login_required
def report_inventory():
    today = date.today()
    thang = min(max(to_int(request.args.get("thang"), today.month) or today.month, 1), 12)
    nam = to_int(request.args.get("nam"), today.year) or today.year
    rows, ky = rep_svc.bao_cao_ton_kho(get_db(), thang, nam)
    return render_template("admin/report_inventory.html", rows=rows, thang=thang, nam=nam, ky=ky)


@bp.route("/bao-cao-doanh-thu")
@login_required
def report_revenue():
    today = date.today()
    thang = min(max(to_int(request.args.get("thang"), today.month) or today.month, 1), 12)
    nam = to_int(request.args.get("nam"), today.year) or today.year
    data = rep_svc.bao_cao_doanh_thu(get_db(), thang, nam)
    return render_template("admin/report_revenue.html", thang=thang, nam=nam, **data)


@bp.route("/chot-ky", methods=["POST"])
@manager_required
def close_period():
    thang = to_int(request.form.get("thang"))
    nam = to_int(request.form.get("nam"))
    try:
        if not thang or not nam or not (1 <= thang <= 12):
            raise BusinessError("Tháng hoặc năm chốt kỳ không hợp lệ.")
        rep_svc.chot_ky_bao_cao(get_db(), thang, nam, g.user["MaNV"])
        flash(f"Đã chốt số liệu báo cáo tồn kho & doanh thu tháng {thang:02d}/{nam}.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("admin.report_inventory", thang=thang, nam=nam))


@bp.route("/khoa-ky", methods=["POST"])
@manager_required
def lock_period():
    thang = to_int(request.form.get("thang"))
    nam = to_int(request.form.get("nam"))
    try:
        if not thang or not nam or not (1 <= thang <= 12):
            raise BusinessError("Tháng hoặc năm khóa kỳ không hợp lệ.")
        rep_svc.khoa_ky_bao_cao(get_db(), thang, nam)
        flash(f"Đã khóa sổ kỳ tháng {thang:02d}/{nam}. Không thể phát sinh thêm chứng từ vào kỳ này.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("admin.report_inventory", thang=thang, nam=nam))


# ------------------------------------------------------------------ 7. DANH MỤC DÙNG CHUNG
@bp.route("/san-pham")
@login_required
def products_admin():
    db = get_db()
    q = request.args.get("q", "").strip()
    loai = request.args.get("loai", "").strip()
    tinh_trang = request.args.get("tinh_trang", "").strip()
    rows = cat_svc.tra_cuu_san_pham_quan_ly(db, q=q, ma_loai=loai, tinh_trang=tinh_trang)
    categories = cat_svc.lay_danh_sach_loai_sp(db)
    return render_template(
        "admin/products.html",
        rows=rows,
        categories=categories,
        q=q,
        loai=loai,
        tinh_trang=tinh_trang,
    )


@bp.route("/san-pham/them", methods=["GET", "POST"])
@bp.route("/san-pham/<ma_sp>/sua", methods=["GET", "POST"])
@login_required
def product_edit(ma_sp=None):
    db = get_db()
    sp = cat_svc.lay_san_pham(db, ma_sp) if ma_sp else None
    if ma_sp and sp is None:
        abort(404)
    categories = cat_svc.lay_danh_sach_loai_sp(db)

    if request.method == "POST":
        try:
            uploaded = _save_uploaded_image(request.files.get("HinhAnhFile"))
            saved_id, is_update = cat_svc.luu_san_pham(db, ma_sp, request.form, uploaded_image=uploaded)
            flash(
                f"Đã {'cập nhật' if is_update else 'thêm mới'} sản phẩm {saved_id}.",
                "success",
            )
            return redirect(url_for("admin.products_admin"))
        except BusinessError as e:
            flash(str(e), "error")

    return render_template("admin/product_form.html", sp=sp, categories=categories, stock_images=STOCK_IMAGES)


@bp.route("/san-pham/<ma_sp>/trang-thai", methods=["POST"])
@login_required
def product_toggle_status(ma_sp):
    try:
        ten, moi = cat_svc.doi_trang_thai_san_pham(get_db(), ma_sp)
        flash(f"Đã chuyển sản phẩm “{ten}” sang trạng thái “{moi}”.", "info")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.products_admin"))


@bp.route("/san-pham/<ma_sp>/xoa", methods=["POST"])
@login_required
def product_delete(ma_sp):
    try:
        ten = cat_svc.xoa_san_pham(get_db(), ma_sp)
        flash(f"Đã xóa vật lý sản phẩm “{ten}”.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.products_admin"))


@bp.route("/loai-san-pham", methods=["GET", "POST"])
@login_required
def categories_admin():
    db = get_db()
    if request.method == "POST":
        if not is_manager():
            flash("Chỉ Quản lý mới có quyền thay đổi quy định loại sản phẩm, đơn vị tính và % lợi nhuận.", "error")
            return redirect(url_for("admin.categories_admin"))
        action = request.form.get("action")
        try:
            if action == "save_unit":
                cat_svc.luu_don_vi_tinh(db, request.form.get("MaDVT"), request.form.get("TenDVT"), g.user["MaNV"])
                flash("Đã lưu đơn vị tính và ghi nhận nhật ký quy định.", "success")
            elif action == "delete_unit":
                cat_svc.xoa_don_vi_tinh(db, request.form.get("MaDVT"))
                flash("Đã xóa đơn vị tính.", "success")
            elif action == "save_cat":
                cat_svc.luu_loai_san_pham(
                    db,
                    request.form.get("MaLoaiSP"),
                    request.form.get("TenLoaiSP"),
                    request.form.get("MaDVT"),
                    request.form.get("PhanTramLoiNhuan"),
                    g.user["MaNV"],
                )
                flash("Đã lưu loại sản phẩm và ghi nhận nhật ký quy định.", "success")
            elif action == "delete_cat":
                cat_svc.xoa_loai_san_pham(db, request.form.get("MaLoaiSP"))
                flash("Đã xóa loại sản phẩm.", "success")
        except BusinessError as e:
            flash(str(e), "error")
        return redirect(url_for("admin.categories_admin"))

    return render_template(
        "admin/categories.html",
        categories=cat_svc.lay_danh_sach_loai_sp(db),
        units=cat_svc.lay_danh_sach_dvt(db),
        can_edit_rules=is_manager(),
    )


@bp.route("/loai-dich-vu", methods=["GET", "POST"])
@login_required
def service_types_admin():
    db = get_db()
    if request.method == "POST":
        if not is_manager():
            flash("Chỉ Quản lý mới có quyền thêm, sửa hoặc thay đổi đơn giá dịch vụ.", "error")
            return redirect(url_for("admin.service_types_admin"))
        action = request.form.get("action")
        try:
            if action == "save":
                cat_svc.luu_dich_vu(
                    db,
                    request.form.get("MaDichVu"),
                    request.form.get("TenDichVu"),
                    request.form.get("DonGiaCoBan"),
                    request.form.get("TinhTrang"),
                    g.user["MaNV"],
                )
                flash("Đã lưu thông tin dịch vụ và ghi nhận nhật ký quy định.", "success")
            elif action == "delete":
                ten = cat_svc.xoa_dich_vu(db, request.form.get("MaDichVu"))
                flash(f"Đã xóa dịch vụ “{ten}”.", "success")
        except BusinessError as e:
            flash(str(e), "error")
        return redirect(url_for("admin.service_types_admin"))

    q = request.args.get("q", "").strip()
    tt = request.args.get("tinh_trang", "").strip()
    rows = cat_svc.lay_danh_sach_dich_vu(db, q=q, tinh_trang=tt)
    ti_le_pct = format_pct_num(set_svc.lay_tham_so(db)["TiLeTraTruoc"])
    return render_template(
        "admin/service_types.html",
        rows=rows,
        q=q,
        tinh_trang=tt,
        ti_le_tra_truoc=ti_le_pct,
        can_edit_rules=is_manager(),
    )


@bp.route("/nha-cung-cap", methods=["GET", "POST"])
@login_required
def suppliers_admin():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "save":
                ma = cat_svc.luu_nha_cung_cap(
                    db,
                    request.form.get("MaNCC"),
                    request.form.get("TenNCC"),
                    request.form.get("DiaChi"),
                    request.form.get("SoDienThoai"),
                    request.form.get("TinhTrang"),
                )
                flash(f"Đã lưu thông tin nhà cung cấp {ma}.", "success")
            elif action == "delete":
                ten = cat_svc.xoa_nha_cung_cap(db, request.form.get("MaNCC"))
                flash(f"Đã xóa nhà cung cấp “{ten}”.", "success")
        except BusinessError as e:
            flash(str(e), "error")
        return redirect(url_for("admin.suppliers_admin"))

    q = request.args.get("q", "").strip()
    tt = request.args.get("tinh_trang", "").strip()
    rows = cat_svc.lay_danh_sach_ncc(db, q=q, tinh_trang=tt)
    return render_template("admin/suppliers.html", rows=rows, q=q, tinh_trang=tt)


@bp.route("/khach-hang")
@login_required
def customers_admin():
    q = request.args.get("q", "").strip()
    rows = rep_svc.lay_danh_sach_khach_hang(get_db(), q=q)
    return render_template("admin/customers.html", rows=rows, q=q)


# ------------------------------------------------------------------ 8. QUY ĐỊNH, TÀI KHOẢN & SAO LƯU
@bp.route("/quy-dinh", methods=["GET", "POST"])
@manager_required
def settings_admin():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "save_thamso":
                changed = set_svc.cap_nhat_ti_le_tra_truoc(
                    db,
                    request.form.get("TiLeTraTruoc"),
                    g.user["MaNV"],
                    request.form.get("GhiChu"),
                )
                flash(
                    "Đã cập nhật tỷ lệ trả trước tối thiểu và lưu nhật ký." if changed
                    else "Tỷ lệ trả trước không thay đổi.",
                    "success" if changed else "info",
                )
            elif action == "add_user":
                ma = set_svc.tao_tai_khoan(
                    db,
                    request.form.get("TenDangNhap"),
                    request.form.get("MatKhau"),
                    request.form.get("TenNV"),
                    request.form.get("VaiTro"),
                    co_quyen_chuyen_nguoc=(request.form.get("CoQuyenChuyenNguoc") == "1"),
                )
                flash(f"Đã tạo tài khoản nhân viên {ma}.", "success")
            elif action == "toggle_user_revert":
                ten, bat = set_svc.dao_quyen_chuyen_nguoc(db, request.form.get("MaNV"))
                flash(f"Đã {'cấp' if bat else 'thu hồi'} quyền chuyển ngược dịch vụ cho {ten}.", "success")
            elif action == "toggle_user_status":
                ten, moi = set_svc.doi_trang_thai_tai_khoan(db, request.form.get("MaNV"), g.user["MaNV"])
                flash(f"Đã chuyển tài khoản “{ten}” sang trạng thái “{moi}”.", "info")
            elif action == "delete_user":
                ten = set_svc.xoa_tai_khoan(db, request.form.get("MaNV"), g.user["MaNV"])
                flash(f"Đã xóa tài khoản “{ten}”.", "success")
        except BusinessError as e:
            flash(str(e), "error")
        return redirect(url_for("admin.settings_admin"))

    tham_so = set_svc.lay_tham_so(db)
    return render_template(
        "admin/settings.html",
        ti_le_pct=format_pct_num(tham_so["TiLeTraTruoc"]),
        users=set_svc.lay_danh_sach_nguoi_dung(db),
        logs=set_svc.lay_nhat_ky_quy_dinh(db, limit=30),
        backups=set_svc.lay_danh_sach_sao_luu(),
    )


@bp.route("/sao-luu", methods=["POST"])
@manager_required
def backup_create():
    filename, _ = set_svc.tao_ban_sao_luu()
    flash(f"Đã sao lưu cơ sở dữ liệu thành công: {filename}", "success")
    return redirect(url_for("admin.settings_admin"))


@bp.route("/sao-luu/tai/<filename>")
@manager_required
def backup_download(filename):
    safe = os.path.basename(filename)
    if not safe.endswith(".db"):
        abort(404)
    return send_from_directory(current_app.config["BACKUP_FOLDER"], safe, as_attachment=True)


@bp.route("/phuc-hoi", methods=["POST"])
@manager_required
def backup_restore():
    backup_folder = current_app.config["BACKUP_FOLDER"]
    try:
        server_file = (request.form.get("BackupFilename") or "").strip()
        if server_file:
            set_svc.phuc_hoi_tu_file_tren_server(backup_folder, server_file)
            flash(f"Đã phục hồi cơ sở dữ liệu từ bản sao lưu {server_file}.", "success")
        else:
            set_svc.phuc_hoi_tu_file_upload(request.files.get("BackupFile"), backup_folder)
            flash("Đã phục hồi cơ sở dữ liệu từ tệp tải lên thành công.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.settings_admin"))
