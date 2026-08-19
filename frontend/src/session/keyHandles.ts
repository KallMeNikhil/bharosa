const STORAGE_KEY = "bharosa.keyHandles";

/**
 * A key handle is what the signer hands back when a key is issued, and it is
 * the only way to sign with that key afterwards. A real deployment would keep
 * it in a secrets store; a development console keeps it here so that issuing
 * a key and signing with it can happen on two different screens.
 */
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
