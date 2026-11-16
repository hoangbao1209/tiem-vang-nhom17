"""Tham số hệ thống và nhật ký thay đổi quy định."""
from datetime import datetime

DEFAULTS = {
    "TenCuaHang": "Tiệm Vàng Kim Ngân",
    "DiaChi": "123 Lê Lợi, Quận 1, TP. Hồ Chí Minh",
    "SoDienThoai": "0909 123 456",
    "Email": "lienhe@kimngan.vn",
    "SoLuongTonToiThieu": "2",
    "TiLeTraTruocToiThieu": "50",
}

PARAM_LABELS = [
    ("TenCuaHang", "Tên cửa hàng"),
    ("DiaChi", "Địa chỉ"),
    ("SoDienThoai", "Số điện thoại"),
    ("Email", "Email liên hệ"),
    ("SoLuongTonToiThieu", "Ngưỡng cảnh báo sắp hết hàng (số lượng tồn ≤)"),
    ("TiLeTraTruocToiThieu", "Tỷ lệ trả trước tối thiểu mặc định khi lập phiếu dịch vụ (%)"),
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


def log_rule_change(conn, loai, ma_doi_tuong, gia_tri_cu, gia_tri_moi, ma_nd=None, ghi_chu=None):
    conn.execute(
        "INSERT INTO NHATKYTHAYDOIQUYDINH(LoaiQuyDinh, MaDoiTuong, GiaTriCu, GiaTriMoi, "
        "ThoiDiemCapNhat, MaND_CapNhat, GhiChu) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            loai,
            str(ma_doi_tuong),
            str(gia_tri_cu) if gia_tri_cu is not None else None,
            str(gia_tri_moi),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ma_nd,
            ghi_chu,
        ),
    )
