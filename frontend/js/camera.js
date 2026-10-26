export class Camera {
  constructor() { this.stream = null; this.video = null; }
  get active() { return !!this.stream; }

  /** Dipanggil hanya setelah klik pengguna; browser meminta izin kamera di sini. */
  async start(video) {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("UNSUPPORTED");
    }
    this.stop();
    this.stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" }, audio: false,
    });
    this.video = video;
    video.srcObject = this.stream;
    await video.play();
  }

  stop() {
    this.stream?.getTracks().forEach((t) => t.stop());
    if (this.video) this.video.srcObject = null;
    this.stream = null;
  }

  /** Ambil satu frame JPEG (tidak dimirror) dengan sisi terpanjang <= maxSide. */
  capture(maxSide = 640, quality = 0.8) {
    const v = this.video;
    if (!v || !v.videoWidth) return Promise.resolve(null);
    const scale = Math.min(1, maxSide / Math.max(v.videoWidth, v.videoHeight));
    const c = document.createElement("canvas");
    c.width = Math.round(v.videoWidth * scale);
    c.height = Math.round(v.videoHeight * scale);
    c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
    return new Promise((resolve) => c.toBlob(resolve, "image/jpeg", quality));
  }
}

export function cameraErrorMessage(err) {
  switch (err?.name || err?.message) {
    case "NotAllowedError": return "Izin kamera ditolak. Izinkan kamera di pengaturan browser, lalu coba lagi.";
    case "NotFoundError": return "Kamera tidak ditemukan.";
    case "NotReadableError": return "Kamera sedang dipakai aplikasi lain.";
    case "UNSUPPORTED": return "Browser tidak mendukung kamera, atau halaman tidak dibuka lewat localhost/HTTPS.";
    default: return `Kamera gagal dinyalakan: ${err?.message || err}`;
  }
}
