"""Báo cáo: tồn kho theo tháng, doanh thu theo tháng."""
from datetime import date

from .vouchers import TT_HUY


def _khoang_thang(thang, nam):
    start = date(nam, thang, 1)
    end = date(nam + (1 if thang == 12 else 0), thang % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


def bao_cao_ton_kho(conn, thang, nam):
    """Tồn cuối tháng = Tồn hiện tại - SL mua sau tháng + SL bán sau tháng
       Tồn đầu tháng  = Tồn cuối - SL mua trong tháng + SL bán trong tháng
    (Phiếu bán đã hủy không được tính.)"""
    s, e = _khoang_thang(thang, nam)
    sql = """
    SELECT sp.MaSP, sp.TenSP, sp.SoLuongTon, l.TenLoaiSP, d.TenDVT,
      COALESCE((SELECT SUM(c.SoLuong) FROM CT_PHIEUMUAHANG c JOIN PHIEUMUAHANG p ON p.SoPhieu = c.SoPhieu
                WHERE c.MaSP = sp.MaSP AND p.NgayLap >= :s AND p.NgayLap < :e), 0) AS MuaTrong,
      COALESCE((SELECT SUM(c.SoLuong) FROM CT_PHIEUMUAHANG c JOIN PHIEUMUAHANG p ON p.SoPhieu = c.SoPhieu
                WHERE c.MaSP = sp.MaSP AND p.NgayLap >= :e), 0) AS MuaSau,
      COALESCE((SELECT SUM(c.SoLuong) FROM CT_PHIEUBANHANG c JOIN PHIEUBANHANG p ON p.SoPhieu = c.SoPhieu
                WHERE c.MaSP = sp.MaSP AND p.TrangThai <> :huy AND p.NgayLap >= :s AND p.NgayLap < :e), 0) AS BanTrong,
      COALESCE((SELECT SUM(c.SoLuong) FROM CT_PHIEUBANHANG c JOIN PHIEUBANHANG p ON p.SoPhieu = c.SoPhieu
                WHERE c.MaSP = sp.MaSP AND p.TrangThai <> :huy AND p.NgayLap >= :e), 0) AS BanSau
    FROM SANPHAM sp
    JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP
    JOIN DONVITINH d ON d.MaDVT = l.MaDVT
    ORDER BY l.MaLoaiSP, sp.TenSP
    """
    result = []
    for r in conn.execute(sql, {"s": s, "e": e, "huy": TT_HUY}):
        ton_cuoi = r["SoLuongTon"] - r["MuaSau"] + r["BanSau"]
        ton_dau = ton_cuoi - r["MuaTrong"] + r["BanTrong"]
        result.append({
            "MaSP": r["MaSP"], "TenSP": r["TenSP"], "TenLoaiSP": r["TenLoaiSP"], "TenDVT": r["TenDVT"],
            "TonDau": ton_dau, "MuaVao": r["MuaTrong"], "BanRa": r["BanTrong"], "TonCuoi": ton_cuoi,
        })
    return result


def bao_cao_doanh_thu(conn, thang, nam):
    s, e = _khoang_thang(thang, nam)
    by_day = {}
    for r in conn.execute(
        "SELECT substr(NgayLap, 1, 10) AS Ngay, COUNT(*) AS SoPhieu, SUM(TongTien) AS Tien "
        "FROM PHIEUBANHANG WHERE TrangThai <> ? AND NgayLap >= ? AND NgayLap < ? GROUP BY Ngay",
        (TT_HUY, s, e),
    ):
        by_day.setdefault(r["Ngay"], {"Ngay": r["Ngay"], "SoPhieuBan": 0, "BanHang": 0, "SoPhieuDV": 0, "DichVu": 0})
        by_day[r["Ngay"]].update(SoPhieuBan=r["SoPhieu"], BanHang=r["Tien"])
    for r in conn.execute(
        "SELECT substr(NgayLap, 1, 10) AS Ngay, COUNT(*) AS SoPhieu, SUM(TongTien) AS Tien "
        "FROM PHIEUDICHVU WHERE NgayLap >= ? AND NgayLap < ? GROUP BY Ngay",
        (s, e),
    ):
        by_day.setdefault(r["Ngay"], {"Ngay": r["Ngay"], "SoPhieuBan": 0, "BanHang": 0, "SoPhieuDV": 0, "DichVu": 0})
        by_day[r["Ngay"]].update(SoPhieuDV=r["SoPhieu"], DichVu=r["Tien"])
    days = sorted(by_day.values(), key=lambda x: x["Ngay"])
    for d in days:
        d["Tong"] = d["BanHang"] + d["DichVu"]

    top = conn.execute(
        "SELECT sp.TenSP, SUM(c.SoLuong) AS SoLuong, SUM(c.ThanhTien) AS DoanhThu "
        "FROM CT_PHIEUBANHANG c JOIN PHIEUBANHANG p ON p.SoPhieu = c.SoPhieu "
        "JOIN SANPHAM sp ON sp.MaSP = c.MaSP "
        "WHERE p.TrangThai <> ? AND p.NgayLap >= ? AND p.NgayLap < ? "
        "GROUP BY c.MaSP ORDER BY DoanhThu DESC LIMIT 5",
        (TT_HUY, s, e),
    ).fetchall()
    return days, top
