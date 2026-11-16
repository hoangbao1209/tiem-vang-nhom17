"""Dữ liệu mẫu đầy đủ cho cửa hàng vàng bạc đá quý."""
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from .services.inventory import tao_phieu_kiem_ke, xac_nhan_kiem_ke
from .services.vouchers import (NGUON_ONLINE, TT_CHO, giao_dich_vu, tao_phieu_ban,
                                tao_phieu_dich_vu, tao_phieu_mua)


def _ngay(thang_truoc, ngay):
    t = date.today()
    y, m = t.year, t.month - thang_truoc
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, min(ngay, 28)).isoformat()


def seed_data(conn):
    conn.executemany("INSERT INTO THAMSO(TenThamSo, GiaTri, MoTa) VALUES (?, ?, ?)", [
        ("TenCuaHang", "Tiệm Vàng Kim Ngân", "Tên cửa hàng"),
        ("DiaChi", "123 Lê Lợi, Quận 1, TP. Hồ Chí Minh", "Địa chỉ"),
        ("SoDienThoai", "0909 123 456", "Số điện thoại"),
        ("Email", "lienhe@kimngan.vn", "Email"),
        ("SoLuongTonToiThieu", "2", "Ngưỡng cảnh báo sắp hết hàng"),
        ("TiLeTraTruocToiThieu", "50", "Tỷ lệ trả trước tối thiểu mặc định (%)"),
    ])

    conn.executemany(
        "INSERT INTO NGUOIDUNG(MaND, TenDangNhap, MatKhau, HoTen, VaiTro, CoQuyenChuyenNguoc, TinhTrang) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", [
            (1, "admin", generate_password_hash("admin123"), "Quản lý cửa hàng", "admin", 1, "Đang làm việc"),
            (2, "nhanvien", generate_password_hash("nhanvien123"), "Nhân viên bán hàng", "nhanvien", 0, "Đang làm việc"),
        ])

    conn.executemany("INSERT INTO DONVITINH(MaDVT, TenDVT) VALUES (?, ?)", [
        (1, "Chiếc"), (2, "Chỉ"), (3, "Cặp"), (4, "Viên"), (5, "Lượng"),
    ])

    # (Mã, Tên loại, Mã ĐVT, % lợi nhuận)
    conn.executemany(
        "INSERT INTO LOAISANPHAM(MaLoaiSP, TenLoaiSP, MaDVT, PhanTramLoiNhuan) VALUES (?, ?, ?, ?)", [
            (1, "Vàng miếng & Nhẫn tròn", 2, 2),
            (2, "Nhẫn trang sức", 1, 15),
            (3, "Dây chuyền", 1, 18),
            (4, "Bông tai", 3, 22),
            (5, "Lắc & Vòng tay", 1, 20),
            (6, "Đá quý & Kim cương", 4, 28),
            (7, "Trang sức bạc", 1, 35),
        ])

    img = "img/products/"
    products = [
        (1, "SP001", "Vàng miếng SJC 999.9 (1 chỉ)", 1, "Vàng 999.9", "24K (99.99%)", "1 chỉ (3.75g)",
         "Bảo hành thu đổi theo giá niêm yết SJC toàn quốc",
         "Vàng miếng SJC 999.9 ép vỉ nguyên seal kèm số seri kiểm định chính hãng, thích hợp tích trữ tài sản và làm quà biếu giá trị.",
         img + "gold-bar.svg"),
        (2, "SP002", "Nhẫn tròn trơn 999.9 Kim Ngân (1 chỉ)", 1, "Vàng 999.9", "24K (99.99%)", "1 chỉ (3.75g)",
         "Thu đổi linh hoạt, kiểm tra tuổi vàng miễn phí",
         "Nhẫn tròn trơn ép vỉ hàm lượng vàng 99.99% chuẩn xác, bề mặt bóng gương tinh xảo, phù hợp tích trữ hoặc làm quà cưới hỏi.",
         img + "gold-bar.svg"),
        (3, "SP003", "Vàng miếng SJC 999.9 (1 lượng)", 1, "Vàng 999.9", "24K (99.99%)", "1 lượng (37.5g)",
         "Bảo hành thu đổi theo giá niêm yết SJC",
         "Vàng miếng SJC trọng lượng 1 lượng (10 chỉ) chuẩn 999.9 nguyên bản, đảm bảo tính thanh khoản cao và giá trị bền vững.",
         img + "gold-bar.svg"),
        (4, "SP004", "Nhẫn kim tiền vàng 18K tài lộc", 2, "Vàng Tây 18K", "18K (75%)", "1.2 chỉ (~4.5g)",
         "Làm sạch & đánh bóng miễn phí trọn đời",
         "Thiết kế chuỗi đồng tiền nối liền mang ý nghĩa chiêu tài giữ lộc, chế tác tinh tế trên nền vàng 18K bền màu, dễ phối trang phục.",
         img + "ring.svg"),
        (5, "SP005", "Nhẫn cưới vàng trắng đính kim cương tấm", 2, "Vàng trắng 14K & Kim cương", "14K (58.5%)", "1.4 chỉ (~5.25g)",
         "Bảo hành gắn đá, làm mới & chỉnh size trọn đời",
         "Cặp nhẫn cưới chế tác từ vàng trắng 14K cao cấp, đính 12 viên kim cương tấm nước E-F cắt giác hoàn hảo, biểu tượng cho tình yêu vĩnh cửu.",
         img + "ring.svg"),
        (6, "SP006", "Nhẫn nam vàng 24K mặt đá Ruby thiên nhiên", 2, "Vàng 24K & Đá Ruby", "24K (99.9%)", "3.2 chỉ (~12g)",
         "Kèm giấy kiểm định đá quý, bảo hành trọn đời",
         "Phom nhẫn bản vuông nam tính mạnh mẽ kết hợp viên Ruby thiên nhiên sắc đỏ huyết bồ câu sang trọng, tôn lên phong thái doanh nhân.",
         img + "ring.svg"),
        (7, "SP007", "Nhẫn nữ Solitaire vàng trắng đính Moissanite", 2, "Vàng trắng 18K & Moissanite", "18K (75%)", "0.95 chỉ (~3.56g)",
         "Bảo hành chấu giữ đá & làm sáng trọn đời",
         "Ổ nhẫn 6 chấu thanh thoát nâng đỡ viên chủ Moissanite 6.3 ly chuẩn giác cắt Hearts & Arrows rực rỡ dưới mọi góc ánh sáng.",
         img + "ring.svg"),
        (8, "SP008", "Dây chuyền vàng 18K mặt trái tim đá CZ", 3, "Vàng 18K & Đá CZ", "18K (75%)", "1.5 chỉ (~5.62g)",
         "Bảo hành hàn nối & đánh bóng trọn đời",
         "Dây mảnh 42cm kết hợp mặt trái tim cách điệu đính đá CZ cao cấp sáng lấp lánh, món quà tinh tế dành tặng phái đẹp.",
         img + "necklace.svg"),
        (9, "SP009", "Dây chuyền vàng Ý 24K mắt xích thanh lịch", 3, "Vàng Ý 24K", "24K (99.9%)", "3.0 chỉ (~11.25g)",
         "Bảo hành làm sạch siêu âm miễn phí trọn đời",
         "Công nghệ dập cắt Ý tạo độ bắt sáng vượt trội, mắt xích đan khít chắc chắn và êm ái khi đeo hằng ngày hoặc dự tiệc.",
         img + "necklace.svg"),
        (10, "SP010", "Dây chuyền ngọc trai Akoya khóa vàng 18K", 3, "Ngọc trai Akoya & Vàng 18K", "18K (75%)", "1 chuỗi 45cm",
         "Bảo hành dây xâu & làm bóng ngọc trai",
         "Chuỗi ngọc trai Akoya tuyển chọn size 7.5–8mm ánh xà cừ hồng tự nhiên, khóa gài bằng vàng 18K sang trọng và quý phái.",
         img + "necklace.svg"),
        (11, "SP011", "Bông tai vàng trắng ngọc trai nước ngọt", 4, "Vàng trắng 10K & Ngọc trai", "10K (41.6%)", "0.8 chỉ / cặp",
         "Bảo hành làm sạch và thay chốt khóa trọn đời",
         "Sự kết hợp dịu dàng giữa sắc vàng trắng hiện đại và viên ngọc trai tròn đều tự nhiên, mang lại nét thanh lịch cho khuôn mặt.",
         img + "earring.svg"),
        (12, "SP012", "Bông tai vàng 18K giọt nước đính đá CZ", 4, "Vàng 18K & Đá CZ", "18K (75%)", "0.9 chỉ / cặp",
         "Bảo hành chấu đá & làm sáng trọn đời",
         "Kiểu dáng giọt nước mềm mại ôm sát dái tai, từng viên đá CZ cắt giác tỉ mỉ giúp bắt sáng nổi bật trong các buổi tiệc tối.",
         img + "earring.svg"),
        (13, "SP013", "Lắc tay vàng 18K hoa mai năm cánh", 5, "Vàng 18K", "18K (75%)", "1.8 chỉ (~6.75g)",
         "Bảo hành hàn nối, đánh bóng miễn phí",
         "Charm hoa mai 5 cánh đan xen bi vàng phay sáng tạo nên vẻ nữ tính, may mắn và tươi mới trên cổ tay.",
         img + "bracelet.svg"),
        (14, "SP014", "Vòng tay vàng ta 24K chạm rồng thủ công", 5, "Vàng 24K nguyên chất", "24K (99.9%)", "5.0 chỉ (~18.75g)",
         "Chế tác thủ công, kiểm định tuổi vàng đầy đủ",
         "Vòng tay bản tròn chạm khắc hình tượng rồng uy nghi bởi nghệ nhân kim hoàn, tượng trưng cho quyền uy và thịnh vượng.",
         img + "bracelet.svg"),
        (15, "SP015", "Kiềng tay cưới vàng 24K hoa văn long phụng", 5, "Vàng 24K", "24K (99.9%)", "4.0 chỉ (~15g)",
         "Thu đổi chuẩn tuổi vàng, làm mới miễn phí",
         "Họa tiết long phụng sum vầy dập nổi sắc nét, phù hợp làm của hồi môn trong lễ cưới truyền thống.",
         img + "bracelet.svg"),
        (16, "SP016", "Kim cương thiên nhiên 5.4 ly kiểm định GIA", 6, "Kim cương thiên nhiên", "Nước D – VS1", "0.62 carat",
         "Đầy đủ chứng thư kiểm định quốc tế GIA",
         "Viên kim cương tự nhiên 5.4 ly nước D trắng tinh khiết, độ sạch VS1, giác cắt Excellent cho độ lửa tán sắc tối đa.",
         img + "gem.svg"),
        (17, "SP017", "Đá Sapphire xanh hoàng gia 1.0 carat", 6, "Sapphire thiên nhiên", "Royal Blue", "1.0 carat",
         "Kèm giấy giám định PNJ Lab / DOJI Lab",
         "Sapphire xanh lam đậm tự nhiên chưa qua xử lý nhiệt, giác cắt oval cân đối, thích hợp lên nhẫn hoặc mặt dây chuyền thiết kế riêng.",
         img + "gem.svg"),
        (18, "SP018", "Nhẫn bạc Ý 925 xi bạch kim tối giản", 7, "Bạc Ý 925", "S925 (92.5%)", "3.8g",
         "Làm sáng bạc miễn phí trọn đời",
         "Bạc Ý 925 phủ lớp Rhodium chống oxy hóa giúp nhẫn giữ độ bóng trắng như bạch kim, thiết kế trơn thanh lịch cho cả nam và nữ.",
         img + "silver.svg"),
        (19, "SP019", "Dây chuyền bạc 925 mặt tròn đính đá trắng", 7, "Bạc Ý 925 & Đá CZ", "S925 (92.5%)", "4.5g",
         "Bảo hành đánh bóng & thay đá nhỏ miễn phí",
         "Thiết kế trẻ trung năng động, mặt tròn Halo đính viền đá nhỏ tinh xảo, phù hợp đeo hằng ngày hoặc làm quà sinh nhật.",
         img + "silver.svg"),
    ]
    conn.executemany(
        "INSERT INTO SANPHAM(MaSP, MaCode, TenSP, MaLoaiSP, ChatLieu, TuoiVang, TrongLuong, BaoHanh, MoTa, HinhAnh) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        products,
    )

    conn.executemany("INSERT INTO NHACUNGCAP(MaNCC, TenNCC, DiaChi, SoDienThoai, TinhTrang) VALUES (?, ?, ?, ?, ?)", [
        (1, "Công ty Vàng bạc Kim Phát", "12 Trần Hưng Đạo, Quận 5, TP.HCM", "02838551234", "Đang hợp tác"),
        (2, "Xưởng chế tác Ngọc Minh", "45 Lê Văn Sỹ, Quận 3, TP.HCM", "0903456789", "Đang hợp tác"),
        (3, "Công ty Đá quý Phương Nam", "88 Nguyễn Trãi, Quận 1, TP.HCM", "02839205678", "Đang hợp tác"),
    ])

    conn.executemany(
        "INSERT INTO LOAIDICHVU(MaLoaiDV, TenLoaiDV, DonGia, PhanTramTraTruoc, TinhTrang) VALUES (?, ?, ?, ?, ?)", [
            (1, "Đánh bóng trang sức", 50000, 50, "Đang hoạt động"),
            (2, "Làm sạch bằng sóng siêu âm", 30000, 50, "Đang hoạt động"),
            (3, "Khắc chữ laser theo yêu cầu", 100000, 50, "Đang hoạt động"),
            (4, "Gắn / thay đá trang sức", 150000, 50, "Đang hoạt động"),
            (5, "Sửa, hàn, nới size nhẫn", 120000, 50, "Đang hoạt động"),
            (6, "Xi mạ vàng / bạch kim", 250000, 50, "Đang hoạt động"),
            (7, "Cân kiểm tra & đo tuổi vàng", 80000, 50, "Đang hoạt động"),
        ])
    conn.commit()

    def mh(ma, sl, gia):
        return {"MaSP": ma, "SoLuong": sl, "DonGia": gia}

    tao_phieu_mua(conn, 1, _ngay(2, 5), [
        mh(1, 20, 8500000), mh(2, 15, 8450000), mh(3, 4, 84500000), mh(4, 8, 6200000),
        mh(8, 6, 9600000), mh(9, 4, 24000000), mh(13, 5, 11500000), mh(14, 2, 42000000), mh(15, 3, 34000000)
    ], ma_nd=1)
    tao_phieu_mua(conn, 2, _ngay(2, 12), [
        mh(5, 5, 18500000), mh(6, 4, 25800000), mh(7, 6, 12400000), mh(10, 5, 14500000),
        mh(11, 10, 3800000), mh(12, 10, 4200000), mh(18, 30, 450000), mh(19, 20, 680000)
    ], ma_nd=1)
    tao_phieu_mua(conn, 3, _ngay(1, 3), [mh(16, 3, 38000000), mh(17, 3, 21000000)], ma_nd=1)
    tao_phieu_mua(conn, 1, _ngay(1, 20), [mh(1, 10, 8600000), mh(4, 5, 6300000)], ma_nd=2)

    def kh(ten, sdt, dia_chi=None):
        return {"ten": ten, "sdt": sdt, "dia_chi": dia_chi}

    tao_phieu_ban(conn, kh("Nguyễn Văn An", "0901111222", "Quận 7, TP.HCM"),
                  [{"MaSP": 1, "SoLuong": 3}, {"MaSP": 4, "SoLuong": 1}], _ngay(2, 18), ma_nd=2, pttt="Tiền mặt")
    tao_phieu_ban(conn, kh("Trần Thị Bình", "0912333444", "Thủ Đức, TP.HCM"),
                  [{"MaSP": 8, "SoLuong": 1}, {"MaSP": 11, "SoLuong": 1}], _ngay(1, 8), ma_nd=2, pttt="Chuyển khoản")
    tao_phieu_ban(conn, kh("Lê Hoàng Cường", "0987555666", "Bình Thạnh, TP.HCM"),
                  [{"MaSP": 5, "SoLuong": 1}, {"MaSP": 1, "SoLuong": 2}], _ngay(1, 25), ma_nd=2, pttt="Tiền mặt")
    tao_phieu_ban(conn, kh("Phạm Minh Đức", "0938777888", "Gò Vấp, TP.HCM"),
                  [{"MaSP": 18, "SoLuong": 2}], f"{date.today().isoformat()} 09:30",
                  nguon=NGUON_ONLINE, trang_thai=TT_CHO, ghi_chu="Giao giờ hành chính", pttt="Chuyển khoản")

    so = tao_phieu_dich_vu(conn, kh("Trần Thị Bình", "0912333444"), [
        {"MaLoaiDV": 1, "SoLuong": 2, "ChiPhiRieng": 0, "TraTruoc": 50000, "NgayGiao": _ngay(1, 12)},
        {"MaLoaiDV": 3, "SoLuong": 1, "ChiPhiRieng": 50000, "TraTruoc": 100000, "NgayGiao": _ngay(1, 15)},
    ], _ngay(1, 10), ma_nd=2)
    for row in conn.execute("SELECT MaCT FROM CT_PHIEUDICHVU WHERE SoPhieu = ?", (so,)).fetchall():
        giao_dich_vu(conn, row["MaCT"], ma_nd=2)

    tao_phieu_dich_vu(conn, kh("Nguyễn Văn An", "0901111222"), [
        {"MaLoaiDV": 5, "SoLuong": 1, "ChiPhiRieng": 30000, "TraTruoc": 80000,
         "NgayGiao": (date.today() + timedelta(days=5)).isoformat()},
    ], date.today().isoformat(), ma_nd=2)

    # Phiếu kiểm kê mẫu
    kk_rows = conn.execute("SELECT MaSP, SoLuongTon FROM SANPHAM ORDER BY MaSP LIMIT 6").fetchall()
    kk_items = [{"MaSP": r["MaSP"], "TonThucTe": r["SoLuongTon"], "LyDoChenhLech": ""} for r in kk_rows]
    so_kk = tao_phieu_kiem_ke(conn, _ngay(1, 28), kk_items, ma_nd=2, ghi_chu="Kiểm kê định kỳ cuối tháng")
    xac_nhan_kiem_ke(conn, so_kk, ma_nd_xac_nhan=1, is_admin=True)
