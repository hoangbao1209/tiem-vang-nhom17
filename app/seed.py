"""Dữ liệu mẫu để demo. Phiếu được tạo qua chính các hàm nghiệp vụ
nên tồn kho / giá mua luôn nhất quán."""
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

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
    ])

    conn.executemany("INSERT INTO NGUOIDUNG(TenDangNhap, MatKhau, HoTen, VaiTro) VALUES (?, ?, ?, ?)", [
        ("admin", generate_password_hash("admin123"), "Quản trị viên", "admin"),
        ("nhanvien", generate_password_hash("nhanvien123"), "Nhân viên bán hàng", "nhanvien"),
    ])

    conn.executemany("INSERT INTO DONVITINH(MaDVT, TenDVT) VALUES (?, ?)", [
        (1, "Cái"), (2, "Chỉ"), (3, "Cặp"), (4, "Viên"), (5, "Lượng"),
    ])

    # (Mã, Tên loại, Mã ĐVT, % lợi nhuận)
    conn.executemany(
        "INSERT INTO LOAISANPHAM(MaLoaiSP, TenLoaiSP, MaDVT, PhanTramLoiNhuan) VALUES (?, ?, ?, ?)", [
            (1, "Vàng miếng", 2, 2),
            (2, "Nhẫn", 1, 15),
            (3, "Dây chuyền", 1, 20),
            (4, "Bông tai", 3, 25),
            (5, "Lắc - Vòng tay", 1, 20),
            (6, "Đá quý", 4, 30),
            (7, "Trang sức bạc", 1, 40),
        ])

    img = "img/products/"
    conn.executemany(
        "INSERT INTO SANPHAM(MaSP, TenSP, MaLoaiSP, MoTa, HinhAnh) VALUES (?, ?, ?, ?, ?)", [
            (1, "Vàng miếng SJC 1 chỉ", 1, "Vàng miếng 999.9, có tem kiểm định, thích hợp tích trữ.", img + "gold-bar.svg"),
            (2, "Vàng nhẫn tròn trơn 9999 – 1 chỉ", 1, "Nhẫn tròn trơn ép vỉ, hàm lượng vàng 99.99%.", img + "gold-bar.svg"),
            (3, "Nhẫn kim tiền vàng 18K", 2, "Nhẫn nữ vàng 18K họa tiết kim tiền mang may mắn, tài lộc.", img + "ring.svg"),
            (4, "Nhẫn cưới vàng trắng đính kim cương", 2, "Vàng trắng 14K, đính kim cương tấm, thiết kế tinh tế cho ngày trọng đại.", img + "ring.svg"),
            (5, "Nhẫn nam vàng 24K mặt đá Ruby", 2, "Nhẫn nam vàng 24K, mặt đá Ruby thiên nhiên đỏ thẫm.", img + "ring.svg"),
            (6, "Dây chuyền vàng 18K mặt trái tim", 3, "Dây chuyền vàng 18K kèm mặt trái tim đính đá CZ.", img + "necklace.svg"),
            (7, "Dây chuyền vàng Ý 24K", 3, "Dây chuyền vàng 24K kiểu Ý, mắt xích chắc chắn, sáng bóng.", img + "necklace.svg"),
            (8, "Bông tai vàng trắng ngọc trai", 4, "Bông tai vàng trắng 10K, ngọc trai nước ngọt tự nhiên.", img + "earring.svg"),
            (9, "Bông tai vàng 18K đính đá CZ", 4, "Thiết kế giọt nước, đá CZ lấp lánh.", img + "earring.svg"),
            (10, "Lắc tay vàng 18K hoa mai", 5, "Lắc tay nữ vàng 18K, charm hoa mai 5 cánh.", img + "bracelet.svg"),
            (11, "Vòng tay vàng ta chạm rồng", 5, "Vòng tay vàng 24K chạm rồng thủ công, quà tặng phong thủy.", img + "bracelet.svg"),
            (12, "Kim cương thiên nhiên 5.4 ly", 6, "Kim cương nước D, độ tinh khiết VS1, có giấy kiểm định GIA.", img + "gem.svg"),
            (13, "Đá Sapphire xanh 1 carat", 6, "Sapphire xanh hoàng gia, giác cắt oval.", img + "gem.svg"),
            (14, "Nhẫn bạc Ý 925", 7, "Bạc Ý 925 xi bạch kim, không đen, không dị ứng.", img + "silver.svg"),
            (15, "Dây chuyền bạc đính đá", 7, "Dây chuyền bạc 925 mặt đá tròn, phong cách trẻ trung.", img + "silver.svg"),
        ])

    conn.executemany("INSERT INTO NHACUNGCAP(MaNCC, TenNCC, DiaChi, SoDienThoai) VALUES (?, ?, ?, ?)", [
        (1, "Công ty Vàng bạc Kim Phát", "12 Trần Hưng Đạo, Quận 5, TP.HCM", "02838551234"),
        (2, "Xưởng chế tác Ngọc Minh", "45 Lê Văn Sỹ, Quận 3, TP.HCM", "0903456789"),
        (3, "Công ty Đá quý Phương Nam", "88 Nguyễn Trãi, Quận 1, TP.HCM", "02839205678"),
    ])

    # (Mã, Tên, Đơn giá, % trả trước tối thiểu)
    conn.executemany(
        "INSERT INTO LOAIDICHVU(MaLoaiDV, TenLoaiDV, DonGia, PhanTramTraTruoc) VALUES (?, ?, ?, ?)", [
            (1, "Đánh bóng trang sức", 50000, 50),
            (2, "Làm sạch bằng sóng siêu âm", 30000, 50),
            (3, "Khắc chữ theo yêu cầu", 100000, 50),
            (4, "Gắn / thay đá", 150000, 50),
            (5, "Sửa, hàn, nới size nhẫn", 120000, 50),
            (6, "Xi mạ vàng / bạch kim", 250000, 60),
        ])
    conn.commit()

    # ---------- Phiếu mua hàng (nhập kho) ----------
    def mh(ma, sl, gia):
        return {"MaSP": ma, "SoLuong": sl, "DonGia": gia}

    tao_phieu_mua(conn, 1, _ngay(2, 5), [
        mh(1, 20, 8500000), mh(2, 15, 8450000), mh(3, 8, 6200000), mh(6, 6, 9600000),
        mh(7, 4, 24000000), mh(10, 5, 11500000), mh(11, 2, 32000000)])
    tao_phieu_mua(conn, 2, _ngay(2, 12), [
        mh(4, 5, 18500000), mh(5, 4, 15800000), mh(8, 10, 3800000), mh(9, 10, 4200000),
        mh(14, 30, 450000), mh(15, 20, 680000)])
    tao_phieu_mua(conn, 3, _ngay(1, 3), [mh(12, 3, 28000000), mh(13, 3, 21000000)])
    tao_phieu_mua(conn, 1, _ngay(1, 20), [mh(1, 10, 8600000), mh(3, 5, 6300000)])

    # ---------- Phiếu bán hàng ----------
    def kh(ten, sdt, dia_chi=None):
        return {"ten": ten, "sdt": sdt, "dia_chi": dia_chi}

    tao_phieu_ban(conn, kh("Nguyễn Văn An", "0901111222", "Quận 7, TP.HCM"),
                  [{"MaSP": 1, "SoLuong": 3}, {"MaSP": 3, "SoLuong": 1}], _ngay(2, 18))
    tao_phieu_ban(conn, kh("Trần Thị Bình", "0912333444", "Thủ Đức, TP.HCM"),
                  [{"MaSP": 6, "SoLuong": 1}, {"MaSP": 8, "SoLuong": 1}], _ngay(1, 8))
    tao_phieu_ban(conn, kh("Lê Hoàng Cường", "0987555666", "Bình Thạnh, TP.HCM"),
                  [{"MaSP": 4, "SoLuong": 1}, {"MaSP": 1, "SoLuong": 2}], _ngay(1, 25))
    tao_phieu_ban(conn, kh("Phạm Minh Đức", "0938777888", "Gò Vấp, TP.HCM"),
                  [{"MaSP": 14, "SoLuong": 2}], f"{date.today().isoformat()} 09:30",
                  nguon=NGUON_ONLINE, trang_thai=TT_CHO, ghi_chu="Giao giờ hành chính")

    # ---------- Phiếu dịch vụ ----------
    so = tao_phieu_dich_vu(conn, kh("Trần Thị Bình", "0912333444"), [
        {"MaLoaiDV": 1, "SoLuong": 2, "ChiPhiRieng": 0, "TraTruoc": 50000, "NgayGiao": _ngay(1, 12)},
        {"MaLoaiDV": 3, "SoLuong": 1, "ChiPhiRieng": 50000, "TraTruoc": 100000, "NgayGiao": _ngay(1, 15)},
    ], _ngay(1, 10))
    for row in conn.execute("SELECT MaCT FROM CT_PHIEUDICHVU WHERE SoPhieu = ?", (so,)).fetchall():
        giao_dich_vu(conn, row["MaCT"])

    tao_phieu_dich_vu(conn, kh("Nguyễn Văn An", "0901111222"), [
        {"MaLoaiDV": 5, "SoLuong": 1, "ChiPhiRieng": 30000, "TraTruoc": 80000,
         "NgayGiao": (date.today() + timedelta(days=5)).isoformat()},
    ], date.today().isoformat())
