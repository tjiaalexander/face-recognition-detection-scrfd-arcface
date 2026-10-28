import { api } from "./api.js";
import { $, clear, fmtDate, h, toast } from "./ui.js";

const PAGE_SIZE = 10;
let page = 1, search = "", total = 0, timer = null;

export function init() {
  $("#user-search").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { search = e.target.value; page = 1; load(); }, 300);
  });
  $("#user-prev").addEventListener("click", () => { if (page > 1) { page--; load(); } });
  $("#user-next").addEventListener("click", () => { if 
    (page * PAGE_SIZE < total) { page++; load(); } });
}
export function onShow() { load(); }
export function onHide() {}

async function load() {
  try {
    const q = new URLSearchParams({ search, page, page_size: PAGE_SIZE });
    const res = await api(`/api/users?${q}`);
    total = res.total;
    render(res.items);
  } catch (e) { toast(e.message, "error"); }
}

function render(items) {
  const body = $("#user-rows");
  clear(body);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  $("#user-count").textContent = `${total} pengguna`;
  $("#user-page").textContent = `Halaman ${page} dari ${pages}`;
  $("#user-prev").disabled = page <= 1; $("#user-next").disabled = page >= pages;
  const empty = $("#user-empty");
  empty.hidden = items.length > 0;
  empty.textContent = search ? `Tidak ada pengguna yang cocok dengan "${search}".` : "Belum ada pengguna. Daftarkan wajah pertama di menu Registrasi Wajah.";
  for (const u of items) {
    body.append(h("tr", {},
      h("td", {}, u.user_id), h("td", {}, u.name), h("td", { class: "num" }, u.template_count), h("td", {}, fmtDate(u.created_at)),
      h("td", { class: "row-actions" },
        h("button", { class: "btn", onclick: () => showDetail(u) }, "Detail"),
        h("button", { class: "btn danger", onclick: () => remove(u) }, "Hapus"))));
  }
}

async function showDetail(u) {
  let user = u;
  try { user = await api(`/api/users/${encodeURIComponent(u.user_id)}`); } catch (e) { toast(e.message, "error"); return; }
  const dl = $("#detail-body");
  clear(dl);
  for (const [k, v] of [["ID", user.user_id], ["Nama", user.name], ["Template wajah", user.template_count],
    ["Terdaftar", fmtDate(user.created_at)], ["Persetujuan dicatat", fmtDate(user.consent_at)]]) {
    dl.append(h("div", {}, h("dt", {}, k), h("dd", {}, v)));
  }
  $("#dlg-detail").showModal();
}

function confirmDelete(u) {
  return new Promise((resolve) => {
    const dlg = $("#dlg-delete");
    $("#delete-text").textContent = `${u.name} (${u.user_id}) dan ${u.template_count} template wajahnya akan dihapus permanen. Tindakan ini tidak dapat dibatalkan.`;
    dlg.returnValue = "";
    dlg.addEventListener("close", () => resolve(dlg.returnValue === "confirm"), { once: true });
    dlg.showModal();
  });
}

async function remove(u) {
  if (!(await confirmDelete(u))) return;
  try {
    const r = await api(`/api/users/${encodeURIComponent(u.user_id)}`, { method: "DELETE" });
    toast(`${u.name} dihapus (${r.deleted_templates} template).`, "ok");
    if (page > 1 && $("#user-rows").children.length === 1) page--;
    load();
  } catch (e) { toast(e.message, "error"); }
}
