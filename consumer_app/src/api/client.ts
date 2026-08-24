import type { VerificationState } from "../theme";

/**
 * The address of the Bharosa API.
 *
 * On a physical phone `localhost` is the phone itself, so a development build
 * has to name the machine running the backend by its address on the local
 * network. Override it without editing this file by setting
 * EXPO_PUBLIC_API_BASE_URL in `.env`.
 */
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://192.168.1.3:8000/api/v1";

export interface VerifyResult {
  state: VerificationState;
  message: string;
  checked_at: string;
}

export interface ScanLocation {
  longitude: number;
  latitude: number;
  reported_accuracy_m?: number;
}

export class NetworkUnavailableError extends Error {}

const REQUEST_TIMEOUT_MS = 12_000;

/**
 * Verifies one code against the public endpoint.
 *
 * Location is optional and its absence never blocks a check, because a farmer
 * who declines to share where they are is not a suspect. The endpoint answers
 * in the same shape every time, including for codes it cannot resolve, so
 * there is no error branch to model here beyond the network failing.
 */
export async function verify(
  code: string,
  location?: ScanLocation | null,
): Promise<VerifyResult> {
  const trimmed = code.trim();
  const body: Record<string, unknown> = trimmed.includes("://")
    ? { digital_link: trimmed }
    : { serial: trimmed.toUpperCase() };

  if (location) {
    body.longitude = location.longitude;
    body.latitude = location.latitude;
    if (location.reported_accuracy_m != null) {
      body.reported_accuracy_m = Math.round(location.reported_accuracy_m);
    }
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      return {
        state: "UNAVAILABLE",
        message: "We cannot check this code right now. Please try again shortly.",
        checked_at: new Date().toISOString(),
      };
    }
    return (await response.json()) as VerifyResult;
  } catch {
    throw new NetworkUnavailableError(
      "Could not reach the checking service. Check your connection and try again.",
    );
  } finally {
    clearTimeout(timeout);
  }
}
