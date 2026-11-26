"""Tầng Điều khiển Giao diện Khách hàng (Storefront – chỉ gọi tầng Services, không chứa SQL)."""
import re
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from ..db import get_db
from ..services import catalog as cat_svc
from ..services import settings as set_svc
from ..services import vouchers as vou_svc
from ..utils import BusinessError, format_pct_num, to_int

bp = Blueprint("shop", __name__)

PHONE_RE = re.compile(r"^0\d{9,10}$")


@bp.route("/")
def index():
    db = get_db()
    featured = cat_svc.lay_san_pham_noi_bat(db, limit=8)
    categories = cat_svc.lay_danh_sach_loai_sp(db)
    services = cat_svc.lay_danh_sach_dich_vu(db, tinh_trang="Đang hoạt động")[:6]
    ti_le_pct = format_pct_num(set_svc.lay_tham_so(db)["TiLeTraTruoc"])
    return render_template(
        "shop/index.html",
        featured=featured,
        categories=categories,
        services=services,
        ti_le_tra_truoc=ti_le_pct,
    )


@bp.route("/san-pham")
def products():
    db = get_db()
    q = request.args.get("q", "").strip()
    loai = request.args.get("loai", "").strip()
    sort = request.args.get("sort", "moi")
    con_hang = request.args.get("con_hang") == "1"

    rows = cat_svc.tra_cuu_san_pham_cua_hang(db, q=q, ma_loai=loai, sort=sort, con_hang=con_hang)
    current_cat = cat_svc.lay_loai_sp(db, loai) if loai else None
    return render_template(
        "shop/products.html",
        products=rows,
        q=q,
        loai=loai,
        sort=sort,
        con_hang=con_hang,
        current_cat=current_cat,
        sorts=cat_svc.SORT_LABELS,
    )


@bp.route("/san-pham/<ma_sp>")
def product_detail(ma_sp):
    db = get_db()
    p = cat_svc.lay_san_pham(db, ma_sp)
    if p is None or not p["HienThi"] or p["TinhTrang"] != "Đang kinh doanh":
        abort(404)
    related = cat_svc.lay_san_pham_lien_quan(db, p["MaLoaiSP"], ma_sp, limit=4)
    return render_template("shop/product_detail.html", p=p, related=related)


@bp.route("/dich-vu")
def dich_vu():
    db = get_db()
    services = cat_svc.lay_danh_sach_dich_vu(db, tinh_trang="Đang hoạt động")
    ti_le_pct = format_pct_num(set_svc.lay_tham_so(db)["TiLeTraTruoc"])
    return render_template("shop/services.html", services=services, ti_le_tra_truoc=ti_le_pct)


def _cart_items(db):
    cart = session.get("cart", {})
    items, total = [], 0.0
    for ma_sp, sl in cart.items():
        p = cat_svc.lay_san_pham(db, ma_sp)
        if p is None or not p["HienThi"] or p["TinhTrang"] != "Đang kinh doanh":
            continue
        item = dict(p)
        item["SoLuong"] = sl
        item["ThanhTien"] = round(sl * p["DonGiaBan"], 2)
        items.append(item)
        total += item["ThanhTien"]
    return items, round(total, 2)


@bp.route("/gio-hang")
def cart():
    items, total = _cart_items(get_db())
    return render_template("shop/cart.html", items=items, total=total)


@bp.route("/gio-hang/them", methods=["POST"])
def cart_add():
    ma_sp = (request.form.get("MaSP") or "").strip()
    sl = max(to_int(request.form.get("SoLuong"), 1) or 1, 1)
    p = cat_svc.lay_san_pham(get_db(), ma_sp) if ma_sp else None
    back = request.referrer or url_for("shop.products")
    if p is None or not p["HienThi"] or p["TinhTrang"] != "Đang kinh doanh":
        flash("Sản phẩm hiện không khả dụng.", "error")
        return redirect(back)

    if p["SoLuongTon"] <= 0:
        flash(f"“{p['TenSP']}” hiện tạm hết hàng.", "error")
        return redirect(back)

    max_qty = int(p["SoLuongTon"]) if p["SoLuongTon"] >= 1 else 1
    cart = session.get("cart", {})
    new_qty = cart.get(ma_sp, 0) + sl
    if new_qty > max_qty:
        new_qty = max_qty
        flash(f"“{p['TenSP']}” chỉ còn {p['SoLuongTon']:g} {p['TenDVT']}, số lượng giỏ hàng đã được điều chỉnh.", "info")
    else:
        flash(f"Đã thêm “{p['TenSP']}” vào giỏ hàng.", "success")
    cart[ma_sp] = new_qty
    session["cart"] = cart

    if request.form.get("buy_now"):
        return redirect(url_for("shop.checkout"))
    return redirect(back)


@bp.route("/gio-hang/cap-nhat", methods=["POST"])
def cart_update():
    db = get_db()
    cart = session.get("cart", {})
    for ma_sp in list(cart.keys()):
        qty = to_int(request.form.get(f"qty_{ma_sp}"), cart[ma_sp])
        p = cat_svc.lay_san_pham(db, ma_sp)
        if p is None or qty is None or qty <= 0 or p["TinhTrang"] != "Đang kinh doanh" or p["SoLuongTon"] <= 0:
            cart.pop(ma_sp, None)
            continue
        max_qty = int(p["SoLuongTon"]) if p["SoLuongTon"] >= 1 else 1
        cart[ma_sp] = min(qty, max_qty)
    session["cart"] = cart
    flash("Đã cập nhật giỏ hàng.", "success")
    return redirect(url_for("shop.cart"))


@bp.route("/gio-hang/xoa/<ma_sp>", methods=["POST"])
def cart_remove(ma_sp):
    cart = session.get("cart", {})
    cart.pop(ma_sp, None)
    session["cart"] = cart
    return redirect(url_for("shop.cart"))


@bp.route("/thanh-toan", methods=["GET", "POST"])
def checkout():
    db = get_db()
    items, total = _cart_items(db)
    if not items:
        flash("Giỏ hàng của bạn đang trống.", "info")
        return redirect(url_for("shop.products"))

    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        ten = form.get("TenKH", "").strip()
        sdt = form.get("SoDienThoai", "").strip().replace(" ", "")
        dia_chi = form.get("DiaChi", "").strip()
        ghi_chu = form.get("GhiChu", "").strip()
        pttt = form.get("PhuongThucThanhToan", "Tiền mặt")
        if pttt not in ("Tiền mặt", "Chuyển khoản"):
            pttt = "Tiền mặt"

        errors = []
        if not ten:
            errors.append("Vui lòng nhập họ và tên khách hàng.")
        if not PHONE_RE.match(sdt):
            errors.append("Số điện thoại không hợp lệ (10–11 chữ số, bắt đầu bằng số 0).")
        if not dia_chi:
            errors.append("Vui lòng nhập địa chỉ nhận hàng.")
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            try:
                so = vou_svc.tao_phieu_ban(
                    db,
                    {"ten": ten, "sdt": sdt, "dia_chi": dia_chi},
                    [{"MaSP": i["MaSP"], "SoLuong": i["SoLuong"]} for i in items],
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    nguon=vou_svc.NGUON_ONLINE,
                    trang_thai=vou_svc.TT_CHO,
                    ghi_chu=ghi_chu,
                    ma_nv=None,
                    pttt=pttt,
                )
            except BusinessError as e:
                flash(str(e), "error")
            else:
                session.pop("cart", None)
                session["last_order"] = so
                return redirect(url_for("shop.order_success", so_phieu=so))
    return render_template("shop/checkout.html", items=items, total=total, form=form)


@bp.route("/dat-hang-thanh-cong/<so_phieu>")
def order_success(so_phieu):
    if session.get("last_order") != so_phieu:
        abort(404)
    p, lines = vou_svc.lay_phieu_ban(get_db(), so_phieu)
    if p is None:
        abort(404)
    return render_template("shop/order_success.html", p=p, lines=lines)


@bp.route("/tra-cuu-don-hang")
def order_lookup():
    so = (request.args.get("so_phieu") or "").strip().upper()
    sdt = (request.args.get("sdt") or "").strip().replace(" ", "")
    p, lines, searched = None, [], bool(request.args)
    if so and sdt:
        p, lines = vou_svc.lay_phieu_ban(get_db(), so)
        if p is None or (p["SoDienThoai"] or "").replace(" ", "") != sdt:
            p, lines = None, []
    return render_template(
        "shop/order_lookup.html",
        p=p,
        lines=lines,
        searched=searched,
        so_phieu=so,
        sdt=sdt,
    )
