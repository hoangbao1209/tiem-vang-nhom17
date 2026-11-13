"""Truy vấn sản phẩm dùng chung. Đơn giá bán được TÍNH, không lưu:
    Đơn giá bán = Đơn giá mua × (1 + % lợi nhuận của loại sản phẩm)
"""

PRODUCT_SELECT = """
SELECT sp.MaSP, sp.TenSP, sp.MaLoaiSP, sp.DonGiaMua, sp.SoLuongTon, sp.MoTa,
       sp.HinhAnh, sp.HienThi, l.TenLoaiSP, l.PhanTramLoiNhuan, d.TenDVT,
       ROUND(sp.DonGiaMua * (1 + l.PhanTramLoiNhuan / 100.0)) AS DonGiaBan
FROM SANPHAM sp
JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP
JOIN DONVITINH d   ON d.MaDVT = l.MaDVT
"""


def get_product(conn, ma_sp):
    return conn.execute(PRODUCT_SELECT + " WHERE sp.MaSP = ?", (ma_sp,)).fetchone()
