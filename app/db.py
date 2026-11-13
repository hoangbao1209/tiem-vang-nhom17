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


@click.command("init-db")
@click.option("--no-seed", is_flag=True, help="Chỉ tạo bảng, không thêm dữ liệu mẫu.")
def init_db_command(no_seed):
    """Xóa và tạo lại CSDL."""
    init_db(seed=not no_seed)
    click.echo("Đã khởi tạo lại cơ sở dữ liệu.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    # Lần chạy đầu tiên: tự tạo CSDL + dữ liệu mẫu
    if not os.path.exists(app.config["DATABASE"]):
        with app.app_context():
            init_db()
