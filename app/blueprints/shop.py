"""Website bán hàng cho khách: xem sản phẩm, giỏ hàng, đặt hàng, tra cứu đơn."""
import re
from datetime import datetime

from flask import (Blueprint, abort, flash, redirect, render_template, request, session,
                   url_for)

from ..db import get_db
from ..services.catalog import PRODUCT_SELECT, get_product
from ..services.vouchers import NGUON_ONLINE, TT_CHO, lay_phieu_ban, tao_phieu_ban
from ..utils import BusinessError, to_int

bp = Blueprint("shop", __name__)

PHONE_RE = re.compile(r"^0\d{9,10}$")
SORTS = {
    "moi": "sp.MaSP DESC",
    "gia-tang": "DonGiaBan ASC",
    "gia-giam": "DonGiaBan DESC",
    "ten": "sp.TenSP ASC",
}
SORT_LABELS = [("moi", "Mới nhất"), ("gia-tang", "Giá tăng dần"),
               ("gia-giam", "Giá giảm dần"), ("ten", "Tên A → Z")]


# ------------------------------------------------------------------ trang chủ & sản phẩm
@bp.route("/")
def index():
    db = get_db()
    featured = db.execute(
        PRODUCT_SELECT + " WHERE sp.HienThi = 1 AND sp.SoLuongTon > 0 ORDER BY sp.MaSP DESC LIMIT 8"
    ).fetchall()
    categories = db.execute(
        "SELECT l.MaLoaiSP, l.TenLoaiSP, COUNT(sp.MaSP) AS SoSP, MIN(sp.HinhAnh) AS HinhAnh "
        "FROM LOAISANPHAM l LEFT JOIN SANPHAM sp ON sp.MaLoaiSP = l.MaLoaiSP AND sp.HienThi = 1 "
        "GROUP BY l.MaLoaiSP ORDER BY l.MaLoaiSP"
    ).fetchall()
    services = db.execute("SELECT * FROM LOAIDICHVU ORDER BY MaLoaiDV LIMIT 6").fetchall()
    return render_template("shop/index.html", featured=featured, categories=categories, services=services)


@bp.route("/san-pham")
def products():
    db = get_db()
    q = request.args.get("q", "").strip()
    loai = to_int(request.args.get("loai"))
    sort = request.args.get("sort", "moi")
    con_hang = request.args.get("con_hang") == "1"

    where, args = ["sp.HienThi = 1"], []
    if q:
        where.append("(sp.TenSP LIKE ? OR l.TenLoaiSP LIKE ?)")
        args += [f"%{q}%", f"%{q}%"]
    if loai:
        where.append("sp.MaLoaiSP = ?")
        args.append(loai)
    if con_hang:
        where.append("sp.SoLuongTon > 0")
    rows = db.execute(
        PRODUCT_SELECT + " WHERE " + " AND ".join(where) + " ORDER BY " + SORTS.get(sort, SORTS["moi"]),
        args,
    ).fetchall()
    current_cat = db.execute("SELECT * FROM LOAISANPHAM WHERE MaLoaiSP = ?", (loai,)).fetchone() if loai else None
    return render_template("shop/products.html", products=rows, q=q, loai=loai, sort=sort,
                           con_hang=con_hang, current_cat=current_cat, sorts=SORT_LABELS)


@bp.route("/san-pham/<int:ma_sp>")
def product_detail(ma_sp):
    db = get_db()
    p = get_product(db, ma_sp)
    if p is None or not p["HienThi"]:
        abort(404)
    related = db.execute(
        PRODUCT_SELECT + " WHERE sp.HienThi = 1 AND sp.MaLoaiSP = ? AND sp.MaSP <> ? LIMIT 4",
        (p["MaLoaiSP"], ma_sp),
    ).fetchall()
    return render_template("shop/product_detail.html", p=p, related=related)


@bp.route("/dich-vu")
def dich_vu():
    services = get_db().execute("SELECT * FROM LOAIDICHVU ORDER BY MaLoaiDV").fetchall()
    return render_template("shop/services.html", services=services)


# ------------------------------------------------------------------ giỏ hàng (lưu trong session)
def cart_items(db):
    cart = session.get("cart", {})
    items, total = [], 0
    for ma, sl in cart.items():
        p = get_product(db, int(ma))
        if p is None or not p["HienThi"]:
            continue
        item = dict(p)
        item["SoLuong"] = sl
        item["ThanhTien"] = sl * p["DonGiaBan"]
        items.append(item)
        total += item["ThanhTien"]
    return items, total


@bp.route("/gio-hang")
def cart():
    items, total = cart_items(get_db())
    return render_template("shop/cart.html", items=items, total=total)


@bp.route("/gio-hang/them", methods=["POST"])
def cart_add():
    ma = to_int(request.form.get("MaSP"))
    sl = max(to_int(request.form.get("SoLuong"), 1) or 1, 1)
    p = get_product(get_db(), ma) if ma else None
    back = request.referrer or url_for("shop.products")
    if p is None or not p["HienThi"]:
        flash("Sản phẩm không tồn tại.", "error")
        return redirect(back)

    cart = session.get("cart", {})
    new_qty = cart.get(str(ma), 0) + sl
    if p["SoLuongTon"] <= 0:
        flash(f"“{p['TenSP']}” tạm hết hàng.", "error")
        return redirect(back)
    if new_qty > p["SoLuongTon"]:
        new_qty = p["SoLuongTon"]
        flash(f"“{p['TenSP']}” chỉ còn {p['SoLuongTon']} {p['TenDVT']}, giỏ hàng đã được điều chỉnh.", "info")
    else:
        flash(f"Đã thêm “{p['TenSP']}” vào giỏ hàng.", "success")
    cart[str(ma)] = new_qty
    session["cart"] = cart

    if request.form.get("buy_now"):
        return redirect(url_for("shop.checkout"))
    return redirect(back)


@bp.route("/gio-hang/cap-nhat", methods=["POST"])
def cart_update():
    db = get_db()
    cart = session.get("cart", {})
    for ma in list(cart.keys()):
        qty = to_int(request.form.get(f"qty_{ma}"), cart[ma])
        p = get_product(db, int(ma))
        if p is None or qty is None or qty <= 0:
            cart.pop(ma)
            continue
        cart[ma] = min(qty, p["SoLuongTon"]) if p["SoLuongTon"] > 0 else 0
        if cart[ma] <= 0:
            cart.pop(ma)
    session["cart"] = cart
    flash("Đã cập nhật giỏ hàng.", "success")
    return redirect(url_for("shop.cart"))


@bp.route("/gio-hang/xoa/<int:ma_sp>", methods=["POST"])
def cart_remove(ma_sp):
    cart = session.get("cart", {})
    cart.pop(str(ma_sp), None)
    session["cart"] = cart
    return redirect(url_for("shop.cart"))


# ------------------------------------------------------------------ đặt hàng
@bp.route("/thanh-toan", methods=["GET", "POST"])
def checkout():
    db = get_db()
    items, total = cart_items(db)
    if not items:
        flash("Giỏ hàng đang trống.", "info")
        return redirect(url_for("shop.products"))

    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        ten = form.get("TenKH", "").strip()
        sdt = form.get("SoDienThoai", "").strip().replace(" ", "")
        dia_chi = form.get("DiaChi", "").strip()
        email = form.get("Email", "").strip()
        ghi_chu = form.get("GhiChu", "").strip()

        errors = []
        if not ten:
            errors.append("Vui lòng nhập họ tên.")
        if not PHONE_RE.match(sdt):
            errors.append("Số điện thoại không hợp lệ (10–11 chữ số, bắt đầu bằng 0).")
        if not dia_chi:
            errors.append("Vui lòng nhập địa chỉ nhận hàng.")
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            try:
                so = tao_phieu_ban(
                    db,
                    {"ten": ten, "sdt": sdt, "dia_chi": dia_chi, "email": email},
                    [{"MaSP": i["MaSP"], "SoLuong": i["SoLuong"]} for i in items],
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    nguon=NGUON_ONLINE, trang_thai=TT_CHO, ghi_chu=ghi_chu,
                )
            except BusinessError as e:
                flash(str(e), "error")
            else:
                session.pop("cart", None)
                session["last_order"] = so
                return redirect(url_for("shop.order_success", so_phieu=so))
    return render_template("shop/checkout.html", items=items, total=total, form=form)


@bp.route("/dat-hang-thanh-cong/<int:so_phieu>")
def order_success(so_phieu):
    if session.get("last_order") != so_phieu:
        abort(404)
    p, lines = lay_phieu_ban(get_db(), so_phieu)
    if p is None:
        abort(404)
    return render_template("shop/order_success.html", p=p, lines=lines)


@bp.route("/tra-cuu-don-hang")
def order_lookup():
    so = to_int(request.args.get("so_phieu"))
    sdt = request.args.get("sdt", "").strip().replace(" ", "")
    p, lines, searched = None, [], bool(request.args)
    if so and sdt:
        p, lines = lay_phieu_ban(get_db(), so)
        if p is None or p["SoDienThoai"] != sdt:
            p, lines = None, []
    return render_template("shop/order_lookup.html", p=p, lines=lines, searched=searched,
                           so_phieu=so or "", sdt=sdt)
