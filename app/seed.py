"""Dữ liệu mẫu chân thực cho hệ thống 21 bảng Quản lý Vàng Bạc Đá Quý (Nhóm 17)."""
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from .services.inventory import tao_phieu_kiem_ke, xac_nhan_kiem_ke
from .services.vouchers import (
    NGUON_ONLINE,
    TT_CHO,
    cap_nhat_tinh_trang_dich_vu,
    tao_phieu_ban,
    tao_phieu_dich_vu,
    tao_phieu_mua,
    thu_tien_dich_vu,
)


def _ngay(thang_truoc, ngay):
    t = date.today()
    y, m = t.year, t.month - thang_truoc
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, min(ngay, 28)).isoformat()


def seed_data(conn):
    # 1. THAMSO (duy nhất 1 dòng MaThamSo = 1, TiLeTraTruoc = 0.5000 = 50%)
    conn.execute("INSERT INTO THAMSO(MaThamSo, TiLeTraTruoc) VALUES (1, 0.5000)")

    # 2. NGUOIDUNG (VaiTro: QuanLy / NhanVien)
    conn.executemany(
        "INSERT INTO NGUOIDUNG(MaNV, TenNV, VaiTro, TenDangNhap, MatKhau, CoQuyenChuyenNguoc, TinhTrang) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("NV001", "Nguyễn Minh Quân", "QuanLy", "admin", generate_password_hash("admin123"), 1, "Đang làm việc"),
            ("NV002", "Trần Thảo Vy", "NhanVien", "nhanvien", generate_password_hash("nhanvien123"), 0, "Đang làm việc"),
            ("NV003", "Lê Quốc Huy", "NhanVien", "kho", generate_password_hash("kho123"), 1, "Đang làm việc"),
        ],
    )

    # 3. DONVITINH
    conn.executemany(
        "INSERT INTO DONVITINH(MaDVT, TenDVT) VALUES (?, ?)",
        [
            ("DVT01", "Chỉ"),
            ("DVT02", "Chiếc"),
            ("DVT03", "Cặp"),
            ("DVT04", "Viên"),
            ("DVT05", "Lượng"),
        ],
    )

    # 4. LOAISANPHAM (PhanTramLoiNhuan dạng thập phân: 0.02 = 2%, 0.15 = 15%...)
    conn.executemany(
        "INSERT INTO LOAISANPHAM(MaLoaiSP, TenLoaiSP, MaDVT, PhanTramLoiNhuan) VALUES (?, ?, ?, ?)",
        [
            ("LSP01", "Vàng miếng & Nhẫn tròn", "DVT01", 0.02),
            ("LSP02", "Nhẫn trang sức", "DVT02", 0.15),
            ("LSP03", "Dây chuyền", "DVT02", 0.18),
            ("LSP04", "Bông tai", "DVT03", 0.22),
            ("LSP05", "Lắc & Vòng tay", "DVT02", 0.20),
            ("LSP06", "Kim cương & Đá quý", "DVT04", 0.28),
            ("LSP07", "Trang sức bạc", "DVT02", 0.35),
        ],
    )

    # 5. SANPHAM (19 sản phẩm trang sức phong phú kèm ảnh chụp studio thực tế)
    img = "img/products/"
    products = [
        ("SP001", "Vàng miếng SJC 999.9 (1 chỉ)", "LSP01", "Vàng 999.9", "24K (99.99%)", "1 chỉ (3.75g)",
         "Thu đổi theo giá niêm yết SJC toàn quốc, đầy đủ số seri kiểm định",
         "Vàng miếng SJC 999.9 ép vỉ nguyên seal kèm số seri chính hãng, độ tinh khiết tuyệt đối, lý tưởng để tích trữ tài sản và làm quà biếu trang trọng.",
         img + "gold-bar.jpg"),
        ("SP002", "Nhẫn tròn trơn 999.9 Kim Ngân (1 chỉ)", "LSP01", "Vàng 999.9", "24K (99.99%)", "1 chỉ (3.75g)",
         "Thu đổi linh hoạt, kiểm tra tuổi vàng bằng máy quang phổ miễn phí",
         "Nhẫn tròn trơn ép vỉ chuẩn tuổi vàng 99.99%, bề mặt xử lý bóng gương tinh xảo, phù hợp tích lũy hoặc làm sính lễ cưới hỏi truyền thống.",
         img + "ring-plain-gold.jpg"),
        ("SP003", "Vàng miếng SJC 999.9 (1 lượng)", "LSP01", "Vàng 999.9", "24K (99.99%)", "1 lượng (37.5g)",
         "Thu đổi minh bạch theo giá niêm yết SJC mỗi ngày",
         "Vàng miếng SJC trọng lượng 1 lượng (10 chỉ) nguyên bản ép vỉ chính hãng, tính thanh khoản cao và giá trị bảo toàn bền vững theo thời gian.",
         img + "gold-bar.jpg"),
        ("SP004", "Nhẫn Kim Tiền vàng 18K tài lộc", "LSP02", "Vàng Tây 18K", "18K (75.0%)", "1.2 chỉ (~4.5g)",
         "Làm sạch siêu âm & đánh bóng miễn phí trọn đời",
         "Thiết kế chuỗi đồng tiền nối liền biểu trưng cho tài lộc sung túc, chế tác sắc nét trên nền vàng 18K sáng bóng, dễ dàng đeo hằng ngày.",
         img + "ring-gold.jpg"),
        ("SP005", "Nhẫn cưới vàng trắng đính kim cương tấm", "LSP02", "Vàng trắng 14K & Kim cương", "14K (58.5%)", "1.4 chỉ (~5.25g)",
         "Bảo hành gắn đá, làm mới & chỉnh ni tay trọn đời",
         "Kiểu dáng tinh giản sang trọng chế tác từ vàng trắng 14K, đính 12 viên kim cương tấm nước E-F cắt giác chuẩn mực, biểu tượng của tình yêu bền chặt.",
         img + "ring-solitaire.jpg"),
        ("SP006", "Nhẫn nam vàng 24K mặt đá Ruby thiên nhiên", "LSP02", "Vàng 24K & Đá Ruby", "24K (99.9%)", "3.2 chỉ (~12g)",
         "Kèm chứng thư giám định đá quý thiên nhiên & bảo hành trọn đời",
         "Phom nhẫn bản vuông uy nghi tôn lên bản lĩnh phái mạnh, nổi bật với viên Ruby thiên nhiên sắc đỏ huyết bồ câu rực rỡ và đường chạm khắc tinh công.",
         img + "ring-ruby.jpg"),
        ("SP007", "Nhẫn nữ Solitaire vàng trắng đính Moissanite", "LSP02", "Vàng trắng 18K & Moissanite", "18K (75.0%)", "0.95 chỉ (~3.56g)",
         "Bảo hành chấu giữ đá & làm sáng miễn phí trọn đời",
         "Ổ nhẫn 6 chấu thanh thoát nâng đỡ viên chủ Moissanite 6.3 ly chuẩn giác cắt Hearts & Arrows tạo hiệu ứng lửa tán sắc lấp lánh mọi góc nhìn.",
         img + "ring-diamond.jpg"),
        ("SP008", "Dây chuyền vàng 18K mặt trái tim đá CZ", "LSP03", "Vàng 18K & Đá CZ", "18K (75.0%)", "1.5 chỉ (~5.62g)",
         "Bảo hành hàn nối dây & đánh bóng trọn đời",
         "Sợi dây mảnh 42cm nhẹ nhàng ôm lấy xương quai xanh kết hợp mặt trái tim đính đá CZ cao cấp, món quà ngọt ngào và thanh lịch cho phái đẹp.",
         img + "necklace-gold.jpg"),
        ("SP009", "Dây chuyền vàng Ý 24K mắt xích thanh lịch", "LSP03", "Vàng Ý 24K", "24K (99.9%)", "3.0 chỉ (~11.25g)",
         "Làm sạch siêu âm & kiểm tra khóa gài miễn phí trọn đời",
         "Công nghệ dập cắt kim cương của Ý tạo độ bắt sáng vượt trội, từng mắt xích đan khít chắc chắn và êm ái khi đeo dự tiệc hoặc trang phục công sở.",
         img + "gold-display.jpg"),
        ("SP010", "Dây chuyền ngọc trai Akoya khóa vàng 18K", "LSP03", "Ngọc trai Akoya & Vàng 18K", "18K (75.0%)", "Chuỗi 45cm",
         "Bảo hành dây xâu lụa & đánh bóng ngọc trai định kỳ",
         "Chuỗi ngọc trai biển Akoya tuyển chọn đồng đều kích thước 7.5–8mm ánh xà cừ hồng dịu, hoàn thiện bằng khóa gài vàng 18K sang trọng.",
         img + "earring-pearl.jpg"),
        ("SP011", "Bông tai vàng trắng ngọc trai nước ngọt", "LSP04", "Vàng trắng 10K & Ngọc trai", "10K (41.6%)", "0.8 chỉ / cặp",
         "Bảo hành làm sạch & thay chốt khóa miễn phí trọn đời",
         "Sự giao hòa tinh tế giữa sắc trắng ánh kim hiện đại và viên ngọc trai tròn mượt tự nhiên, mang lại vẻ đẹp dịu dàng và quý phái cho gương mặt.",
         img + "earring-pearl.jpg"),
        ("SP012", "Bông tai vàng 18K giọt nước đính đá CZ", "LSP04", "Vàng 18K & Đá CZ", "18K (75.0%)", "0.9 chỉ / cặp",
         "Bảo hành chấu đá & làm sáng miễn phí trọn đời",
         "Thiết kế giọt nước uyển chuyển bắt sáng rực rỡ theo từng cử động, chế tác từ vàng 18K cao cấp kết hợp đá CZ giác cắt tinh xảo.",
         img + "earring-gold.jpg"),
        ("SP013", "Lắc tay vàng 18K hoa mai năm cánh", "LSP05", "Vàng 18K", "18K (75.0%)", "1.8 chỉ (~6.75g)",
         "Bảo hành hàn nối & đánh bóng miễn phí trọn đời",
         "Chuỗi charm hoa mai 5 cánh đan xen bi vàng phay sáng tạo điểm nhấn nữ tính, mang ý nghĩa cát tường và khởi đầu may mắn.",
         img + "bracelet-gold.jpg"),
        ("SP014", "Vòng tay vàng ta 24K chạm rồng thủ công", "LSP05", "Vàng 24K nguyên chất", "24K (99.9%)", "5.0 chỉ (~18.75g)",
         "Chế tác thủ công, đầy đủ giấy kiểm định tuổi vàng",
         "Vòng tay bản tròn chạm khắc hình tượng rồng uy nghi bởi nghệ nhân kim hoàn lành nghề, biểu trưng cho quyền uy, thịnh vượng và đẳng cấp.",
         img + "gold-display.jpg"),
        ("SP015", "Kiềng tay cưới vàng 24K long phụng sum vầy", "LSP05", "Vàng 24K", "24K (99.9%)", "4.0 chỉ (~15g)",
         "Thu đổi chuẩn tuổi vàng, làm mới miễn phí trọn đời",
         "Họa tiết long phụng sum vầy dập nổi tinh xảo trên nền vàng 24K rực rỡ, lựa chọn hoàn hảo làm của hồi môn trang trọng trong lễ cưới.",
         img + "bracelet-box.jpg"),
        ("SP016", "Kim cương thiên nhiên 5.4 ly kiểm định GIA", "LSP06", "Kim cương thiên nhiên", "Nước D – VS1", "0.62 carat",
         "Đầy đủ chứng thư kiểm định quốc tế GIA khắc laser cạnh viên",
         "Viên kim cương tự nhiên 5.4 ly nước D trắng tinh khiết, độ sạch VS1, giác cắt 3EX (Excellent) mang lại độ lấp lánh và giá trị sưu tầm đỉnh cao.",
         img + "hero-showcase.jpg"),
        ("SP017", "Đá Sapphire xanh hoàng gia 1.0 carat", "LSP06", "Sapphire thiên nhiên", "Royal Blue", "1.0 carat",
         "Kèm chứng thư giám định đá quý uy tín trong nước",
         "Sapphire thiên nhiên sắc xanh lam hoàng gia sâu thẳm chưa qua xử lý nhiệt, giác cắt oval cân đối, lý tưởng để lên ổ nhẫn hoặc mặt dây thiết kế riêng.",
         img + "gem-sapphire.jpg"),
        ("SP018", "Nhẫn bạc Ý 925 xi bạch kim tối giản", "LSP07", "Bạc Ý 925", "S925 (92.5%)", "3.8g",
         "Làm sáng bạc miễn phí trọn đời tại cửa hàng",
         "Bạc Ý S925 phủ lớp Rhodium cao cấp chống oxy hóa giữ độ bóng trắng như bạch kim, kiểu dáng tối giản thanh lịch phù hợp cả nam và nữ.",
         img + "jewelry-luxury.jpg"),
        ("SP019", "Dây chuyền bạc 925 mặt tròn Halo đá trắng", "LSP07", "Bạc Ý 925 & Đá CZ", "S925 (92.5%)", "4.5g",
         "Bảo hành đánh bóng & thay đá tấm miễn phí",
         "Phong cách trẻ trung tinh tế với mặt tròn Halo viền đá trắng lấp lánh, dễ phối cùng nhiều trang phục thường ngày hoặc làm quà sinh nhật.",
         img + "silver-set.jpg"),
    ]
    conn.executemany(
        "INSERT INTO SANPHAM(MaSP, TenSP, MaLoaiSP, ChatLieu, TuoiVang, TrongLuong, BaoHanh, MoTa, HinhAnh) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        products,
    )

    # 6. NHACUNGCAP
    conn.executemany(
        "INSERT INTO NHACUNGCAP(MaNCC, TenNCC, DiaChi, SoDienThoai, TinhTrang) VALUES (?, ?, ?, ?, ?)",
        [
            ("NCC001", "Công ty Vàng bạc Đá quý Kim Phát", "12 Trần Hưng Đạo, Quận 5, TP.HCM", "02838551234", "Đang hợp tác"),
            ("NCC002", "Xưởng chế tác Trang sức Ngọc Minh", "45 Lê Văn Sỹ, Quận 3, TP.HCM", "0903456789", "Đang hợp tác"),
            ("NCC003", "Công ty Giám định & Đá quý Phương Nam", "88 Nguyễn Trãi, Quận 1, TP.HCM", "02839205678", "Đang hợp tác"),
            ("NCC004", "Cơ sở Kim hoàn Gia Hưng", "210 Cách Mạng Tháng 8, Quận 10, TP.HCM", "0918223344", "Đang hợp tác"),
        ],
    )

    # 7. DICHVU
    conn.executemany(
        "INSERT INTO DICHVU(MaDichVu, TenDichVu, DonGiaCoBan, TinhTrang) VALUES (?, ?, ?, ?)",
        [
            ("DV001", "Đánh bóng & làm mới trang sức", 50000, "Đang hoạt động"),
            ("DV002", "Làm sạch bằng sóng siêu âm", 30000, "Đang hoạt động"),
            ("DV003", "Khắc chữ laser theo yêu cầu", 100000, "Đang hoạt động"),
            ("DV004", "Gắn / thay đá trang sức", 150000, "Đang hoạt động"),
            ("DV005", "Sửa, hàn, chỉnh ni tay nhẫn", 120000, "Đang hoạt động"),
            ("DV006", "Xi mạ vàng 18K / bạch kim Rhodium", 250000, "Đang hoạt động"),
            ("DV007", "Cân thử & đo tuổi vàng quang phổ", 80000, "Đang hoạt động"),
        ],
    )
    conn.commit()

    # 8. Phiếu mua hàng mẫu (tự động cộng tồn & cập nhật DonGiaMua)
    def mh(ma, sl, gia):
        return {"MaSP": ma, "SoLuong": sl, "DonGia": gia}

    tao_phieu_mua(conn, "NCC001", _ngay(2, 5), [
        mh("SP001", 20, 8500000), mh("SP002", 15, 8450000), mh("SP003", 4, 84500000),
        mh("SP004", 8, 6200000), mh("SP008", 6, 9600000), mh("SP009", 4, 24000000),
        mh("SP013", 5, 11500000), mh("SP014", 2, 42000000), mh("SP015", 3, 34000000),
    ], ghi_chu="Lô nhập vàng miếng & trang sức định kỳ", ma_nv="NV001")

    tao_phieu_mua(conn, "NCC002", _ngay(2, 12), [
        mh("SP005", 5, 18500000), mh("SP006", 4, 25800000), mh("SP007", 6, 12400000),
        mh("SP010", 5, 14500000), mh("SP011", 10, 3800000), mh("SP012", 10, 4200000),
        mh("SP018", 30, 450000), mh("SP019", 20, 680000),
    ], ghi_chu="Lô nhập trang sức chế tác & bạc Ý", ma_nv="NV003")

    tao_phieu_mua(conn, "NCC003", _ngay(1, 3), [
        mh("SP016", 3, 38000000), mh("SP017", 3, 21000000),
    ], ghi_chu="Lô kim cương GIA & Sapphire thiên nhiên", ma_nv="NV001")

    tao_phieu_mua(conn, "NCC001", _ngay(1, 20), [
        mh("SP001", 10, 8600000), mh("SP004", 5, 6300000),
    ], ghi_chu="Bổ sung hàng bán chạy", ma_nv="NV003")

    # 9. Phiếu bán hàng mẫu (tại quầy + đơn đặt giữ Online)
    tao_phieu_ban(
        conn, {"ten": "Nguyễn Văn An", "sdt": "0901111222", "dia_chi": "Quận 7, TP.HCM"},
        [{"MaSP": "SP001", "SoLuong": 3}, {"MaSP": "SP004", "SoLuong": 1}],
        _ngay(2, 18), ma_nv="NV002", pttt="Tiền mặt", so_tien_nhan=35000000,
    )
    tao_phieu_ban(
        conn, {"ten": "Trần Thị Bình", "sdt": "0912333444", "dia_chi": "TP. Thủ Đức, TP.HCM"},
        [{"MaSP": "SP008", "SoLuong": 1}, {"MaSP": "SP011", "SoLuong": 1}],
        _ngay(1, 8), ma_nv="NV002", pttt="Chuyển khoản",
    )
    tao_phieu_ban(
        conn, {"ten": "Lê Hoàng Cường", "sdt": "0987555666", "dia_chi": "Quận Bình Thạnh, TP.HCM"},
        [{"MaSP": "SP005", "SoLuong": 1}, {"MaSP": "SP001", "SoLuong": 2}],
        _ngay(1, 25), ma_nv="NV002", pttt="Tiền mặt", so_tien_nhan=40000000,
    )
    tao_phieu_ban(
        conn, {"ten": "Võ Thanh Hà", "sdt": "0909888777", "dia_chi": "Quận 3, TP.HCM"},
        [{"MaSP": "SP013", "SoLuong": 1}, {"MaSP": "SP019", "SoLuong": 1}],
        _ngay(0, min(date.today().day, 5)), ma_nv="NV002", pttt="Chuyển khoản",
    )
    tao_phieu_ban(
        conn, {"ten": "Phạm Minh Đức", "sdt": "0938777888", "dia_chi": "Quận Gò Vấp, TP.HCM"},
        [{"MaSP": "SP018", "SoLuong": 2}],
        f"{date.today().isoformat()} 09:30",
        nguon=NGUON_ONLINE, trang_thai=TT_CHO, ghi_chu="Giao giờ hành chính hoặc nhận tại quầy",
        pttt="Chuyển khoản",
    )

    # 10. Phiếu dịch vụ + Thu tiền dịch vụ + Lịch sử tình trạng mẫu
    so_dv1 = tao_phieu_dich_vu(
        conn, {"ten": "Trần Thị Bình", "sdt": "0912333444"},
        [
            {"MaDichVu": "DV001", "SoLuong": 2, "ChiPhiRieng": 0, "TraTruoc": 50000, "NgayGiaoDuKien": _ngay(1, 12)},
            {"MaDichVu": "DV003", "SoLuong": 1, "ChiPhiRieng": 50000, "TraTruoc": 100000, "NgayGiaoDuKien": _ngay(1, 15)},
        ],
        _ngay(1, 10), ma_nv="NV002", hinh_thuc="Tiền mặt",
    )
    thu_tien_dich_vu(
        conn, so_dv1, 100000, hinh_thuc="Tiền mặt", ma_nv="NV002",
        ghi_chu="Khách thanh toán phần còn lại khi nhận trang sức", ngay_thu=_ngay(1, 15),
    )
    for row in conn.execute("SELECT MaChiTiet FROM CT_PHIEUDICHVU WHERE SoPhieuDV = ?", (so_dv1,)).fetchall():
        cap_nhat_tinh_trang_dich_vu(conn, row["MaChiTiet"], "Đã giao", ma_nv="NV002", ghi_chu="Đã bàn giao cho khách")

    tao_phieu_dich_vu(
        conn, {"ten": "Nguyễn Văn An", "sdt": "0901111222"},
        [
            {"MaDichVu": "DV005", "SoLuong": 1, "ChiPhiRieng": 30000, "TraTruoc": 80000,
             "NgayGiaoDuKien": (date.today() + timedelta(days=4)).isoformat()},
            {"MaDichVu": "DV006", "SoLuong": 1, "ChiPhiRieng": 0, "TraTruoc": 150000,
             "NgayGiaoDuKien": (date.today() + timedelta(days=5)).isoformat()},
        ],
        date.today().isoformat(), ma_nv="NV002", hinh_thuc="Chuyển khoản",
    )

    # 11. Phiếu kiểm kê kho mẫu (NV003 kiểm kê, NV001 Quản lý xác nhận)
    kk_rows = conn.execute("SELECT MaSP, SoLuongTon FROM SANPHAM ORDER BY MaSP LIMIT 6").fetchall()
    kk_items = [{"MaSP": r["MaSP"], "TonThucTe": r["SoLuongTon"], "LyDoChenhLech": ""} for r in kk_rows]
    so_kk = tao_phieu_kiem_ke(conn, _ngay(1, 28), kk_items, ma_nv="NV003", ghi_chu="Kiểm kê đối chiếu cuối tháng")
    xac_nhan_kiem_ke(conn, so_kk, ma_nv_xac_nhan="NV001", is_manager=True)

    # 12. Nhật ký quy định khởi tạo ban đầu
    conn.execute(
        "INSERT INTO NHATKYTHAYDOIQUYDINH(LoaiQuyDinh, MaDoiTuong, GiaTriCu, GiaTriMoi, "
        "ThoiDiemCapNhat, MaNV_CapNhat, GhiChu) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("Tỷ lệ trả trước", "THAMSO:1", None, "50%", f"{_ngay(2, 1)} 08:30:00", "NV001", "Thiết lập tỷ lệ trả trước mặc định ban đầu"),
    )
    conn.commit()
