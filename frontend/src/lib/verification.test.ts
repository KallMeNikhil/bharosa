import { afterEach, describe, expect, it, vi } from "vitest";

import { checkCode, groupSerial, prepareCode } from "./verification";

const SERIAL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".replace(/[01]/g, "2");

describe("prepareCode", () => {
  it("cleans a typed serial the way the consumer app does", () => {
    expect(prepareCode("  abcd efgh\tijkl ")).toEqual({ serial: "ABCDEFGHIJKL", shown: "ABCDEFGHIJKL" });
  });

  it("sends a Digital Link unchanged and shows its serial", () => {
    const link = "https://id.bharosa.example/01/09506000134352/21/A1?bhs=abcd";
    expect(prepareCode(link)).toEqual({ digital_link: link, shown: "ABCD" });
  });
});

describe("groupSerial", () => {
  it("groups a full serial in fours", () => {
    expect(groupSerial(SERIAL)).toBe("ABCD EFGH IJKL MNOP QRST UVWX YZ");
  });
});

describe("checkCode", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("posts the cleaned serial", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ state: "GENUINE", message: "ok", checked_at: "2026-01-01T00:00:00Z" })),
    );
    vi.stubGlobal("fetch", fetchMock);

    await checkCode("abcd efgh");

    const body = JSON.parse((fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1].body as string);
    expect(body).toMatchObject({ serial: "ABCDEFGH", channel: "WEB" });
  });

  it("turns an unreachable service into an UNAVAILABLE result", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));

    const outcome = await checkCode("ABCD");

    expect(outcome.result.state).toBe("UNAVAILABLE");
    expect(outcome.result.message).toMatch(/could not reach/i);
  });

  it("turns a refused request into an UNAVAILABLE result", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 503 })));

    const outcome = await checkCode("ABCD");

    expect(outcome.result.state).toBe("UNAVAILABLE");
  });
});
