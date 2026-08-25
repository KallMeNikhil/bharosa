const BHAROSA_SERIAL_PARAM = "bhs";
const SERIAL_PATTERN = /^[A-Z2-7]{26}$/;

function serialFromDigitalLink(uri: string): string | null {
  const query = uri.split("?")[1];
  if (!query) return null;
  for (const pair of query.split("&")) {
    const [key, value] = pair.split("=");
    if (key === BHAROSA_SERIAL_PARAM && value) {
      return decodeURIComponent(value).toUpperCase();
    }
  }
  return null;
}

export function readScannedCode(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  if (/^https?:\/\//i.test(trimmed)) return serialFromDigitalLink(trimmed);
  return trimmed.toUpperCase();
}

export function looksLikeSerial(value: string): boolean {
  return SERIAL_PATTERN.test(value.trim().toUpperCase());
}

export function groupSerial(serial: string): string {
  if (!SERIAL_PATTERN.test(serial)) return serial;
  return serial.replace(/(.{4})/g, "$1 ").trim();
}

export function serialTail(serial: string, count = 6): string {
  return serial.slice(-count);
}
