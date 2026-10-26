import { api, auth } from "./api.js";
import { Camera } from "./camera.js";
import * as dashboard from "./dashboard.js";
import * as recognition from "./recognition.js";
import * as register from "./register.js";
import * as users from "./users.js";
import { $, toast } from "./ui.js";

const PAGES = {
  dashboard: { mod: dashboard, title: "Dashboard" },
  recognition: { mod: recognition, title: "Face Recognition" },
  register: { mod: register, title: "Registrasi Wajah" },
  users: { mod: users, title: "Database Pengguna" },
};
let current = null, healthTimer = null, live = false;

async function loadModelOptions() {
  try {
    const res = await api("/api/system/models");
    const select = document.getElementById("model-select");
    if (!select) return;
    select.innerHTML = "";
    if (!Array.isArray(res.models) || res.models.length === 0) {
      const opt = document.createElement("option");
      opt.value = res.current || "antelopev2";
      opt.textContent = `${opt.value} (belum terpasang)`;
      select.appendChild(opt);
      select.disabled = true;
      return;
    }
    select.disabled = false;
    for (const model of res.models) {
      const opt = document.createElement("option");
      opt.value = model;
      opt.textContent = model;
      opt.selected = model === res.current;
      select.appendChild(opt);
    }
    select.onchange = async () => {
      try {
        const updated = await api("/api/system/model", { method: "POST", body: { model: select.value } });
        setPill("#pill-backend", "ok", `Model aktif: ${updated.current}`);
      } catch (e) {
        toast(e.message, "error");
        const currentModel = await api("/api/system/models");
        select.value = currentModel.current;
      }
    };
  } catch (e) {
    console.warn("Gagal memuat model selector", e);
  }
}

function setPill(id, state, text) {
  const el = $(id);
  el.className = `pill ${state}`;
  el.lastElementChild.textContent = text;
}

const ctx = {
  camera: new Camera(),
  toast,
  setCamera(active) { setPill("#pill-camera", active ? "ok" : "", active ? "Kamera aktif" : "Kamera mati"); },
  setLive(v) { live = v; },
};

function show(name) {
  if (current) PAGES[current].mod.onHide?.();
  current = name;
  for (const [key, p] of Object.entries(PAGES)) $(`#page-${key}`).hidden = key !== name;
  document.querySelectorAll(".nav-item[data-page]").forEach((b) => b.classList.toggle("active", b.dataset.page === name));
  $("#page-title").textContent = PAGES[name].title;
  PAGES[name].mod.onShow?.();
}

async function checkHealth() {
  try {
    const h = await api("/api/health");
    setPill("#pill-backend", h.model_loaded ? "ok" : "warn", h.model_loaded ? "Backend siap" : "Backend aktif, model belum dimuat");
  } catch {
    setPill("#pill-backend", "bad", "Backend tidak terhubung");
  }
}

function showApp() {
  $("#login-screen").hidden = true; $("#app").hidden = false;
  checkHealth();
  loadModelOptions();
  healthTimer = setInterval(checkHealth, 8000);
  show("dashboard");
}

function showLogin(message) {
  clearInterval(healthTimer);
  if (current) { PAGES[current].mod.onHide?.(); current = null; }
  $("#app").hidden = true; $("#login-screen").hidden = false;
  const err = $("#login-error");
  err.hidden = !message; err.textContent = message || "";
}

function init() {
  for (const p of Object.values(PAGES)) p.mod.init?.(ctx);
  document.querySelectorAll(".nav-item[data-page]").forEach((b) => b.addEventListener("click", () => show(b.dataset.page)));
  $("#logout").addEventListener("click", () => { auth.clear(); showLogin(); });
  window.addEventListener("auth:expired", () => showLogin("Sesi berakhir. Silakan login lagi."));
  $("#login-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = ev.target;
    try {
      const res = await api("/api/auth/login", { method: "POST", body: { username: f.username.value, password: f.password.value } });
      auth.set(res.access_token); f.password.value = ""; showApp();
    } catch (e) { showLogin(e.message); }
  });
  if (auth.token) api("/api/auth/me").then(showApp).catch(() => showLogin()); else showLogin();
}

init();
