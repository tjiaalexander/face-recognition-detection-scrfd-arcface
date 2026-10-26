export const $ = (sel, root = document) => root.querySelector(sel);

export function clear(node) {
  if (!node) return;
  while (node.firstChild) node.removeChild(node.firstChild);
}

/** Buat elemen DOM tanpa innerHTML (aman dari XSS untuk data pengguna). */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return el;
}

export function toast(message, kind = "info", ms = 4500) {
  const el = h("div", { class: `toast ${kind}`, role: "status" }, message);
  $("#toasts").append(el);
  setTimeout(() => el.remove(), ms);
}

export function fmtDate(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
