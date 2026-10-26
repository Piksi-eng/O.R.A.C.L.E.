// localStorage can be missing or throw (private mode, blocked site data), so the app works without it.

export function load(key: string, fallback = ""): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

export function save(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* not persisted, fine */
  }
}

/** A stable id per phone, so a reconnect is the same player rather than a new one. */
export function playerId(): string {
  let id = load("dmc.playerId");
  if (!id) {
    id = Array.from(crypto.getRandomValues(new Uint8Array(8)), (b) => b.toString(16).padStart(2, "0")).join("");
    save("dmc.playerId", id);
  }
  return id;
}
