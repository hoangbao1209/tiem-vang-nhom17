"""Tầng Nghiệp vụ (Business Layer): Xác thực người dùng, Phân quyền,
Thay đổi quy định (THAMSO), Nhật ký thay đổi, và Sao lưu / Phục hồi CSDL.
"""
import os
import sqlite3
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .. import db as db_mod
from .. import repositories as repo
from ..utils import BusinessError, to_float


# ------------------------------------------------------------------ XÁC THỰC & TÀI KHOẢN
def xac_thuc_dang_nhap(conn, username, password):
    user = repo.get_user_by_username(conn, (username or "").strip())
    if user is None or not check_password_hash(user["MatKhau"], password or ""):
        raise BusinessError("Tên đăng nhập hoặc mật khẩu không đúng.")
    if user["TinhTrang"] != "Đang làm việc":
        raise BusinessError("Tài khoản này đã ngừng hoạt động (Đã nghỉ việc).")
    return user


def lay_nguoi_dung(conn, ma_nv):
    return repo.get_user_by_id(conn, ma_nv)


def lay_danh_sach_nguoi_dung(conn):
    return repo.list_users(conn)


def tao_tai_khoan(conn, ten_dang_nhap, mat_khau, ten_nv, vai_tro, co_quyen_chuyen_nguoc=False):
    u = (ten_dang_nhap or "").strip()
    pw = mat_khau or ""
    ten = (ten_nv or "").strip()
    if not u or len(u) < 3:
        raise BusinessError("Tên đăng nhập phải có ít nhất 3 ký tự.")
    if len(pw) < 6:
        raise BusinessError("Mật khẩu phải có ít nhất 6 ký tự.")
    if not ten:
        raise BusinessError("Vui lòng nhập họ tên nhân viên.")
    if vai_tro not in ("NhanVien", "QuanLy"):
        raise BusinessError("Vai trò phải là Nhân viên hoặc Quản lý.")

    quyen_cn = 1 if (vai_tro == "QuanLy" or co_quyen_chuyen_nguoc) else 0
    try:
        ma_nv = repo.next_code(conn, "NGUOIDUNG", "MaNV", "NV", width=3)
        repo.insert_user(conn, ma_nv, ten, vai_tro, u, generate_password_hash(pw), quyen_cn)
        conn.commit()
        return ma_nv
    except sqlite3.IntegrityError:
        conn.rollback()
        raise BusinessError(f"Tên đăng nhập “{u}” đã tồn tại.")


def doi_mat_khau(conn, ma_nv, mat_khau_cu, mat_khau_moi, xac_nhan):
    user = repo.get_user_by_id(conn, ma_nv)
    if user is None:
        raise BusinessError("Không tìm thấy tài khoản.")
    if not check_password_hash(user["MatKhau"], mat_khau_cu or ""):
        raise BusinessError("Mật khẩu hiện tại không chính xác.")
    if not mat_khau_moi or len(mat_khau_moi) < 6:
        raise BusinessError("Mật khẩu mới phải có ít nhất 6 ký tự.")
    if mat_khau_moi != xac_nhan:
        raise BusinessError("Xác nhận mật khẩu mới không khớp.")
    repo.update_user_password(conn, ma_nv, generate_password_hash(mat_khau_moi))
    conn.commit()


def dao_quyen_chuyen_nguoc(conn, ma_nv):
    u = repo.get_user_by_id(conn, ma_nv)
    if u is None:
        raise BusinessError("Không tìm thấy nhân viên.")
    if u["VaiTro"] == "QuanLy":
        raise BusinessError("Quản lý luôn mặc định có quyền chuyển ngược trạng thái dịch vụ.")
    moi = 0 if u["CoQuyenChuyenNguoc"] else 1
    repo.update_user_revert_perm(conn, ma_nv, moi)
    conn.commit()
    return u["TenNV"], bool(moi)


def doi_trang_thai_tai_khoan(conn, ma_nv, current_ma_nv):
    if ma_nv == current_ma_nv:
        raise BusinessError("Không thể tự khóa tài khoản đang đăng nhập.")
    u = repo.get_user_by_id(conn, ma_nv)
    if u is None:
        raise BusinessError("Không tìm thấy tài khoản.")
    moi = "Đã nghỉ việc" if u["TinhTrang"] == "Đang làm việc" else "Đang làm việc"
    repo.update_user_status(conn, ma_nv, moi)
    conn.commit()
    return u["TenNV"], moi


def xoa_tai_khoan(conn, ma_nv, current_ma_nv):
    if ma_nv == current_ma_nv:
        raise BusinessError("Không thể tự xóa tài khoản đang đăng nhập.")
    users = {u["MaNV"]: u for u in repo.list_users(conn)}
    u = users.get(ma_nv)
    if u is None:
        raise BusinessError("Không tìm thấy tài khoản.")
    if u["DaPhatSinh"]:
        raise BusinessError(
            f"Tài khoản “{u['TenNV']}” đã phát sinh chứng từ/nhật ký nên không thể xóa vật lý. "
            "Hãy chuyển sang trạng thái “Đã nghỉ việc”."
        )
    repo.delete_user(conn, ma_nv)
    conn.commit()
    return u["TenNV"]


# ------------------------------------------------------------------ THAM SỐ & NHẬT KÝ QUY ĐỊNH
def lay_tham_so(conn):
    return repo.get_tham_so(conn)


def cap_nhat_ti_le_tra_truoc(conn, phan_tram_pct, ma_nv, ghi_chu=None):
    pt = to_float(phan_tram_pct)
    if pt is None or not (0 <= pt <= 100):
        raise BusinessError("Tỷ lệ trả trước tối thiểu phải nằm trong khoảng từ 0% đến 100%.")
    moi_dec = round(pt / 100.0, 4)
    cu_dec = float(repo.get_tham_so(conn)["TiLeTraTruoc"])
    if abs(moi_dec - cu_dec) < 1e-6:
        return False
    repo.update_ti_le_tra_truoc(conn, moi_dec)
    repo.insert_rule_log(
        conn,
        "Tỷ lệ trả trước",
        "THAMSO:1",
        f"{round(cu_dec * 100, 2):g}%",
        f"{pt:g}%",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ma_nv,
        (ghi_chu or "").strip() or "Cập nhật tỷ lệ trả trước tối thiểu (chỉ áp dụng cho phiếu dịch vụ mới)",
    )
    conn.commit()
    return True


def lay_nhat_ky_quy_dinh(conn, limit=30):
    return repo.list_rule_logs(conn, limit=limit)


# ------------------------------------------------------------------ SAO LƯU & PHỤC HỒI (YCHT07)
def tao_ban_sao_luu():
    return db_mod.backup_database(label="thu_cong")


def lay_danh_sach_sao_luu():
    return db_mod.list_backups()


def phuc_hoi_tu_file_tren_server(backup_folder, filename):
    safe = os.path.basename(filename or "")
    if not safe.endswith(".db"):
        raise BusinessError("Tên tệp sao lưu không hợp lệ.")
    path = os.path.join(backup_folder, safe)
    if not os.path.isfile(path):
        raise BusinessError("Không tìm thấy tệp sao lưu được chọn.")
    try:
        db_mod.restore_database(path)
    except ValueError as e:
        raise BusinessError(str(e))


def phuc_hoi_tu_file_upload(file_storage, backup_folder):
    if not file_storage or not file_storage.filename:
        raise BusinessError("Vui lòng chọn tệp sao lưu (.db) để phục hồi.")
    if not file_storage.filename.lower().endswith(".db"):
        raise BusinessError("Chỉ chấp nhận tệp sao lưu định dạng .db.")
    os.makedirs(backup_folder, exist_ok=True)
    tmp_path = os.path.join(backup_folder, f"_upload_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    file_storage.save(tmp_path)
    try:
        db_mod.restore_database(tmp_path)
    except ValueError as e:
        raise BusinessError(str(e))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
