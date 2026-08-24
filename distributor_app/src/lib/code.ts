/**
 * Reading the code off a pack.
 *
 * A pack carries a GS1 Digital Link, which is an ordinary https URL, so a
 * scan usually yields a URL rather than a bare serial. The serial travels in
 * the `bhs` extension parameter because it is longer than GS1's own serial
 * component allows.
 *
 * The consumer app sends the whole scanned string to the public endpoint and
 * lets the server pull the serial out. This app cannot: it has to look the
 * serial up as an identity before it can record a movement against it, so
 * extraction happens here and a URL that carries no `bhs` yields nothing
 * rather than a serial-shaped guess.
 */

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

/** The serial a scan resolves to, or null if the code carries none. */
export function readScannedCode(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  if (/^https?:\/\//i.test(trimmed)) return serialFromDigitalLink(trimmed);
  return trimmed.toUpperCase();
}

/**
 * Whether a typed code has the shape of a Bharosa serial.
 *
 * Used only to enable the add button, never to reject a code. A code that
 * looks wrong is still sent if the person insists, because the server decides
 * and a client-side rule that is subtly wrong would strand a whole consignment.
 */
export function looksLikeSerial(value: string): boolean {
  return SERIAL_PATTERN.test(value.trim().toUpperCase());
}

/** Groups a serial into fours so it can be read aloud or compared by eye. */
export function groupSerial(serial: string): string {
  if (!SERIAL_PATTERN.test(serial)) return serial;
  return serial.replace(/(.{4})/g, "$1 ").trim();
}

/** The tail of a serial, which is what distinguishes packs from one batch. */
export function serialTail(serial: string, count = 6): string {
  return serial.slice(-count);
}
