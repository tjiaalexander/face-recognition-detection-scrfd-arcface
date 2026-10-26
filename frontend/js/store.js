export const recent = [];
export function addRecent(entry) {
  recent.unshift({ ...entry, time: new Date() });
  recent.length = Math.min(recent.length, 12);
  window.dispatchEvent(new Event("recent:update"));
}
