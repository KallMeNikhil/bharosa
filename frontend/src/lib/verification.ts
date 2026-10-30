// The public check, kept in step with the consumer app (consumer_app/src/lib/code.ts,
// consumer_app/src/api/client.ts and consumer_app/src/theme.ts) so that the same pack
// reads the same way whichever surface checked it.

import { ApiError } from "../api/client";
import { publicSurface } from "../api/endpoints";
import type { VerificationState, VerifyResponse } from "../api/types";

const SERIAL_PATTERN = /^[A-Z2-7]{26}$/;
const BHAROSA_SERIAL_PARAM = "bhs";

export interface PreparedCode {
  serial?: string;
  digital_link?: string;
  // What the result screen shows as "Code checked".
  shown: string;
}

// A Digital Link goes to the server as scanned. Anything else is a typed serial, which
// the server compares exactly, so spacing and case are removed here as the app does.
export function prepareCode(raw: string): PreparedCode {
  const payload = raw.trim();
  if (/^https?:\/\//i.test(payload)) {
    return { digital_link: payload, shown: serialFromDigitalLink(payload) ?? payload };
  }
  const serial = payload.replace(/\s+/g, "").toUpperCase();
  return { serial, shown: serial };
}

function serialFromDigitalLink(uri: string): string | null {
  try {
    const value = new URL(uri).searchParams.get(BHAROSA_SERIAL_PARAM);
    return value ? value.toUpperCase() : null;
  } catch {
    return null;
  }
}

export function looksLikeSerial(value: string): boolean {
  return SERIAL_PATTERN.test(value.replace(/\s+/g, "").toUpperCase());
}

export function groupSerial(serial: string): string {
  if (!SERIAL_PATTERN.test(serial)) return serial;
  return serial.replace(/(.{4})/g, "$1 ").trim();
}

export interface StatePresentation {
  verdict: string;
  action: string;
}

export const STATE_PRESENTATION: Record<VerificationState, StatePresentation> = {
  GENUINE: {
    verdict: "Registered",
    action: "Nothing unusual in this pack's recent history.",
  },
  CAUTION: {
    verdict: "Check first",
    action: "Call the manufacturer's support line before you use this.",
  },
  INVALID: {
    verdict: "Not confirmed",
    action: "Call the manufacturer's support line before you use this.",
  },
  ALREADY_REPORTED: {
    verdict: "Reported",
    action: "Someone has already raised this pack with the manufacturer.",
  },
  UNAVAILABLE: {
    verdict: "No answer",
    action: "We could not reach the checking service. Try again shortly.",
  },
};

const UNREACHABLE_MESSAGE =
  "Could not reach the checking service. Check your connection and try again.";
const REFUSED_MESSAGE = "We cannot check this code right now. Please try again shortly.";
const MAX_REPORTED_ACCURACY_M = 100_000;

export interface CheckOutcome {
  result: VerifyResponse;
  shown: string;
}

async function currentLocation(): Promise<GeolocationPosition | null> {
  if (!navigator.geolocation) return null;
  try {
    return await new Promise<GeolocationPosition>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 2500 });
    });
  } catch {
    return null;
  }
}

// Never throws. A failed request becomes an UNAVAILABLE result, as it does in the app,
// rather than a developer-facing error on a public page.
export async function checkCode(raw: string): Promise<CheckOutcome> {
  const prepared = prepareCode(raw);
  const position = await currentLocation();

  try {
    const result = await publicSurface.verify({
      ...(prepared.digital_link ? { digital_link: prepared.digital_link } : { serial: prepared.serial }),
      ...(position
        ? {
            longitude: position.coords.longitude,
            latitude: position.coords.latitude,
            reported_accuracy_m: Math.min(
              Math.round(position.coords.accuracy),
              MAX_REPORTED_ACCURACY_M,
            ),
          }
        : {}),
      channel: "WEB",
    });
    return { result, shown: prepared.shown };
  } catch (cause) {
    const unreachable = cause instanceof ApiError && cause.status === 0;
    return {
      result: {
        state: "UNAVAILABLE",
        message: unreachable ? UNREACHABLE_MESSAGE : REFUSED_MESSAGE,
        checked_at: new Date().toISOString(),
      },
      shown: prepared.shown,
    };
  }
}
