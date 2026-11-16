/* Hỗ trợ tính toán tự động trên các biểu mẫu bán hàng, mua hàng, dịch vụ và kiểm kê */
function formatVND(n) {
  const num = Number(n) || 0;
  return num.toLocaleString("vi-VN") + " ₫";
}

function addVoucherRow(tbodyId, templateId) {
  const tbody = document.getElementById(tbodyId);
  const tpl = document.getElementById(templateId);
  if (!tbody || !tpl) return;
  const clone = tpl.content.cloneNode(true);
  tbody.appendChild(clone);
  recalcVoucher();
}

function removeVoucherRow(btn) {
  const tbody = btn.closest("tbody");
  if (tbody && tbody.querySelectorAll("tr").length > 1) {
    btn.closest("tr").remove();
    recalcVoucher();
  }
}

function updateSalePayment() {
  const ptttEl = document.getElementById("sale-pttt");
  const nhanInput = document.getElementById("sale-so-tien-nhan");
  const thuaEl = document.getElementById("sale-tien-thua");
  const totalEl = document.getElementById("voucher-total");
  if (!ptttEl || !nhanInput || !thuaEl || !totalEl) return;

  const total = Number(totalEl.dataset.raw || 0);
  if (ptttEl.value === "Chuyển khoản") {
    nhanInput.value = total;
    nhanInput.readOnly = true;
    thuaEl.textContent = formatVND(0);
    thuaEl.style.color = "var(--slate-700)";
  } else {
    nhanInput.readOnly = false;
    if (!nhanInput.dataset.touched) {
      nhanInput.value = total;
    }
    const nhan = Number(nhanInput.value || 0);
    const thua = nhan - total;
    thuaEl.textContent = thua >= 0 ? formatVND(thua) : "Chưa đủ (" + formatVND(thua) + ")";
    thuaEl.style.color = thua >= 0 ? "var(--success)" : "var(--danger)";
  }
}

function recalcVoucher() {
  // Phiếu mua hàng
  const purchaseTable = document.getElementById("purchase-items-body");
  if (purchaseTable) {
    let total = 0;
    purchaseTable.querySelectorAll("tr").forEach((tr) => {
      const sel = tr.querySelector("select[name='MaSP']");
      const opt = sel && sel.selectedOptions[0];
      const loaiEl = tr.querySelector(".cell-loai");
      const dvtEl = tr.querySelector(".cell-dvt");
      const priceInput = tr.querySelector("input[name='DonGia']");
      if (opt && opt.value) {
        if (loaiEl) loaiEl.textContent = opt.dataset.loai || "";
        if (dvtEl) dvtEl.textContent = opt.dataset.dvt || "";
        if (priceInput && !priceInput.dataset.touched && opt.dataset.giamua) {
          priceInput.value = opt.dataset.giamua;
        }
      }
      const qty = Number(tr.querySelector("input[name='SoLuong']")?.value || 0);
      const price = Number(priceInput?.value || 0);
      const sub = Math.max(qty, 0) * Math.max(price, 0);
      total += sub;
      const subEl = tr.querySelector(".cell-thanhtien");
      if (subEl) subEl.textContent = formatVND(sub);
    });
    const totalEl = document.getElementById("voucher-total");
    if (totalEl) totalEl.textContent = formatVND(total);
  }

  // Phiếu bán hàng
  const saleTable = document.getElementById("sale-items-body");
  if (saleTable) {
    let total = 0;
    saleTable.querySelectorAll("tr").forEach((tr) => {
      const sel = tr.querySelector("select[name='MaSP']");
      const opt = sel && sel.selectedOptions[0];
      const loaiEl = tr.querySelector(".cell-loai");
      const dvtEl = tr.querySelector(".cell-dvt");
      const tonEl = tr.querySelector(".cell-ton");
      const giaEl = tr.querySelector(".cell-giaban");
      const qtyInput = tr.querySelector("input[name='SoLuong']");
      let price = 0;
      if (opt && opt.value) {
        if (loaiEl) loaiEl.textContent = opt.dataset.loai || "";
        if (dvtEl) dvtEl.textContent = opt.dataset.dvt || "";
        if (tonEl) tonEl.textContent = opt.dataset.ton || "0";
        price = Number(opt.dataset.giaban || 0);
        if (giaEl) giaEl.textContent = formatVND(price);
        if (qtyInput && opt.dataset.ton) qtyInput.max = opt.dataset.ton;
      }
      const qty = Number(qtyInput?.value || 0);
      const sub = Math.max(qty, 0) * price;
      total += sub;
      const subEl = tr.querySelector(".cell-thanhtien");
      if (subEl) subEl.textContent = formatVND(sub);
    });
    const totalEl = document.getElementById("voucher-total");
    if (totalEl) {
      totalEl.dataset.raw = String(total);
      totalEl.textContent = formatVND(total);
    }
    updateSalePayment();
  }

  // Phiếu dịch vụ
  const svTable = document.getElementById("service-items-body");
  if (svTable) {
    const sysRatio = Number(svTable.dataset.ratio || 50);
    let total = 0;
    let totalPre = 0;
    let totalRem = 0;
    svTable.querySelectorAll("tr").forEach((tr) => {
      const sel = tr.querySelector("select[name='MaLoaiDV']");
      const opt = sel && sel.selectedOptions[0];
      const dgdvEl = tr.querySelector(".cell-dgdv");
      const dgdtEl = tr.querySelector(".cell-dgdt");
      const ttEl = tr.querySelector(".cell-thanhtien");
      const clEl = tr.querySelector(".cell-conlai");
      const minHint = tr.querySelector(".cell-min-hint");
      const cpr = Number(tr.querySelector("input[name='ChiPhiRieng']")?.value || 0);
      const qty = Number(tr.querySelector("input[name='SoLuong']")?.value || 0);
      const traInput = tr.querySelector("input[name='TraTruoc']");

      const base = opt && opt.value ? Number(opt.dataset.dongia || 0) : 0;
      const dgdt = base + Math.max(cpr, 0);
      const sub = dgdt * Math.max(qty, 0);
      const minPre = Math.round((sub * sysRatio) / 100);

      if (dgdvEl) dgdvEl.textContent = formatVND(base);
      if (dgdtEl) dgdtEl.textContent = formatVND(dgdt);
      if (ttEl) ttEl.textContent = formatVND(sub);
      if (minHint) minHint.textContent = `Tối thiểu ${sysRatio}%: ${formatVND(minPre)}`;
      if (traInput && !traInput.dataset.touched && sub > 0) {
        traInput.value = minPre;
      }
      const tra = Number(traInput?.value || 0);
      const rem = sub - tra;
      if (clEl) clEl.textContent = formatVND(rem);

      total += sub;
      totalPre += tra;
      totalRem += rem;
    });
    const tEl = document.getElementById("voucher-total");
    const pEl = document.getElementById("voucher-prepaid");
    const rEl = document.getElementById("voucher-remain");
    if (tEl) tEl.textContent = formatVND(total);
    if (pEl) pEl.textContent = formatVND(totalPre);
    if (rEl) rEl.textContent = formatVND(totalRem);
  }

  // Phiếu kiểm kê kho
  const kkTable = document.getElementById("stocktake-items-body");
  if (kkTable) {
    kkTable.querySelectorAll("tr").forEach((tr) => {
      const sysVal = Number(tr.dataset.ton || 0);
      const actualInput = tr.querySelector("input[name='TonThucTe']");
      const diffEl = tr.querySelector(".cell-diff");
      const reasonInput = tr.querySelector("input[name='LyDoChenhLech']");
      const actual = Number(actualInput?.value ?? sysVal);
      const diff = actual - sysVal;
      if (diffEl) {
        diffEl.textContent = diff > 0 ? `+${diff}` : String(diff);
        diffEl.style.color = diff === 0 ? "var(--success)" : "var(--danger)";
        diffEl.style.fontWeight = "700";
      }
      if (reasonInput) {
        reasonInput.required = diff !== 0;
        reasonInput.placeholder = diff !== 0 ? "Bắt buộc nhập lý do chênh lệch..." : "Không chênh lệch";
      }
    });
  }
}

document.addEventListener("input", (e) => {
  if (e.target.matches("input[name='DonGia'], input[name='TraTruoc'], #sale-so-tien-nhan")) {
    e.target.dataset.touched = "1";
  }
  if (e.target.id === "sale-so-tien-nhan") {
    updateSalePayment();
    return;
  }
  if (e.target.closest("#purchase-items-body, #sale-items-body, #service-items-body, #stocktake-items-body")) {
    recalcVoucher();
  }
});

document.addEventListener("change", (e) => {
  if (e.target.id === "sale-pttt") {
    const nhanInput = document.getElementById("sale-so-tien-nhan");
    if (nhanInput) delete nhanInput.dataset.touched;
    updateSalePayment();
    return;
  }
  if (e.target.matches("select[name='MaSP']")) {
    const tr = e.target.closest("tr");
    const priceInput = tr?.querySelector("input[name='DonGia']");
    if (priceInput) delete priceInput.dataset.touched;
  }
  if (e.target.matches("select[name='MaLoaiDV']")) {
    const tr = e.target.closest("tr");
    const traInput = tr?.querySelector("input[name='TraTruoc']");
    if (traInput) delete traInput.dataset.touched;
  }
  if (e.target.closest("#purchase-items-body, #sale-items-body, #service-items-body, #stocktake-items-body")) {
    recalcVoucher();
  }
  if (e.target.id === "quick-customer-select") {
    const opt = e.target.selectedOptions[0];
    if (opt && opt.value) {
      const f = e.target.closest("form");
      if (f.querySelector("input[name='TenKH']")) f.querySelector("input[name='TenKH']").value = opt.dataset.ten || "";
      if (f.querySelector("input[name='SoDienThoai']")) f.querySelector("input[name='SoDienThoai']").value = opt.dataset.sdt || "";
      if (f.querySelector("input[name='DiaChi']")) f.querySelector("input[name='DiaChi']").value = opt.dataset.diachi || "";
    }
  }
});

document.addEventListener("DOMContentLoaded", recalcVoucher);
