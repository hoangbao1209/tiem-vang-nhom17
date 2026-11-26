/* Tính toán tự động biểu mẫu & tương tác UX mượt mà (không phụ thuộc thư viện ngoài) */

function formatVND(n) {
  const num = Number(n) || 0;
  return Math.round(num).toLocaleString("vi-VN") + " ₫";
}

function addVoucherRow(tbodyId, templateId) {
  const tbody = document.getElementById(tbodyId);
  const tpl = document.getElementById(templateId);
  if (!tbody || !tpl) return;
  tbody.appendChild(tpl.content.cloneNode(true));
  recalcVoucher();
}

function removeVoucherRow(btn) {
  const tbody = btn.closest("tbody");
  if (tbody && tbody.querySelectorAll("tr").length > 1) {
    btn.closest("tr").remove();
    recalcVoucher();
  }
}

function stepQty(btn, delta) {
  const wrap = btn.closest(".qty-stepper");
  const input = wrap && wrap.querySelector("input[type='number']");
  if (!input) return;
  const min = Number(input.min || 1);
  const max = Number(input.max || 9999);
  const cur = Number(input.value || min);
  const next = Math.min(Math.max(cur + delta, min), max);
  input.value = next;
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

function filterSelectOptions(inputId, selectId) {
  const input = document.getElementById(inputId);
  const sel = document.getElementById(selectId);
  if (!input || !sel) return;
  const kw = input.value.trim().toLowerCase();
  Array.from(sel.options).forEach((opt, idx) => {
    if (idx === 0) return;
    const match = !kw || opt.textContent.toLowerCase().includes(kw);
    opt.hidden = !match;
  });
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
    if (thua >= 0) {
      thuaEl.textContent = formatVND(thua);
      thuaEl.style.color = "var(--emerald)";
    } else {
      thuaEl.textContent = "Còn thiếu " + formatVND(Math.abs(thua));
      thuaEl.style.color = "var(--ruby)";
    }
  }
}

function recalcVoucher() {
  // 1. Phiếu mua hàng
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
        if (loaiEl) loaiEl.textContent = opt.dataset.loai || "—";
        if (dvtEl) dvtEl.textContent = opt.dataset.dvt || "—";
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

  // 2. Phiếu bán hàng
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
        if (loaiEl) loaiEl.textContent = opt.dataset.loai || "—";
        if (dvtEl) dvtEl.textContent = opt.dataset.dvt || "—";
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
      totalEl.dataset.raw = String(Math.round(total));
      totalEl.textContent = formatVND(total);
    }
    updateSalePayment();
  }

  // 3. Phiếu dịch vụ
  const svTable = document.getElementById("service-items-body");
  if (svTable) {
    const sysRatio = Number(svTable.dataset.ratio || 50);
    let total = 0;
    let totalPre = 0;
    let totalRem = 0;
    svTable.querySelectorAll("tr").forEach((tr) => {
      const sel = tr.querySelector("select[name='MaDichVu']");
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
      if (minHint) {
        minHint.textContent = `Tối thiểu ${sysRatio}%: ${formatVND(minPre)}`;
      }
      if (traInput && !traInput.dataset.touched && sub > 0) {
        traInput.value = minPre;
      }
      const tra = Number(traInput?.value || 0);
      const rem = sub - tra;
      if (clEl) clEl.textContent = formatVND(rem);

      if (minHint && sub > 0) {
        if (tra < minPre) {
          minHint.style.color = "var(--ruby)";
        } else if (tra > sub) {
          minHint.textContent = "Không vượt quá thành tiền!";
          minHint.style.color = "var(--ruby)";
        } else {
          minHint.style.color = "var(--emerald)";
        }
      }

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

  // 4. Phiếu kiểm kê kho
  const kkTable = document.getElementById("stocktake-items-body");
  if (kkTable) {
    let diffCount = 0;
    kkTable.querySelectorAll("tr").forEach((tr) => {
      const sysVal = Number(tr.dataset.ton || 0);
      const actualInput = tr.querySelector("input[name='TonThucTe']");
      const diffEl = tr.querySelector(".cell-diff");
      const reasonInput = tr.querySelector("input[name='LyDoChenhLech']");
      const actual = Number(actualInput?.value ?? sysVal);
      const diff = Math.round((actual - sysVal) * 1000) / 1000;
      const isDiff = Math.abs(diff) > 1e-9;
      if (isDiff) diffCount += 1;
      if (diffEl) {
        diffEl.textContent = diff > 0 ? `+${diff}` : String(diff);
        diffEl.style.color = isDiff ? "var(--ruby)" : "var(--emerald)";
        diffEl.style.fontWeight = "700";
      }
      if (reasonInput) {
        reasonInput.required = isDiff;
        reasonInput.placeholder = isDiff ? "Bắt buộc nhập lý do chênh lệch..." : "Khớp số liệu";
        reasonInput.style.borderColor = isDiff && !reasonInput.value.trim() ? "var(--ruby)" : "";
      }
    });
    const countEl = document.getElementById("stocktake-diff-count");
    if (countEl) {
      countEl.textContent = diffCount === 0 ? "Tất cả đều khớp" : `${diffCount} sản phẩm có chênh lệch`;
      countEl.className = diffCount === 0 ? "badge badge-success" : "badge badge-danger";
    }
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
  if (e.target.id === "supplier-quick-search") {
    filterSelectOptions("supplier-quick-search", "purchase-supplier-select");
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
  if (e.target.matches("select[name='MaDichVu']")) {
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
    }
  }
});

document.addEventListener("click", (e) => {
  if (e.target.matches(".alert-close")) {
    const alertBox = e.target.closest(".alert");
    if (alertBox) alertBox.remove();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  recalcVoucher();
  initLuxury3DEffects();
});

/* ==================================================================
   HIỆU ỨNG 3D TƯƠNG TÁC (TILT 3D, ÁNH KIM PHẢN CHIẾU, TRÌNH XEM 3D)
   ================================================================== */
function initLuxury3DEffects() {
  const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) {
    document.querySelectorAll(".reveal-3d").forEach((el) => el.classList.add("is-visible"));
    return;
  }

  // 1. Nghiêng 3D + ánh kim phản chiếu trên Hero Showcase & Thẻ sản phẩm/danh mục
  document.querySelectorAll(".tilt-3d, .hero-3d-card").forEach((card) => {
    let glare = card.querySelector(".glare-layer");
    if (!glare) {
      glare = document.createElement("div");
      glare.className = "glare-layer";
      card.appendChild(glare);
    }
    const maxAngle = card.classList.contains("hero-3d-card") ? 10 : 6.5;

    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width;
      const py = (e.clientY - rect.top) / rect.height;
      const rotY = (px - 0.5) * (maxAngle * 2);
      const rotX = (0.5 - py) * (maxAngle * 2);
      card.style.transform = `perspective(1000px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) translateY(-4px)`;
      card.style.setProperty("--glare-x", `${(px * 100).toFixed(1)}%`);
      card.style.setProperty("--glare-y", `${(py * 100).toFixed(1)}%`);
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = "";
    });
  });

  // 2. Trình xem cận cảnh & xoay 3D trên trang chi tiết sản phẩm
  const stage = document.getElementById("product-3d-stage");
  if (stage) {
    let glare = stage.querySelector(".glare-layer");
    if (!glare) {
      glare = document.createElement("div");
      glare.className = "glare-layer";
      stage.appendChild(glare);
    }
    stage.addEventListener("mousemove", (e) => {
      const rect = stage.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width;
      const py = (e.clientY - rect.top) / rect.height;
      stage.style.setProperty("--glare-x", `${(px * 100).toFixed(1)}%`);
      stage.style.setProperty("--glare-y", `${(py * 100).toFixed(1)}%`);
      stage.style.setProperty("--zoom-x", `${(px * 100).toFixed(1)}%`);
      stage.style.setProperty("--zoom-y", `${(py * 100).toFixed(1)}%`);
      if (!stage.classList.contains("is-zoomed") && !stage.classList.contains("is-auto-3d")) {
        const rotY = (px - 0.5) * 24;
        const rotX = (0.5 - py) * 18;
        stage.style.transform = `rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) scale(1.02)`;
      }
    });
    stage.addEventListener("mouseleave", () => {
      if (!stage.classList.contains("is-auto-3d")) {
        stage.style.transform = "";
      }
    });

    const btnAuto = document.getElementById("btn-toggle-3d");
    const btnZoom = document.getElementById("btn-toggle-zoom");
    if (btnAuto) {
      btnAuto.addEventListener("click", () => {
        stage.classList.remove("is-zoomed");
        if (btnZoom) btnZoom.classList.remove("btn-primary");
        const on = stage.classList.toggle("is-auto-3d");
        stage.style.transform = "";
        btnAuto.classList.toggle("btn-primary", on);
        btnAuto.classList.toggle("btn-outline", !on);
        btnAuto.textContent = on ? "⏸ Dừng xoay 3D" : "✦ Xoay trưng bày 3D";
      });
    }
    if (btnZoom) {
      btnZoom.addEventListener("click", () => {
        stage.classList.remove("is-auto-3d");
        if (btnAuto) {
          btnAuto.classList.remove("btn-primary");
          btnAuto.classList.add("btn-outline");
          btnAuto.textContent = "✦ Xoay trưng bày 3D";
        }
        stage.style.transform = "";
        const on = stage.classList.toggle("is-zoomed");
        btnZoom.classList.toggle("btn-primary", on);
        btnZoom.classList.toggle("btn-outline", !on);
        btnZoom.textContent = on ? "✕ Thoát phóng to" : "🔍 Soi cận cảnh";
      });
    }
  }

  // 3. Xuất hiện mượt theo chiều sâu 3D khi cuộn trang
  const reveals = document.querySelectorAll(".reveal-3d");
  if (reveals.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            en.target.classList.add("is-visible");
            io.unobserve(en.target);
          }
        });
      },
      { threshold: 0.08 }
    );
    reveals.forEach((el, idx) => {
      el.style.transitionDelay = `${Math.min((idx % 4) * 70, 210)}ms`;
      io.observe(el);
    });
  } else {
    reveals.forEach((el) => el.classList.add("is-visible"));
  }
}
