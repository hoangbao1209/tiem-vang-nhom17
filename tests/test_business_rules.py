"""Bộ kiểm thử tự động các quy tắc nghiệp vụ & chất lượng phần mềm (CL01, CL04, QĐ1–QĐ15, YCHT05–YCHT08).
Chạy bằng lệnh: python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from app import create_app
from app.db import REQUIRED_TABLES, get_db, init_db
from app.services import catalog as cat_svc
from app.services import inventory as inv_svc
from app.services import reports as rep_svc
from app.services import settings as set_svc
from app.services import vouchers as vou_svc
from app.utils import BusinessError


class JewelryBusinessRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

        class TestConfig(Config):
            TESTING = True
            DATABASE = os.path.join(self.tmpdir.name, "test.db")
            BACKUP_FOLDER = os.path.join(self.tmpdir.name, "backups")
            UPLOAD_FOLDER = os.path.join(self.tmpdir.name, "uploads")

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.db = get_db()
        self.today = date.today().isoformat()

    def tearDown(self):
        self.ctx.pop()
        self.tmpdir.cleanup()

    def test_01_schema_21_tables_and_3tier_separation(self):
        """Kiểm tra đủ 21 bảng chuẩn và tầng Presentation không chứa lệnh SQL trực tiếp."""
        tables = {
            r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        self.assertTrue(REQUIRED_TABLES.issubset(tables))

        base_app = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app")
        for rel in ("auth.py", os.path.join("blueprints", "shop.py"), os.path.join("blueprints", "admin.py")):
            with open(os.path.join(base_app, rel), encoding="utf-8") as f:
                src = f.read()
            self.assertNotIn(".execute(", src, f"Phát hiện SQL trực tiếp trong tầng Presentation: {rel}")

    def test_02_product_supplier_service_delete_protection(self):
        """Kiểm tra quy tắc không xóa vật lý đối tượng đã phát sinh giao dịch."""
        # Sản phẩm đã có trong dữ liệu mẫu -> không được xóa vật lý
        with self.assertRaises(BusinessError):
            cat_svc.xoa_san_pham(self.db, "SP001")

        # Sản phẩm mới chưa phát sinh giao dịch -> xóa vật lý được
        ma_moi, _ = cat_svc.luu_san_pham(self.db, None, {
            "TenSP": "Nhẫn thử nghiệm", "MaLoaiSP": "LSP02", "DonGiaMua": "1000000", "TinhTrang": "Đang kinh doanh"
        })
        cat_svc.xoa_san_pham(self.db, ma_moi)
        self.assertIsNone(cat_svc.lay_san_pham(self.db, ma_moi))

        # Nhà cung cấp & Dịch vụ đã phát sinh -> chặn xóa
        with self.assertRaises(BusinessError):
            cat_svc.xoa_nha_cung_cap(self.db, "NCC001")
        with self.assertRaises(BusinessError):
            cat_svc.xoa_dich_vu(self.db, "DV001")

    def test_03_purchase_sale_pricing_and_rule_history(self):
        """Kiểm tra mua cộng tồn, bán trừ tồn, tính giá bán & tiền thừa, đổi % lợi nhuận không sửa phiếu cũ."""
        sp_truoc = cat_svc.lay_san_pham(self.db, "SP004")
        ton_truoc = sp_truoc["SoLuongTon"]

        vou_svc.tao_phieu_mua(
            self.db, "NCC001", self.today,
            [{"MaSP": "SP004", "SoLuong": 2, "DonGia": 7000000}], ma_nv="NV001",
        )
        sp_sau_mua = cat_svc.lay_san_pham(self.db, "SP004")
        self.assertEqual(sp_sau_mua["SoLuongTon"], ton_truoc + 2)
        self.assertEqual(sp_sau_mua["DonGiaMua"], 7000000)
        self.assertEqual(sp_sau_mua["DonGiaBan"], round(7000000 * 1.15))

        # Tiền khách đưa thiếu -> báo lỗi
        with self.assertRaises(BusinessError):
            vou_svc.tao_phieu_ban(
                self.db, {"ten": "Khách A"}, [{"MaSP": "SP004", "SoLuong": 1}],
                self.today, ma_nv="NV002", pttt="Tiền mặt", so_tien_nhan=1000000,
            )

        # Bán hợp lệ tiền mặt -> tính tiền thừa & trừ tồn
        so_pb = vou_svc.tao_phieu_ban(
            self.db, {"ten": "Khách A"}, [{"MaSP": "SP004", "SoLuong": 1}],
            self.today, ma_nv="NV002", pttt="Tiền mặt", so_tien_nhan=9000000,
        )
        pb, lines = vou_svc.lay_phieu_ban(self.db, so_pb)
        self.assertEqual(pb["TongTien"], 8050000)
        self.assertEqual(pb["TienThua"], 950000)
        self.assertEqual(cat_svc.lay_san_pham(self.db, "SP004")["SoLuongTon"], ton_truoc + 1)

        # Đổi % lợi nhuận LSP02 lên 25% -> phiếu cũ giữ nguyên DonGiaBan = 8,050,000 & ghi nhật ký
        cat_svc.luu_loai_san_pham(self.db, "LSP02", "Nhẫn trang sức", "DVT02", 25, "NV001")
        _, lines_after = vou_svc.lay_phieu_ban(self.db, so_pb)
        self.assertEqual(lines_after[0]["DonGiaBan"], 8050000)
        self.assertEqual(cat_svc.lay_san_pham(self.db, "SP004")["DonGiaBan"], round(7000000 * 1.25))

    def test_04_service_voucher_prepayment_status_and_revert_permission(self):
        """Kiểm tra tỷ lệ trả trước, thu tiền nhiều đợt, tự tính Hoàn thành và quyền chuyển ngược."""
        # Trả trước < 50% -> từ chối
        with self.assertRaises(BusinessError):
            vou_svc.tao_phieu_dich_vu(
                self.db, {"ten": "Chị Lan", "sdt": "0909000111"},
                [{"MaDichVu": "DV003", "SoLuong": 1, "ChiPhiRieng": 0, "TraTruoc": 40000, "NgayGiaoDuKien": self.today}],
                self.today, ma_nv="NV002",
            )

        # Lập hợp lệ -> tự tạo THUTIENDICHVU
        so_dv = vou_svc.tao_phieu_dich_vu(
            self.db, {"ten": "Chị Lan", "sdt": "0909000111"},
            [{"MaDichVu": "DV003", "SoLuong": 1, "ChiPhiRieng": 20000, "TraTruoc": 60000, "NgayGiaoDuKien": self.today}],
            self.today, ma_nv="NV002",
        )
        p, lines, receipts, _ = vou_svc.lay_phieu_dich_vu(self.db, so_dv)
        self.assertEqual(p["TongTien"], 120000)
        self.assertEqual(p["DaThu"], 60000)
        self.assertEqual(p["TinhTrang"], "Chưa hoàn thành")
        self.assertEqual(len(receipts), 1)

        # Bàn giao -> phiếu tự chuyển Hoàn thành
        ma_ct = lines[0]["MaChiTiet"]
        vou_svc.cap_nhat_tinh_trang_dich_vu(self.db, ma_ct, "Đã giao", ma_nv="NV002")
        p2, _, _, _ = vou_svc.lay_phieu_dich_vu(self.db, so_dv)
        self.assertEqual(p2["TinhTrang"], "Hoàn thành")

        # Chuyển ngược không có quyền -> lỗi
        with self.assertRaises(BusinessError):
            vou_svc.cap_nhat_tinh_trang_dich_vu(self.db, ma_ct, "Chưa giao", ma_nv="NV002",
                                                co_quyen_chuyen_nguoc=False, ly_do="Sửa lại")
        # Chuyển ngược có quyền nhưng thiếu lý do -> lỗi
        with self.assertRaises(BusinessError):
            vou_svc.cap_nhat_tinh_trang_dich_vu(self.db, ma_ct, "Chưa giao", ma_nv="NV001",
                                                co_quyen_chuyen_nguoc=True, ly_do="")
        # Chuyển ngược có quyền + lý do -> thành công & ghi lịch sử
        vou_svc.cap_nhat_tinh_trang_dich_vu(self.db, ma_ct, "Chưa giao", ma_nv="NV001",
                                            co_quyen_chuyen_nguoc=True, ly_do="Khách yêu cầu khắc lại nét sâu hơn")
        p3, _, _, logs = vou_svc.lay_phieu_dich_vu(self.db, so_dv)
        self.assertEqual(p3["TinhTrang"], "Chưa hoàn thành")
        self.assertEqual(len(logs), 2)

    def test_05_stocktake_never_mutates_inventory_and_requires_independent_manager(self):
        """Kiểm tra kiểm kê bắt buộc lý do khi lệch, người xác nhận khác người kiểm kê, không đổi tồn kho."""
        ton_ban_dau = cat_svc.lay_san_pham(self.db, "SP001")["SoLuongTon"]

        # Chênh lệch mà không có lý do -> lỗi
        with self.assertRaises(BusinessError):
            inv_svc.tao_phieu_kiem_ke(
                self.db, self.today,
                [{"MaSP": "SP001", "TonThucTe": ton_ban_dau - 1, "LyDoChenhLech": ""}],
                ma_nv="NV003",
            )

        so_kk = inv_svc.tao_phieu_kiem_ke(
            self.db, self.today,
            [{"MaSP": "SP001", "TonThucTe": ton_ban_dau - 1, "LyDoChenhLech": "1 chỉ đang trưng bày ở tủ phụ"}],
            ma_nv="NV003",
        )
        # Tự xác nhận -> lỗi
        with self.assertRaises(BusinessError):
            inv_svc.xac_nhan_kiem_ke(self.db, so_kk, "NV003", is_manager=True)

        # Quản lý khác xác nhận -> thành công và tồn hệ thống KHÔNG thay đổi
        inv_svc.xac_nhan_kiem_ke(self.db, so_kk, "NV001", is_manager=True)
        self.assertEqual(cat_svc.lay_san_pham(self.db, "SP001")["SoLuongTon"], ton_ban_dau)

    def test_06_period_close_lock_and_backup_restore(self):
        """Kiểm tra chốt kỳ, khóa kỳ chặn lập phiếu cũ, và sao lưu/phục hồi CSDL (YCHT07)."""
        t = date.today()
        # Sao lưu trước khi thay đổi
        bak_name, _ = set_svc.tao_ban_sao_luu()

        # Chốt kỳ & Khóa kỳ tháng hiện tại
        rep_svc.chot_ky_bao_cao(self.db, t.month, t.year, "NV001")
        rep_svc.khoa_ky_bao_cao(self.db, t.month, t.year)

        # Sau khi khóa kỳ -> không được lập phiếu bán mới trong tháng đó
        with self.assertRaises(BusinessError):
            vou_svc.tao_phieu_ban(
                self.db, {"ten": "Khách B"}, [{"MaSP": "SP001", "SoLuong": 1}],
                self.today, ma_nv="NV002", pttt="Chuyển khoản",
            )

        # Phục hồi về bản sao lưu trước khi khóa kỳ -> kỳ mở lại bình thường
        set_svc.phuc_hoi_tu_file_tren_server(self.app.config["BACKUP_FOLDER"], bak_name)
        self.db = get_db()
        _, ky = rep_svc.bao_cao_ton_kho(self.db, t.month, t.year)
        self.assertIsNone(ky)


if __name__ == "__main__":
    unittest.main()
