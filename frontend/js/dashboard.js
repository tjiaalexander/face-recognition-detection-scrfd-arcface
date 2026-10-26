import { api } from "./api.js";
import { $, clear, fmtDate, h } from "./ui.js";
import { recent } from "./store.js";

let ctx;

export function init(c) {
  ctx = c;
  window.addEventListener("recent:update", renderRecent);
}

export async function onShow() {
  renderRecent();
  try {
    const s = await api("/api/stats");
    $("#stat-users").textContent = s.users;
    $("#stat-templates").textContent = s.templates;
    $("#stat-model").textContent = s.model;
    $("#stat-threshold").textContent = s.threshold.toFixed(2);
    $("#stat-threshold-note").textContent = s.threshold_calibrated ? "Threshold (dikalibrasi)" : "Threshold (belum dikalibrasi)";
    const rows = [
      ["Backend", "Terhubung", "ok"],
      ["Model", s.model_loaded ? "Dimuat" : (s.model_error || "Belum dimuat"), s.model_loaded ? "ok" : "bad"],
      ["Akselerasi", s.providers.join(", ") || "–", "ok"],
      ["Kamera", ctx.camera.active ? "Aktif" : "Mati", ctx.camera.active ? "ok" : "warn"],
      ["Threshold", s.threshold_calibrated ? "Sudah dikalibrasi" : "Belum dikalibrasi (nilai awal)", s.threshold_calibrated ? "ok" : "warn"],
      ["Liveness", s.liveness === "not_configured" ? "Belum dikonfigurasi" : s.liveness, s.liveness === "not_configured" ? "warn" : "ok"],
    ];
    if (s.templates_other_model) rows.push(["Template model lain", `${s.templates_other_model} (tidak dipakai)`, "warn"]);
    if (s.templates_undecryptable) rows.push(["Template tak terbaca", String(s.templates_undecryptable), "bad"]);
    const list = $("#status-list");
    clear(list);
    for (const [k, v, cls] of rows) list.append(h("div", {}, h("dt", {}, k), h("dd", { class: cls }, v)));
  } catch (e) {
    ctx.toast(e.message, "error");
  }
}

function renderRecent() {
  const list = $("#recent-list");
  clear(list);
  $("#recent-empty").hidden = recent.length > 0;
  for (const r of recent) {
    list.append(h("li", {}, h("strong", {}, r.name || r.user_id), h("span", { class: "score" }, r.score.toFixed(2)),
      h("small", {}, `${r.user_id} · ${fmtDate(r.time)}`)));
  }
}
