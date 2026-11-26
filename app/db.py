"""Tầng Dữ liệu (Data Layer): Kết nối SQLite, khởi tạo CSDL, Sao lưu & Phục hồi."""
import os
import shutil
import sqlite3
from datetime import datetime

import click
from flask import current_app, g


REQUIRED_TABLES = {
    "DONVITINH", "LOAISANPHAM", "SANPHAM", "NHACUNGCAP", "DICHVU", "NGUOIDUNG",
    "PHIEUMUAHANG", "CT_PHIEUMUAHANG", "PHIEUBANHANG", "CT_PHIEUBANHANG",
    "THAMSO", "PHIEUDICHVU", "CT_PHIEUDICHVU", "THUTIENDICHVU", "LICHSUTINHTRANG",
    "PHIEUKIEMKE", "CT_PHIEUKIEMKE", "KYKETOAN", "BAOCAOTONKHO_THANG",
    "BAOCAODOANHTHU_NGAY", "NHATKYTHAYDOIQUYDINH",
}


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"], timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(e=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(seed=True):
    conn = get_db()
    with current_app.open_resource("schema.sql") as f:
        conn.executescript(f.read().decode("utf-8"))
    conn.execute("PRAGMA foreign_keys = ON")
    if seed:
        from .seed import seed_data
        seed_data(conn)
    conn.commit()


def _needs_schema_upgrade(db_path):
    if not os.path.exists(db_path):
        return True
    try:
        conn = sqlite3.connect(db_path, timeout=15)
        existing = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if not REQUIRED_TABLES.issubset(existing):
            conn.close()
            return True
        user_cols = {r[1] for r in conn.execute("PRAGMA table_info(NGUOIDUNG)").fetchall()}
        param_cols = {r[1] for r in conn.execute("PRAGMA table_info(THAMSO)").fetchall()}
        conn.close()
        return not ({"MaNV", "TenNV", "CoQuyenChuyenNguoc"}.issubset(user_cols)
                    and {"MaThamSo", "TiLeTraTruoc"}.issubset(param_cols))
    except sqlite3.Error:
        return True


def backup_database(label="manual"):
    """Tạo bản sao lưu nóng an toàn bằng SQLite Backup API (YCHT07)."""
    src_path = current_app.config["DATABASE"]
    backup_dir = current_app.config["BACKUP_FOLDER"]
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(ch for ch in label if ch.isalnum() or ch in ("-", "_"))[:24] or "backup"
    filename = f"tiemvang_{safe_label}_{ts}.db"
    dst_path = os.path.join(backup_dir, filename)

    src_conn = sqlite3.connect(src_path, timeout=15)
    dst_conn = sqlite3.connect(dst_path)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()
    return filename, dst_path


def list_backups():
    """Liệt kê các bản sao lưu hiện có (mới nhất trước)."""
    backup_dir = current_app.config["BACKUP_FOLDER"]
    if not os.path.isdir(backup_dir):
        return []
    items = []
    for name in os.listdir(backup_dir):
        if not name.endswith(".db"):
            continue
        full = os.path.join(backup_dir, name)
        if os.path.isfile(full):
            st = os.stat(full)
            items.append({
                "filename": name,
                "size_kb": round(st.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
                "mtime": st.st_mtime,
            })
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


def validate_backup_file(path):
    """Kiểm tra tính toàn vẹn SQLite và đủ 21 bảng trước khi phục hồi."""
    conn = None
    try:
        conn = sqlite3.connect(path, timeout=10)
        check = conn.execute("PRAGMA quick_check").fetchone()
        if not check or check[0] != "ok":
            return False, "Tệp sao lưu bị hỏng hoặc không phải tệp SQLite hợp lệ."
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if not REQUIRED_TABLES.issubset(tables):
            return False, "Tệp sao lưu không đúng cấu trúc 21 bảng của hệ thống."
        return True, None
    except sqlite3.Error:
        return False, "Không thể đọc tệp sao lưu (định dạng không hợp lệ)."
    finally:
        if conn is not None:
            conn.close()


def restore_database(source_path):
    """Phục hồi CSDL từ bản sao lưu sau khi sao lưu dự phòng trạng thái hiện tại."""
    ok, err = validate_backup_file(source_path)
    if not ok:
        raise ValueError(err)

    # Tạo bản sao lưu an toàn trước khi ghi đè
    backup_database(label="truoc_phuc_hoi")

    # Đóng kết nối đang mở trên request hiện tại
    close_db()

    dst_path = current_app.config["DATABASE"]
    src_conn = sqlite3.connect(source_path, timeout=15)
    dst_conn = sqlite3.connect(dst_path, timeout=15)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


@click.command("init-db")
@click.option("--no-seed", is_flag=True, help="Chỉ tạo 21 bảng, không nạp dữ liệu mẫu.")
def init_db_command(no_seed):
    """Xóa và khởi tạo lại cơ sở dữ liệu."""
    init_db(seed=not no_seed)
    click.echo("Đã khởi tạo lại cơ sở dữ liệu 21 bảng.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    db_path = app.config["DATABASE"]
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(app.config["BACKUP_FOLDER"], exist_ok=True)
    if _needs_schema_upgrade(db_path):
        # Nếu đã tồn tại DB phiên bản cũ, chép lưu dự phòng để không mất dấu vết
        if os.path.exists(db_path):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            legacy_bak = os.path.join(app.config["BACKUP_FOLDER"], f"legacy_before_upgrade_{ts}.db")
            try:
                shutil.copy2(db_path, legacy_bak)
            except OSError:
                pass
        with app.app_context():
            init_db()
