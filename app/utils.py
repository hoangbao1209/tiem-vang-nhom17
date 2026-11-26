"""Hàm tiện ích chung: định dạng tiền tệ/số lượng/ngày tháng, xác thực đầu vào, BusinessError."""
from datetime import date, datetime

from flask import current_app, session, url_for

PLACEHOLDER_IMG = "img/products/ring-solitaire.jpg"


class BusinessError(Exception):
    """Lỗi vi phạm quy định nghiệp vụ (hiển thị rõ nguyên nhân cho người dùng – CL03)."""


# ------------------------------------------------------------------ CHUYỂN KIỂU AN TOÀN
def to_int(value, default=None):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def to_float(value, default=None):
    try:
        s = str(value).strip().replace(",", ".")
        return float(s)
    except (TypeError, ValueError):
        return default


def parse_date(value, label="Ngày"):
    s = (value or "").strip()
    if len(s) >= 10:
        s = s[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise BusinessError(f"{label} không hợp lệ (định dạng chuẩn YYYY-MM-DD).")


def validate_ngay_lap(value, label="Ngày lập"):
    d = parse_date(value, label)
    if d > date.today().isoformat():
        raise BusinessError(f"{label} không được lớn hơn ngày hiện tại ({date.today().strftime('%d/%m/%Y')}).")
    return d


def rows_from_form(form, fields):
    """Gom các cột dữ liệu mảng từ form thành danh sách từ điển từng dòng."""
    cols = [form.getlist(f) for f in fields]
    n = max((len(c) for c in cols), default=0)
    return [
        {f: (cols[i][r].strip() if r < len(cols[i]) else "") for i, f in enumerate(fields)}
        for r in range(n)
    ]


# ------------------------------------------------------------------ ĐỊNH DẠNG HIỂN THỊ (YCHT06)
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


def format_qty(value):
    """Hiển thị số lượng gọn: 2.0 -> '2', 1.5 -> '1.5', 0.25 -> '0.25'."""
    if value is None or value == "":
        return "0"
    try:
        num = round(float(value), 3)
        if abs(num - round(num)) < 1e-9:
            return str(int(round(num)))
        return f"{num:g}"
    except (TypeError, ValueError):
        return str(value)


def format_pct(value):
    """Hiển thị tỷ lệ thập phân sang %: 0.15 -> '15%', 0.025 -> '2.5%'."""
    if value is None or value == "":
        return "0%"
    try:
        pct = round(float(value) * 100.0, 2)
        if abs(pct - round(pct)) < 1e-9:
            return f"{int(round(pct))}%"
        return f"{pct:g}%"
    except (TypeError, ValueError):
        return str(value)


def format_pct_num(value):
    """Chuyển tỷ lệ thập phân thành số % dùng trong ô input: 0.15 -> 15."""
    if value is None or value == "":
        return 0
    try:
        pct = round(float(value) * 100.0, 2)
        if abs(pct - round(pct)) < 1e-9:
            return int(round(pct))
        return pct
    except (TypeError, ValueError):
        return 0


def format_plain(value):
    """Dùng cho thuộc tính value của input số: 150000.0 -> 150000."""
    if value is None:
        return ""
    if isinstance(value, float) and abs(value - round(value)) < 1e-9:
        return int(round(value))
    return value


def format_date(value):
    if not value:
        return ""
    s = str(value).strip()
    try:
        if len(s) >= 16:
            return datetime.strptime(s[:16], "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
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
    app.jinja_env.filters["qty"] = format_qty
    app.jinja_env.filters["pct"] = format_pct
    app.jinja_env.filters["pct_num"] = format_pct_num
    app.jinja_env.filters["plain"] = format_plain
    app.jinja_env.filters["date"] = format_date
    app.jinja_env.globals["product_img"] = product_img

    @app.context_processor
    def inject_globals():
        from .db import get_db
        from . import repositories as repo

        db = get_db()
        cart = session.get("cart", {})
        cats = repo.list_categories(db)
        tham_so = repo.get_tham_so(db)
        return {
            "cart_count": sum(cart.values()),
            "nav_categories": cats,
            "store": current_app.config["STORE_INFO"],
            "today": date.today().isoformat(),
            "ti_le_tra_truoc_pct": format_pct_num(tham_so["TiLeTraTruoc"]),
        }
