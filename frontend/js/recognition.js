import { auth } from "./api.js";
import { cameraErrorMessage } from "./camera.js";
import { addRecent } from "./store.js";
import { $, clear, h, toast } from "./ui.js";

const COLORS = { confirmed: "#1b7f4b", tentative: "#c98a1a", unknown: "#b23a3a", low_quality: "#7d8a94" };
let ctx, ws = null, running = false, ready = false, inflight = false, sentAt = 0, frameId = 0;
let retry = 0, loopTimer = null, lastResultAt = 0, fps = 0, lastErrorToast = 0;
const seen = new Set();

export function init(c) {
  ctx = c;
  $("#rec-start").addEventListener("click", start);
  $("#rec-stop").addEventListener("click", () => stop());
}
export function onHide() { stop(); }

const setConn = (text) => { $("#rec-conn").textContent = text; };

async function start() {
  if (running) return;
  const video = $("#rec-video");
  try { await ctx.camera.start(video); } catch (e) { toast(cameraErrorMessage(e), "error"); return; }
  $("#rec-stage").style.setProperty("--ar", `${video.videoWidth} / ${video.videoHeight}`);
  $("#rec-stage").classList.add("live");
  running = true; retry = 0;
  ctx.setCamera(true);
  $("#rec-start").hidden = true; $("#rec-stop").hidden = false;
  connect();
  loop();
}

function stop() {
  running = false; ready = false; inflight = false;
  clearTimeout(loopTimer);
  if (ws) { ws.onclose = null; ws.close(); ws = null; }
  ctx?.camera.stop();
  ctx?.setCamera(false);
  $("#rec-stage").classList.remove("live");
  $("#rec-start").hidden = false; $("#rec-stop").hidden = true;
  clearOverlay(); renderFaces([]);
  setConn("Terputus"); ctx?.setLive(false);
}

function connect() {
  const sock = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/recognize`);
  sock.binaryType = "arraybuffer";
  ws = sock; ready = false; seen.clear();
  setConn("Menyambung…");
  sock.onopen = () => sock.send(JSON.stringify({ type: "auth", token: auth.token }));
  sock.onmessage = (ev) => handle(JSON.parse(ev.data));
  sock.onclose = (ev) => {
    if (sock !== ws || !running) return;
    ready = false; inflight = false; ctx.setLive(false);
    if (ev.code === 4401) {
      toast("Sesi berakhir. Silakan login ulang.", "error"); stop();
      window.dispatchEvent(new Event("auth:expired")); return;
    }
    setConn("Terputus, mencoba lagi…");
    setTimeout(() => { if (running && sock === ws) connect(); }, Math.min(10000, 1000 * 2 ** retry++));
  };
}

function handle(m) {
  if (m.type === "ready") {
    ready = true; retry = 0; setConn("Terhubung"); ctx.setLive(true);
    $("#rec-threshold").textContent = `${m.threshold.toFixed(2)}${m.threshold_calibrated ? "" : " (belum dikalibrasi)"}`;
  } else if (m.type === "result") {
    inflight = false;
    const now = performance.now();
    if (lastResultAt) fps = fps ? 0.8 * fps + 0.2 * (1000 / (now - lastResultAt)) : 1000 / (now - lastResultAt);
    lastResultAt = now;
    $("#rec-latency").textContent = `${m.latency_ms} ms`;
    $("#rec-fps").textContent = fps.toFixed(1);
    draw(m); renderFaces(m.faces);
    for (const f of m.faces) {
      const key = `${f.track_id}:${f.user_id}`;
      if (f.status === "confirmed" && !seen.has(key)) { seen.add(key); addRecent({ user_id: f.user_id, name: f.name, score: f.score }); }
    }
  } else if (m.type === "error") {
    inflight = false;
    if (m.code === "model_unavailable") { toast(m.message, "error"); stop(); return; }
    if (Date.now() - lastErrorToast > 5000) { lastErrorToast = Date.now(); toast(m.message, "error"); }
  }
}

function loop() {
  if (!running) return;
  if (ready && ws?.readyState === WebSocket.OPEN && (!inflight || performance.now() - sentAt > 2500)) sendFrame();
  loopTimer = setTimeout(loop, 100);
}

async function sendFrame() {
  inflight = true; sentAt = performance.now();
  try {
    const blob = await ctx.camera.capture(640, 0.7);
    if (!blob) { inflight = false; return; }
    const body = new Uint8Array(await blob.arrayBuffer());
    const buf = new Uint8Array(4 + body.length);
    new DataView(buf.buffer).setUint32(0, ++frameId >>> 0);
    buf.set(body, 4);
    if (ws?.readyState === WebSocket.OPEN) ws.send(buf); else inflight = false;
  } catch { inflight = false; }
}

// ---- tampilan ----
function labelFor(f) {
  const s = f.score == null ? "" : ` ${f.score.toFixed(2)}`;
  if (f.status === "confirmed") return `${f.name}${s}`;
  if (f.status === "tentative") return `Mencocokkan: ${f.name}${s}`;
  if (f.status === "unknown") return `Unknown${s}`;
  return f.quality.messages[0] || "Kualitas kurang";
}

function clearOverlay() {
  const c = $("#rec-overlay"); c.getContext("2d").clearRect(0, 0, c.width, c.height);
}

function draw(m) {
  const canvas = $("#rec-overlay"), rect = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(rect.width * dpr); canvas.height = Math.round(rect.height * dpr);
  const g = canvas.getContext("2d");
  g.scale(dpr, dpr);
  const sx = rect.width / m.width, sy = rect.height / m.height;
  g.font = "600 13px 'Segoe UI', system-ui, sans-serif"; g.textBaseline = "middle";
  for (const f of m.faces) {
    // video ditampilkan mirror, jadi koordinat x dibalik di sini agar teks tidak ikut terbalik
    const l = rect.width - f.bbox[2] * sx, r = rect.width - f.bbox[0] * sx, t = f.bbox[1] * sy, b = f.bbox[3] * sy;
    const color = COLORS[f.status] || COLORS.low_quality;
    const len = Math.max(12, Math.min(r - l, b - t) * 0.22);
    g.strokeStyle = color; g.lineWidth = 3; g.lineCap = "square"; g.beginPath();
    for (const [x, y, dx, dy] of [[l, t, 1, 1], [r, t, -1, 1], [l, b, 1, -1], [r, b, -1, -1]]) {
      g.moveTo(x + dx * len, y); g.lineTo(x, y); g.lineTo(x, y + dy * len);
    }
    g.stroke();
    const text = labelFor(f), w = g.measureText(text).width + 14, ty = t > 28 ? t - 26 : b + 4;
    g.fillStyle = color; g.fillRect(l, ty, w, 22);
    g.fillStyle = "#fff"; g.fillText(text, l + 7, ty + 11.5);
  }
}

function renderFaces(faces) {
  const list = $("#rec-faces");
  clear(list);
  $("#rec-faces-empty").hidden = faces.length > 0;
  for (const f of faces) {
    const title = f.status === "confirmed" ? f.name : f.status === "tentative" ? `Kemungkinan ${f.name}` : f.status === "unknown" ? "Unknown" : "Kualitas kurang";
    const note = f.status === "confirmed" ? `Terkonfirmasi (${f.votes} frame konsisten) · ID ${f.user_id}`
      : f.status === "tentative" ? "Menunggu beberapa frame konsisten"
      : f.status === "unknown" ? "Di bawah threshold"
      : f.quality.messages.join(" ");
    list.append(h("li", { class: f.status }, h("strong", {}, title), h("span", { class: "score" }, f.score == null ? "" : f.score.toFixed(2)), h("small", {}, note)));
  }
}
