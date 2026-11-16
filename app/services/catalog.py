"""Truy vấn sản phẩm dùng chung.
Đơn giá bán = Đơn giá mua × (1 + % lợi nhuận của loại sản phẩm).
"""

PRODUCT_SELECT = """
SELECT sp.MaSP, sp.MaCode, sp.TenSP, sp.MaLoaiSP, sp.DonGiaMua, sp.SoLuongTon,
       sp.ChatLieu, sp.TuoiVang, sp.TrongLuong, sp.BaoHanh, sp.MoTa,
       sp.HinhAnh, sp.TinhTrang, sp.HienThi,
       l.TenLoaiSP, l.PhanTramLoiNhuan, d.TenDVT,
       ROUND(sp.DonGiaMua * (1 + l.PhanTramLoiNhuan / 100.0)) AS DonGiaBan,
       CASE
         WHEN EXISTS (SELECT 1 FROM CT_PHIEUMUAHANG m WHERE m.MaSP = sp.MaSP)
           OR EXISTS (SELECT 1 FROM CT_PHIEUBANHANG b WHERE b.MaSP = sp.MaSP)
           OR EXISTS (SELECT 1 FROM CT_PHIEUKIEMKE k WHERE k.MaSP = sp.MaSP)
         THEN 1 ELSE 0
       END AS DaPhatSinh
FROM SANPHAM sp
JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP
JOIN DONVITINH d   ON d.MaDVT = l.MaDVT
"""


def get_product(conn, ma_sp):
    return conn.execute(PRODUCT_SELECT + " WHERE sp.MaSP = ?", (ma_sp,)).fetchone()
