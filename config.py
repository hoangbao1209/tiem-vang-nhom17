import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "nhom17-dev-secret-hay-doi-khi-trien-khai")
    DATABASE = os.path.join(BASE_DIR, "instance", "tiemvang.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # ảnh tối đa 4MB
    ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
