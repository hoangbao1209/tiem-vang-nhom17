"""Kết nối CSDL SQLite (có sẵn trong Python, không cần cài thêm)."""
import os
import sqlite3

import click
from flask import current_app, g


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
        has_new = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='PHIEUKIEMKE'"
        ).fetchone()
        has_col = False
        if has_new:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(SANPHAM)").fetchall()]
            has_col = "ChatLieu" in cols and "TinhTrang" in cols
        conn.close()
        return not (has_new and has_col)
    except sqlite3.Error:
        return True


@click.command("init-db")
@click.option("--no-seed", is_flag=True, help="Chỉ tạo bảng, không thêm dữ liệu mẫu.")
def init_db_command(no_seed):
    """Xóa và tạo lại CSDL."""
    init_db(seed=not no_seed)
    click.echo("Đã khởi tạo lại cơ sở dữ liệu.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    if _needs_schema_upgrade(app.config["DATABASE"]):
        with app.app_context():
            init_db()
