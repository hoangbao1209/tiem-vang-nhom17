"""Tham số hệ thống (bảng THAMSO)."""

DEFAULTS = {
    "TenCuaHang": "Tiệm Vàng Kim Ngân",
    "DiaChi": "",
    "SoDienThoai": "",
    "Email": "",
    "SoLuongTonToiThieu": "2",
}

# Thứ tự + nhãn hiển thị trên trang "Thay đổi quy định"
PARAM_LABELS = [
    ("TenCuaHang", "Tên cửa hàng"),
    ("DiaChi", "Địa chỉ"),
    ("SoDienThoai", "Số điện thoại"),
    ("Email", "Email"),
    ("SoLuongTonToiThieu", "Cảnh báo sắp hết hàng khi tồn ≤"),
]


def get_params(conn):
    params = dict(DEFAULTS)
    for row in conn.execute("SELECT TenThamSo, GiaTri FROM THAMSO"):
        params[row["TenThamSo"]] = row["GiaTri"]
    return params


def set_param(conn, name, value):
    conn.execute(
        "INSERT INTO THAMSO(TenThamSo, GiaTri) VALUES (?, ?) "
        "ON CONFLICT(TenThamSo) DO UPDATE SET GiaTri = excluded.GiaTri",
        (name, value),
    )
