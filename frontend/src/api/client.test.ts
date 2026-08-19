import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, clearLog, readLog, request, setCredential } from "./client";

function respondWith(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  clearLog();
  setCredential(null);
});

describe("request", () => {
  it("sends the credential as a bearer token and logs the exchange", async () => {
    respondWith(200, { status: "ok" });
    setCredential("dev:abc:alice:*");

    await request("/health");

    const [call] = vi.mocked(fetch).mock.calls;
    expect(call[0]).toBe("/api/v1/health");
    expect((call[1]?.headers as Record<string, string>).Authorization).toBe(
      "Bearer dev:abc:alice:*",
    );
    expect(readLog()[0].path).toBe("/api/v1/health");
  });

  it("omits the credential from the public surface", async () => {
    respondWith(200, { state: "INVALID" });
    setCredential("dev:abc:alice:*");

    await request("/verify", { method: "POST", body: { serial: "x" }, anonymous: true });

    const [call] = vi.mocked(fetch).mock.calls;
    expect((call[1]?.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it("surfaces the server's detail on failure", async () => {
    respondWith(403, { detail: "Actor does not hold MANAGE_KEYS." });

    await expect(request("/keys", { method: "POST", body: {} })).rejects.toThrow(ApiError);
    expect(readLog()[0].ok).toBe(false);
  });
});
