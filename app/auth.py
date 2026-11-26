"""Tầng Điều khiển Xác thực & Phân quyền (Presentation Controller – không chứa SQL)."""
import functools

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from .db import get_db
from .services import settings as settings_svc
from .utils import BusinessError

bp = Blueprint("auth", __name__)


@bp.before_app_request
def load_logged_in_user():
    ma_nv = session.get("user_id")
    g.user = None
    if ma_nv is not None:
        u = settings_svc.lay_nguoi_dung(get_db(), ma_nv)
        if u is not None and u["TinhTrang"] == "Đang làm việc":
            g.user = u
        else:
            session.pop("user_id", None)


def is_manager():
    return g.user is not None and g.user["VaiTro"] == "QuanLy"


def can_revert_service():
    return g.user is not None and (g.user["VaiTro"] == "QuanLy" or bool(g.user["CoQuyenChuyenNguoc"]))


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def manager_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        if not is_manager():
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@bp.route("/dang-nhap", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        username = request.form.get("TenDangNhap", "")
        password = request.form.get("MatKhau", "")
        try:
            user = settings_svc.xac_thuc_dang_nhap(get_db(), username, password)
        except BusinessError as e:
            flash(str(e), "error")
        else:
            cart = session.get("cart")
            session.clear()
            if cart:
                session["cart"] = cart
            session["user_id"] = user["MaNV"]
            flash(f"Xin chào {user['TenNV']}!", "success")
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("admin.dashboard"))
    return render_template("auth/login.html")


@bp.route("/doi-mat-khau", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        try:
            settings_svc.doi_mat_khau(
                get_db(),
                g.user["MaNV"],
                request.form.get("MatKhauCu", ""),
                request.form.get("MatKhauMoi", ""),
                request.form.get("XacNhan", ""),
            )
            flash("Đã đổi mật khẩu thành công.", "success")
            return redirect(url_for("admin.dashboard"))
        except BusinessError as e:
            flash(str(e), "error")
    return render_template("auth/change_password.html")


@bp.route("/dang-xuat")
def logout():
    session.pop("user_id", None)
    flash("Đã đăng xuất khỏi hệ thống quản lý.", "info")
    return redirect(url_for("shop.index"))
