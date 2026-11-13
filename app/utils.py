"""Hàm tiện ích dùng chung: định dạng tiền/ngày, đọc dữ liệu form, lỗi nghiệp vụ."""
from datetime import date, datetime

from flask import session, url_for

PLACEHOLDER_IMG = "img/products/gem.svg"


class BusinessError(Exception):
    """Lỗi vi phạm quy định nghiệp vụ (hiển thị trực tiếp cho người dùng)."""


# ---------- Chuyển kiểu an toàn ----------
def to_int(value, default=None):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def to_float(value, default=None):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def parse_date(value, label="Ngày"):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise BusinessError(f"{label} không hợp lệ.")


def validate_ngay_lap(value):
    d = parse_date(value, "Ngày lập")
    if d > date.today().isoformat():
        raise BusinessError("Ngày lập không được sau ngày hiện tại.")
    return d


def rows_from_form(form, fields):
    """Gom các input cùng tên (MaSP, SoLuong, ...) thành danh sách dòng chi tiết."""
    cols = [form.getlist(f) for f in fields]
    n = max((len(c) for c in cols), default=0)
    return [
        {f: (cols[i][r].strip() if r < len(cols[i]) else "") for i, f in enumerate(fields)}
        for r in range(n)
    ]


# ---------- Định dạng hiển thị ----------
def format_vnd(value):
    if value is None or value == "":
        value = 0
    try:
        return f"{float(value):,.0f}".replace(",", ".") + " ₫"
    except (TypeError, ValueError):
        return str(value)


def format_number(value):
    try:
        return f"{float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return value


def format_plain(value):
    """15.0 -> 15 ; 12.5 -> 12.5 (dùng cho ô nhập liệu)."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return "" if value is None else value


def format_date(value):
    if not value:
        return ""
    s = str(value)
    try:
        if len(s) > 10:
            return datetime.strptime(s[:16], "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return s


def product_img(p):
    path = p["HinhAnh"] if p is not None and p["HinhAnh"] else PLACEHOLDER_IMG
    if path.startswith(("http://", "https://")):
        return path
    return url_for("static", filename=path)


def register_template_helpers(app):
    app.jinja_env.filters["vnd"] = format_vnd
    app.jinja_env.filters["num"] = format_number
    app.jinja_env.filters["plain"] = format_plain
    app.jinja_env.filters["date"] = format_date
    app.jinja_env.globals["product_img"] = product_img

    @app.context_processor
    def inject_globals():
        from .db import get_db
        from .services.settings import get_params

        db = get_db()
        cart = session.get("cart", {})
        cats = db.execute("SELECT MaLoaiSP, TenLoaiSP FROM LOAISANPHAM ORDER BY MaLoaiSP").fetchall()
        return {
            "cart_count": sum(cart.values()),
            "nav_categories": cats,
            "store": get_params(db),
            "today": date.today().isoformat(),
        }
