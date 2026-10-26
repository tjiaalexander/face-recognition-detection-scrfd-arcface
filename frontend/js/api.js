const KEY = "frs.token";
let token = sessionStorage.getItem(KEY);   // hilang saat tab ditutup

export const auth = {
  get token() { return token; },
  set(t) { token = t; sessionStorage.setItem(KEY, t); },
  clear() { token = null; sessionStorage.removeItem(KEY); },
};

export class ApiError extends Error {
  constructor(status, code, message, detail) { super(message); this.status = status; this.code = code; this.detail = detail; }
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(path, { method, headers, cache: "no-store", body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError(0, "network", "Tidak dapat terhubung ke backend. Pastikan server berjalan.");
  }
  const data = await res.json().catch(() => null);
  if (res.status === 401 && token && !path.startsWith("/api/auth/login")) {
    auth.clear();
    window.dispatchEvent(new Event("auth:expired"));
  }
  if (!res.ok) {
    const d = data?.detail;
    let code = "error", message = `Permintaan gagal (${res.status}).`;
    if (d && typeof d === "object" && !Array.isArray(d)) { code = d.code || code; message = d.message || message; }
    else if (typeof d === "string") message = d;
    else if (Array.isArray(d)) { code = "validation"; message = "Data yang dikirim tidak valid. Periksa ID (huruf, angka, titik, strip) dan nama."; }
    throw new ApiError(res.status, code, message, d);
  }
  return data;
}
