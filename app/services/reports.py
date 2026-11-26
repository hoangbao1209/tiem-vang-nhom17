"""Tầng Nghiệp vụ (Business Layer): Báo cáo Tồn kho, Báo cáo Doanh thu,
Chốt kỳ & Khóa kỳ kế toán, và dữ liệu Tổng quan điều hành.
"""
from datetime import date, datetime

from .. import repositories as repo
from ..utils import BusinessError


def _khoang_thang(thang, nam):
    start = date(nam, thang, 1)
    end = date(nam + (1 if thang == 12 else 0), thang % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


def _thang_truoc(thang, nam):
    return (12, nam - 1) if thang == 1 else (thang - 1, nam)


# ------------------------------------------------------------------ TỔNG QUAN & KHÁCH HÀNG
def lay_du_lieu_tong_quan(conn, min_ton=2):
    today = date.today()
    ym = f"{today.year:04d}-{today.month:02d}"
    stats = repo.query_dashboard_stats(conn, ym)
    low_stock = repo.list_products(
        conn, tinh_trang="Đang kinh doanh", stock_filter="sap_het",
        min_ton_warning=min_ton, order_by="sp.SoLuongTon ASC, sp.MaSP ASC", limit=8,
    )
    out_of_stock = repo.list_products(
        conn, tinh_trang="Đang kinh doanh", stock_filter="het",
        order_by="sp.MaSP ASC", limit=6,
    )
    pending_orders = repo.list_sales(conn, trang_thai="Chờ xử lý", limit=6)
    recent_sales = repo.list_sales(conn, limit=6)
    recent_services = repo.list_service_vouchers(conn, limit=6)

    # Doanh thu 6 tháng gần nhất (phục vụ biểu đồ cột thuần CSS trên Dashboard)
    monthly_series = []
    for offset in range(5, -1, -1):
        m = today.month - offset
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        s, e = _khoang_thang(m, y)
        ban = sum(r["DoanhThu"] for r in repo.query_live_sales_by_day(conn, s, e))
        dv = sum(r["DoanhThu"] for r in repo.query_live_service_revenue_by_day(conn, s, e))
        monthly_series.append({"label": f"T{m}/{str(y)[-2:]}", "ban": ban, "dv": dv, "tong": ban + dv})
    max_rev = max((x["tong"] for x in monthly_series), default=0) or 1
    for item in monthly_series:
        item["pct_h"] = round(item["tong"] / max_rev * 100, 1) if item["tong"] > 0 else 4

    return {
        "thang": today.month,
        "nam": today.year,
        **stats,
        "min_ton": min_ton,
        "low_stock": list(out_of_stock) + list(low_stock),
        "pending_orders": pending_orders,
        "recent_sales": recent_sales,
        "recent_services": recent_services,
        "monthly_series": monthly_series,
    }


def lay_danh_sach_khach_hang(conn, q=""):
    return repo.query_customer_directory(conn, q=q)


# ------------------------------------------------------------------ BÁO CÁO TỒN KHO
def bao_cao_ton_kho(conn, thang, nam):
    ky = repo.get_period(conn, thang, nam)
    if ky is not None and ky["TrangThai"] in ("Đã chốt", "Đã khóa"):
        saved = repo.get_closed_inventory_rows(conn, ky["MaKy"])
        if saved:
            return [dict(r) for r in saved], ky

    s, e = _khoang_thang(thang, nam)
    rows = repo.query_live_inventory_movements(conn, s, e)
    result = []
    for r in rows:
        ton_cuoi = round(float(r["SoLuongTon"]) - float(r["MuaSau"]) + float(r["BanSau"]), 3)
        ton_dau = round(ton_cuoi - float(r["MuaTrong"]) + float(r["BanTrong"]), 3)
        result.append({
            "MaSP": r["MaSP"],
            "TenSP": r["TenSP"],
            "TenLoaiSP": r["TenLoaiSP"],
            "TenDVT": r["TenDVT"],
            "TonDau": ton_dau,
            "MuaVao": round(float(r["MuaTrong"]), 3),
            "BanRa": round(float(r["BanTrong"]), 3),
            "TonCuoi": ton_cuoi,
        })
    return result, ky


# ------------------------------------------------------------------ BÁO CÁO DOANH THU
def bao_cao_doanh_thu(conn, thang, nam):
    s, e = _khoang_thang(thang, nam)
    ky = repo.get_period(conn, thang, nam)

    sale_days = []
    sv_days = []
    if ky is not None and ky["TrangThai"] in ("Đã chốt", "Đã khóa"):
        for r in repo.get_closed_revenue_rows(conn, ky["MaKy"]):
            if r["SoGiaoDichBan"] > 0 or r["DoanhThuBan"] > 0:
                sale_days.append({"Ngay": r["Ngay"], "SoGD": r["SoGiaoDichBan"], "DoanhThu": r["DoanhThuBan"]})
            if r["SoGiaoDichDV"] > 0 or r["DoanhThuDV"] > 0:
                sv_days.append({"Ngay": r["Ngay"], "SoGD": r["SoGiaoDichDV"], "DoanhThu": r["DoanhThuDV"]})
    else:
        for r in repo.query_live_sales_by_day(conn, s, e):
            sale_days.append({"Ngay": r["Ngay"], "SoGD": r["SoGD"], "DoanhThu": r["DoanhThu"]})
        for r in repo.query_live_service_revenue_by_day(conn, s, e):
            sv_days.append({"Ngay": r["Ngay"], "SoGD": r["SoGD"], "DoanhThu": r["DoanhThu"]})

    tong_ban = round(sum(d["DoanhThu"] for d in sale_days), 2)
    for d in sale_days:
        d["TyLe"] = round((d["DoanhThu"] / tong_ban * 100.0), 2) if tong_ban > 0 else 0

    tong_dv = round(sum(d["DoanhThu"] for d in sv_days), 2)
    for d in sv_days:
        d["TyLe"] = round((d["DoanhThu"] / tong_dv * 100.0), 2) if tong_dv > 0 else 0

    top = repo.query_top_selling_products(conn, s, e, limit=5)

    return {
        "sale_days": sale_days,
        "sv_days": sv_days,
        "tong_ban": tong_ban,
        "tong_dv": tong_dv,
        "tong_chung": round(tong_ban + tong_dv, 2),
        "top": top,
        "ky": ky,
    }


# ------------------------------------------------------------------ CHỐT KỲ & KHÓA KỲ KẾ TOÁN
def chot_ky_bao_cao(conn, thang, nam, ma_nv, ghi_chu=None):
    existing = repo.get_period(conn, thang, nam)
    if existing is not None:
        raise BusinessError(f"Kỳ tháng {thang:02d}/{nam} hiện đã ở trạng thái “{existing['TrangThai']}”.")

    ton_rows, _ = bao_cao_ton_kho(conn, thang, nam)
    # Kiểm tra nối kỳ nếu kỳ trước đã chốt
    prev_m, prev_y = _thang_truoc(thang, nam)
    prev_ky = repo.get_period(conn, prev_m, prev_y)
    prev_map = {}
    if prev_ky is not None and prev_ky["TrangThai"] in ("Đã chốt", "Đã khóa"):
        prev_map = {r["MaSP"]: r["TonCuoi"] for r in repo.get_closed_inventory_rows(conn, prev_ky["MaKy"])}

    for r in ton_rows:
        if r["TonDau"] < -1e-9 or r["TonCuoi"] < -1e-9:
            raise BusinessError(f"Sản phẩm “{r['TenSP']}” có tồn kho âm trong kỳ, không thể chốt.")
        if r["MaSP"] in prev_map and abs(r["TonDau"] - prev_map[r["MaSP"]]) > 1e-6:
            raise BusinessError(
                f"Tồn đầu kỳ của “{r['TenSP']}” ({r['TonDau']:g}) không khớp tồn cuối kỳ trước ({prev_map[r['MaSP']]:g})."
            )

    dt = bao_cao_doanh_thu(conn, thang, nam)
    by_day = {}
    for d in dt["sale_days"]:
        by_day.setdefault(d["Ngay"], {"Ngay": d["Ngay"], "SoGDBan": 0, "DTBan": 0.0, "SoGDDV": 0, "DTDV": 0.0})
        by_day[d["Ngay"]].update(SoGDBan=d["SoGD"], DTBan=d["DoanhThu"])
    for d in dt["sv_days"]:
        by_day.setdefault(d["Ngay"], {"Ngay": d["Ngay"], "SoGDBan": 0, "DTBan": 0.0, "SoGDDV": 0, "DTDV": 0.0})
        by_day[d["Ngay"]].update(SoGDDV=d["SoGD"], DTDV=d["DoanhThu"])

    try:
        ma_ky = repo.insert_period_closed(
            conn, thang, nam, datetime.now().strftime("%Y-%m-%d %H:%M"), ma_nv, ghi_chu
        )
        for r in ton_rows:
            repo.insert_inventory_snapshot(
                conn, ma_ky, r["MaSP"], max(r["TonDau"], 0), r["MuaVao"], r["BanRa"], max(r["TonCuoi"], 0)
            )
        for d in sorted(by_day.values(), key=lambda x: x["Ngay"]):
            repo.insert_revenue_snapshot(
                conn, ma_ky, d["Ngay"], d["SoGDBan"], d["DTBan"], d["SoGDDV"], d["DTDV"]
            )
        conn.commit()
        return ma_ky
    except Exception:
        conn.rollback()
        raise


def khoa_ky_bao_cao(conn, thang, nam):
    ky = repo.get_period(conn, thang, nam)
    if ky is None:
        raise BusinessError(f"Cần chốt số liệu kỳ tháng {thang:02d}/{nam} trước khi khóa sổ.")
    if ky["TrangThai"] == "Đã khóa":
        raise BusinessError(f"Kỳ tháng {thang:02d}/{nam} đã được khóa trước đó.")
    repo.lock_period(conn, ky["MaKy"], datetime.now().strftime("%Y-%m-%d %H:%M"))
    conn.commit()
