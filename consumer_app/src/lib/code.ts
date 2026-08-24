/**
 * Reading the code off a pack.
 *
 * A pack carries a GS1 Digital Link, which is an ordinary https URL, so a
 * scan usually yields a URL rather than a bare serial. The serial travels in
 * the `bhs` extension parameter because it is longer than GS1's own serial
 * component allows.
 *
 * Nothing here decides whether a code is genuine. It only works out what to
 * show the person and what to send. The server is the only authority on
 * whether a code resolves.
 */

const BHAROSA_SERIAL_PARAM = "bhs";
const SERIAL_PATTERN = /^[A-Z2-7]{26}$/;

export interface ScannedCode {
  /** Sent to the API verbatim: either a URL or a bare serial. */
  payload: string;
  /** Shown to the person, and stored in their history. */
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

/**
 * Whether a typed code has the shape of a Bharosa serial.
 *
 * Used only to enable the check button, never to reject a code. A code that
 * looks wrong still gets sent if the person insists, because the server
 * decides and a client-side rule that is subtly wrong would strand them.
 */
export function looksLikeSerial(value: string): boolean {
  return SERIAL_PATTERN.test(value.trim().toUpperCase());
}

/** Groups a serial into fours so it can be read aloud or compared by eye. */
export function groupSerial(serial: string): string {
  if (!SERIAL_PATTERN.test(serial)) return serial;
  return serial.replace(/(.{4})/g, "$1 ").trim();
}
