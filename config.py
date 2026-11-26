"""Cấu hình ứng dụng quản lý & bán hàng cửa hàng vàng bạc đá quý (Nhóm 17)."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "nhom17-se104-kim-ngan-jewelry-secret-key")
    DATABASE = os.path.join(BASE_DIR, "instance", "tiemvang.db")
    BACKUP_FOLDER = os.path.join(BASE_DIR, "instance", "backups")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # tối đa 8MB (ảnh hoặc file sao lưu .db)
    ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

    # Thông tin thương hiệu cửa hàng (hiển thị trên giao diện & bản in chứng từ)
    STORE_INFO = {
        "TenCuaHang": "Kim Ngân Jewelry",
        "KhauHieu": "Tinh Hoa Kim Hoàn Việt — Chuẩn Tuổi Vàng & Kiểm Định Uy Tín",
        "DiaChi": "123 Lê Lợi, Phường Bến Thành, Quận 1, TP. Hồ Chí Minh",
        "SoDienThoai": "0909 123 456",
        "Email": "lienhe@kimnganjewelry.vn",
        "GioMoCua": "08:30 – 20:30 (Tất cả các ngày trong tuần)",
        "NguongCanhBaoTon": 2,
    }
