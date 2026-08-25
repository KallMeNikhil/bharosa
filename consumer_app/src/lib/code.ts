const BHAROSA_SERIAL_PARAM = "bhs";
const SERIAL_PATTERN = /^[A-Z2-7]{26}$/;

export interface ScannedCode {
  payload: string;
  serial: string;
}

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

export function readScannedCode(raw: string): ScannedCode {
  const payload = raw.trim();
  if (/^https?:\/\//i.test(payload)) {
    return { payload, serial: serialFromDigitalLink(payload) ?? payload };
  }
  return { payload: payload.toUpperCase(), serial: payload.toUpperCase() };
}

export function looksLikeSerial(value: string): boolean {
  return SERIAL_PATTERN.test(value.trim().toUpperCase());
}

export function groupSerial(serial: string): string {
  if (!SERIAL_PATTERN.test(serial)) return serial;
  return serial.replace(/(.{4})/g, "$1 ").trim();
}
