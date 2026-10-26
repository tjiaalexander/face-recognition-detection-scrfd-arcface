import { api } from "./api.js";
import { cameraErrorMessage } from "./camera.js";
import { $, clear, h, sleep, toast } from "./ui.js";

const SAMPLES = 5, MAX_SAMPLES = 10, ID_RE = /^[A-Za-z0-9._-]{1,64}$/;
let ctx, samples = [], busy = false;

export function init(c) {
  ctx = c;
  $("#reg-camera").addEventListener("click", toggleCamera);
  $("#reg-upload-input").onchange = (ev) => {
    addUploadedSamples(ev.target.files);
    ev.target.value = "";
  };
  $("#reg-upload-folder").onchange = (ev) => {
    addUploadedSamples(ev.target.files);
    ev.target.value = "";
  };
  $("#reg-capture").addEventListener("click", capture);
  $("#reg-reset").addEventListener("click", reset);
  $("#reg-form").addEventListener("input", refresh);
  $("#reg-form").addEventListener("submit", submit);
}
export function onHide() { stopCamera(); }

function stopCamera() {
  ctx?.camera.stop(); ctx?.setCamera(false);
  $("#reg-stage").classList.remove("live");
  $("#reg-camera").textContent = "Nyalakan kamera";
  refresh();
}

async function toggleCamera() {
  if (ctx.camera.active) { stopCamera(); return; }
  const video = $("#reg-video");
  try { await ctx.camera.start(video); } catch (e) { toast(cameraErrorMessage(e), "error"); return; }
  $("#reg-stage").style.setProperty("--ar", `${video.videoWidth} / ${video.videoHeight}`);
  $("#reg-stage").classList.add("live");
  $("#reg-camera").textContent = "Matikan kamera";
  ctx.setCamera(true); refresh();
}

function formValues() {
  const f = $("#reg-form");
  return { user_id: f.user_id.value.trim(), name: f.name.value.trim(), consent: f.consent.checked };
}

function refresh() {
  const v = formValues();
  $("#reg-capture").disabled = busy || !ctx.camera.active;
  $("#reg-reset").disabled = busy || samples.length === 0;
  $("#reg-submit").disabled = busy || samples.length < 3 || !ID_RE.test(v.user_id) || !v.name || !v.consent;
}

async function capture() {
  busy = true; refresh(); clear($("#reg-thumbs")); clear($("#reg-report")); samples = [];
  for (let i = 0; i < SAMPLES && ctx.camera.active; i++) {
    const blob = await ctx.camera.capture(960, 0.9);
    if (!blob) break;
    const img = h("img", { src: URL.createObjectURL(blob), alt: `Sampel ${i + 1}` });
    samples.push({ blob, img });
    $("#reg-thumbs").append(img);
    $("#reg-hint").textContent = `Sampel ${i + 1} dari ${SAMPLES}. Ubah sedikit sudut kepala.`;
    await sleep(700);
  }
  $("#reg-hint").textContent = samples.length ? "Sampel siap. Lengkapi data lalu daftarkan." : "Tidak ada sampel yang terambil.";
  busy = false; refresh();
}

function isValidImageFile(file) {
  if (!file || !file.name || file.size <= 0) return false;
  const name = file.name.toLowerCase();
  const type = (file.type || "").toLowerCase();
  const validExt = /\.(jpe?g|png)$/i.test(name);
  const validMime = !type || type.startsWith("image/") || [
    "application/octet-stream",
    "image/pjpeg",
    "image/jpg",
    "image/x-png",
  ].includes(type);
  return validExt && validMime;
}

function addUploadedSamples(fileList) {
  if (!fileList || !fileList.length) return;
  const files = Array.from(fileList).filter(isValidImageFile);
  if (!files.length) {
    toast("Tidak ada gambar JPG/PNG yang valid di pilihan Anda. Coba pilih file secara individu atau pastikan ekstensi file benar.", "error");
    return;
  }
  const remaining = MAX_SAMPLES - samples.length;
  if (remaining <= 0) {
    toast(`Maksimal ${MAX_SAMPLES} sampel. Reset terlebih dahulu.`, "error");
    return;
  }
  const selected = files.slice(0, remaining);
  const added = selected.map((file) => {
    const img = h("img", { src: URL.createObjectURL(file), alt: file.name });
    return { blob: file, img };
  });
  samples.push(...added);
  for (const item of added) $("#reg-thumbs").append(item.img);
  $("#reg-hint").textContent = `Sampel unggah ditambahkan (${samples.length}/${MAX_SAMPLES}). Lengkapi data lalu daftarkan.`;
  refresh();
}

function reset() {
  samples.forEach((s) => URL.revokeObjectURL(s.img.src));
  samples = []; clear($("#reg-thumbs")); clear($("#reg-report"));
  $("#reg-hint").textContent = "Ambil 5 sampel: hadap kamera, lalu sedikit ubah sudut kepala di antaranya.";
  refresh();
}

const toB64 = (blob) => new Promise((res, rej) => {
  const r = new FileReader();
  r.onload = () => res(String(r.result).split(",")[1]);
  r.onerror = () => rej(r.error);
  r.readAsDataURL(blob);
});

function showReports(reports) {
  const list = $("#reg-report");
  clear(list);
  for (const r of reports) {
    list.append(h("li", { class: r.accepted ? "ok" : "bad" }, `Sampel ${r.index + 1}: ${r.accepted ? "diterima" : "ditolak, " + r.messages.join(" ")}`));
    const img = samples[r.index]?.img;
    if (img) img.className = r.accepted ? "ok" : "bad";
  }
}

async function submit(ev) {
  ev.preventDefault();
  if ($("#reg-submit").disabled) return;
  busy = true; refresh();
  try {
    const frames = await Promise.all(samples.map((s) => toB64(s.blob)));
    const res = await api("/api/users/register", { method: "POST", body: { ...formValues(), frames } });
    showReports(res.reports);
    toast(`${res.user.name} terdaftar dengan ${res.accepted_samples} template.`, "ok");
    $("#reg-form").reset(); samples = []; clear($("#reg-thumbs"));
    $("#reg-hint").textContent = "Registrasi selesai. Ambil sampel baru untuk pengguna berikutnya.";
  } catch (e) {
    if (e.detail?.reports) showReports(e.detail.reports);
    toast(e.message, "error", 7000);
  } finally { busy = false; refresh(); }
}
