"""Báo cáo tồn kho & doanh thu theo tháng, kèm hỗ trợ chốt kỳ kế toán."""
from datetime import date, datetime

from ..utils import BusinessError
from .vouchers import TT_HUY


def _khoang_thang(thang, nam):
    start = date(nam, thang, 1)
    end = date(nam + (1 if thang == 12 else 0), thang % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


def lay_ky_ke_toan(conn, thang, nam):
    return conn.execute(
        "SELECT k.*, u.HoTen AS NguoiChot FROM KYKETOAN k "
        "LEFT JOIN NGUOIDUNG u ON u.MaND = k.MaND_Chot "
        "WHERE k.Thang = ? AND k.Nam = ?",
        (thang, nam),
    ).fetchone()


def bao_cao_ton_kho(conn, thang, nam):
    ky = lay_ky_ke_toan(conn, thang, nam)
    if ky is not None:
        saved = conn.execute(
            "SELECT b.MaSP, sp.MaCode, sp.TenSP, l.TenLoaiSP, d.TenDVT, "
            "b.TonDau, b.SoLuongMua AS MuaVao, b.SoLuongBan AS BanRa, b.TonCuoi "
            "FROM BAOCAOTONKHO_THANG b "
            "JOIN SANPHAM sp ON sp.MaSP = b.MaSP "
            "JOIN LOAISANPHAM l ON l.MaLoaiSP = sp.MaLoaiSP "
            "JOIN DONVITINH d ON d.MaDVT = l.MaDVT "
            "WHERE b.MaKy = ? ORDER BY l.MaLoaiSP, sp.TenSP",
            (ky["MaKy"],),
        ).fetchall()
        if saved:
            return [dict(r) for r in saved], ky

    s, e = _khoang_thang(thang, nam)
    sql = """
    SELECT sp.MaSP, sp.MaCode, sp.TenSP, sp.SoLuongTon, l.TenLoaiSP, d.TenDVT,
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
            "MaSP": r["MaSP"],
            "MaCode": r["MaCode"],
            "TenSP": r["TenSP"],
            "TenLoaiSP": r["TenLoaiSP"],
            "TenDVT": r["TenDVT"],
            "TonDau": ton_dau,
            "MuaVao": r["MuaTrong"],
            "BanRa": r["BanTrong"],
            "TonCuoi": ton_cuoi,
        })
    return result, ky


def bao_cao_doanh_thu(conn, thang, nam):
    s, e = _khoang_thang(thang, nam)
    ky = lay_ky_ke_toan(conn, thang, nam)

    sale_days = []
    for r in conn.execute(
        "SELECT substr(NgayLap, 1, 10) AS Ngay, COUNT(*) AS SoGD, SUM(TongTien) AS DoanhThu "
        "FROM PHIEUBANHANG WHERE TrangThai <> ? AND NgayLap >= ? AND NgayLap < ? "
        "GROUP BY Ngay ORDER BY Ngay",
        (TT_HUY, s, e),
    ):
        sale_days.append({"Ngay": r["Ngay"], "SoGD": r["SoGD"], "DoanhThu": r["DoanhThu"]})

    tong_ban = sum(d["DoanhThu"] for d in sale_days)
    for d in sale_days:
        d["TyLe"] = round((d["DoanhThu"] / tong_ban * 100), 2) if tong_ban > 0 else 0

    # Doanh thu dịch vụ tính theo thực thu (THUTIENDICHVU)
    sv_days = []
    for r in conn.execute(
        "SELECT substr(NgayThu, 1, 10) AS Ngay, COUNT(*) AS SoGD, SUM(SoTienThu) AS DoanhThu "
        "FROM THUTIENDICHVU WHERE NgayThu >= ? AND NgayThu < ? "
        "GROUP BY Ngay ORDER BY Ngay",
        (s, e),
    ):
        sv_days.append({"Ngay": r["Ngay"], "SoGD": r["SoGD"], "DoanhThu": r["DoanhThu"]})

    tong_dv = sum(d["DoanhThu"] for d in sv_days)
    for d in sv_days:
        d["TyLe"] = round((d["DoanhThu"] / tong_dv * 100), 2) if tong_dv > 0 else 0

    top = conn.execute(
        "SELECT sp.TenSP, SUM(c.SoLuong) AS SoLuong, SUM(c.ThanhTien) AS DoanhThu "
        "FROM CT_PHIEUBANHANG c JOIN PHIEUBANHANG p ON p.SoPhieu = c.SoPhieu "
        "JOIN SANPHAM sp ON sp.MaSP = c.MaSP "
        "WHERE p.TrangThai <> ? AND p.NgayLap >= ? AND p.NgayLap < ? "
        "GROUP BY c.MaSP ORDER BY DoanhThu DESC LIMIT 5",
        (TT_HUY, s, e),
    ).fetchall()

    return {
        "sale_days": sale_days,
        "sv_days": sv_days,
        "tong_ban": tong_ban,
        "tong_dv": tong_dv,
        "tong_chung": tong_ban + tong_dv,
        "top": top,
        "ky": ky,
    }


def chot_ky_bao_cao(conn, thang, nam, ma_nd):
    if lay_ky_ke_toan(conn, thang, nam) is not None:
        raise BusinessError(f"Kỳ tháng {thang}/{nam} đã được chốt trước đó.")
    ton_rows, _ = bao_cao_ton_kho(conn, thang, nam)
    for r in ton_rows:
        if r["TonCuoi"] < 0 or r["TonDau"] < 0:
            raise BusinessError(f"Sản phẩm “{r['TenSP']}” có tồn kho âm trong kỳ, không thể chốt.")
    dt = bao_cao_doanh_thu(conn, thang, nam)
    by_day = {}
    for d in dt["sale_days"]:
        by_day.setdefault(d["Ngay"], {"Ngay": d["Ngay"], "SoGDBan": 0, "DTBan": 0, "SoGDDV": 0, "DTDV": 0})
        by_day[d["Ngay"]].update(SoGDBan=d["SoGD"], DTBan=d["DoanhThu"])
    for d in dt["sv_days"]:
        by_day.setdefault(d["Ngay"], {"Ngay": d["Ngay"], "SoGDBan": 0, "DTBan": 0, "SoGDDV": 0, "DTDV": 0})
        by_day[d["Ngay"]].update(SoGDDV=d["SoGD"], DTDV=d["DoanhThu"])

    try:
        cur = conn.execute(
            "INSERT INTO KYKETOAN(Thang, Nam, TrangThai, NgayChot, MaND_Chot) VALUES (?, ?, 'Đã chốt', ?, ?)",
            (thang, nam, datetime.now().strftime("%Y-%m-%d %H:%M"), ma_nd),
        )
        ma_ky = cur.lastrowid
        for r in ton_rows:
            conn.execute(
                "INSERT INTO BAOCAOTONKHO_THANG(MaKy, MaSP, TonDau, SoLuongMua, SoLuongBan, TonCuoi) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ma_ky, r["MaSP"], r["TonDau"], r["MuaVao"], r["BanRa"], r["TonCuoi"]),
            )
        for d in sorted(by_day.values(), key=lambda x: x["Ngay"]):
            conn.execute(
                "INSERT INTO BAOCAODOANHTHU_NGAY(MaKy, Ngay, SoGiaoDichBan, DoanhThuBan, "
                "SoGiaoDichDV, DoanhThuDV, TongDoanhThuNgay) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ma_ky, d["Ngay"], d["SoGDBan"], d["DTBan"], d["SoGDDV"], d["DTDV"], d["DTBan"] + d["DTDV"]),
            )
        conn.commit()
        return ma_ky
    except Exception:
        conn.rollback()
        raise
