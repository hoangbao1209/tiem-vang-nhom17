"""Application Factory – Khởi tạo ứng dụng Flask theo kiến trúc 3 lớp."""
import os

from flask import Flask, render_template

from config import Config
from . import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    os.makedirs(app.config["BACKUP_FOLDER"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    from .utils import register_template_helpers
    register_template_helpers(app)

    from .auth import bp as auth_bp
    from .blueprints.shop import bp as shop_bp
    from .blueprints.admin import bp as admin_bp

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template(
            "error.html",
            code=403,
            message="Bạn không có quyền thực hiện chức năng này. Vui lòng liên hệ Quản lý cửa hàng.",
        ), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template(
            "error.html",
            code=404,
            message="Không tìm thấy trang hoặc chứng từ bạn yêu cầu.",
        ), 404

    return app
