/* Hỗ trợ tính toán tự động trên các biểu mẫu BM1, BM2, BM3 */
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

function recalcVoucher() {
  // BM1: Phiếu mua hàng
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

  // BM2: Phiếu bán hàng
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
    if (totalEl) totalEl.textContent = formatVND(total);
  }

  // BM3: Phiếu dịch vụ
  const svTable = document.getElementById("service-items-body");
  if (svTable) {
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
      const pt = opt && opt.value ? Number(opt.dataset.pt || 50) : 50;
      const dgdt = base + Math.max(cpr, 0);
      const sub = dgdt * Math.max(qty, 0);
      const minPre = Math.round((sub * pt) / 100);

      if (dgdvEl) dgdvEl.textContent = formatVND(base);
      if (dgdtEl) dgdtEl.textContent = formatVND(dgdt);
      if (ttEl) ttEl.textContent = formatVND(sub);
      if (minHint) minHint.textContent = `Tối thiểu ${pt}%: ${formatVND(minPre)}`;
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
}

document.addEventListener("input", (e) => {
  if (e.target.matches("input[name='DonGia'], input[name='TraTruoc']")) {
    e.target.dataset.touched = "1";
  }
  if (e.target.closest("#purchase-items-body, #sale-items-body, #service-items-body")) {
    recalcVoucher();
  }
});

document.addEventListener("change", (e) => {
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
  if (e.target.closest("#purchase-items-body, #sale-items-body, #service-items-body")) {
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
