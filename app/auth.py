"""Đăng nhập / đăng xuất và phân quyền (admin, nhân viên)."""
import functools

from flask import (Blueprint, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)


@bp.before_app_request
def load_logged_in_user():
    uid = session.get("user_id")
    g.user = None
    if uid is not None:
        g.user = get_db().execute("SELECT * FROM NGUOIDUNG WHERE MaND = ?", (uid,)).fetchone()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        if g.user["VaiTro"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def is_admin():
    return g.user is not None and g.user["VaiTro"] == "admin"


@bp.route("/dang-nhap", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("TenDangNhap", "").strip()
        password = request.form.get("MatKhau", "")
        user = get_db().execute("SELECT * FROM NGUOIDUNG WHERE TenDangNhap = ?", (username,)).fetchone()
        if user is None or not check_password_hash(user["MatKhau"], password):
            flash("Tên đăng nhập hoặc mật khẩu không đúng.", "error")
        else:
            cart = session.get("cart")
            session.clear()
            if cart:
                session["cart"] = cart
            session["user_id"] = user["MaND"]
            flash(f"Xin chào {user['HoTen']}!", "success")
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("admin.dashboard"))
    return render_template("auth/login.html")


@bp.route("/dang-xuat")
def logout():
    session.pop("user_id", None)
    flash("Đã đăng xuất.", "info")
    return redirect(url_for("shop.index"))
