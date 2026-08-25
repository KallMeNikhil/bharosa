const STORAGE_KEY = "bharosa.keyHandles";

function readAll(): Record<string, string> {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, string>) : {};
  } catch {
    return {};
  }
}

export function rememberKeyHandle(keyId: string, handle: string): void {
  const all = readAll();
  all[keyId] = handle;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}

export function recallKeyHandle(keyId: string): string {
  return readAll()[keyId] ?? "";
}
