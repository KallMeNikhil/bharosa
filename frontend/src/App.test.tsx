import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

async function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
  await act(async () => undefined);
}

describe("App", () => {
  it("renders the public marketing home page at the root", async () => {
    await renderAt("/");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "A valid code can be copied.",
    );
    expect(screen.queryByText("Signing keys")).not.toBeInTheDocument();
  });

  it("serves the public verify journey", async () => {
    await renderAt("/verify");
    expect(screen.getByRole("heading", { name: "Check the pack in your hand" })).toBeInTheDocument();
    expect(screen.queryByText("Signing keys")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated workspace visits to sign in", async () => {
    await renderAt("/app");
    expect(screen.getByRole("heading", { name: "Sign in to your workspace" })).toBeInTheDocument();
  });

  it("still serves the internal dev/test console under /dev", async () => {
    await renderAt("/dev");
    expect(screen.getByText("internal test console")).toBeInTheDocument();
    expect(screen.getByText("Tenant & actor")).toBeInTheDocument();
  });

  describe("with a configured session", () => {
    afterEach(() => {
      vi.unstubAllGlobals();
      window.localStorage.clear();
    });

    it("renders the Workspace Overview instead of redirecting to sign in", async () => {
      window.localStorage.setItem(
        "bharosa.session",
        JSON.stringify({
          manufacturerId: "mfr-1",
          manufacturerName: "Kisan Crop Sciences",
          actorId: "operator",
          capabilities: [],
        }),
      );
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => new Response(JSON.stringify([]), { status: 200 })),
      );

      await renderAt("/app");
      expect(screen.getAllByText("Kisan Crop Sciences").length).toBeGreaterThan(0);
      expect(screen.getAllByRole("link", { name: "Products" }).length).toBeGreaterThan(0);
    });
  });

  describe("the public verify journey", () => {
    afterEach(() => {
      vi.unstubAllGlobals();
    });

    it("submits a code and shows a plain-language result with no internal detail", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () =>
          new Response(
            JSON.stringify({ state: "GENUINE", message: "ok", checked_at: new Date().toISOString() }),
            { status: 200 },
          ),
        ),
      );

      render(
        <MemoryRouter initialEntries={["/verify"]}>
          <App />
        </MemoryRouter>,
      );

      fireEvent.change(screen.getByPlaceholderText(/code from the pack/i), {
        target: { value: "ABC123" },
      });
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: "Check this product" }));
      });

      expect(await screen.findByRole("heading", { name: "Registered" })).toBeInTheDocument();
      expect(screen.queryByText(/risk score|detector|confidence/i)).not.toBeInTheDocument();
    });

    it("checks a printed Digital Link opened from a phone camera", async () => {
      const fetchMock = vi.fn(async () =>
        new Response(
          JSON.stringify({ state: "CAUTION", message: "look closer", checked_at: new Date().toISOString() }),
          { status: 200 },
        ),
      );
      vi.stubGlobal("fetch", fetchMock);

      await renderAt("/01/09506000134352/21/A1?bhs=abcd");

      expect(await screen.findByRole("heading", { name: "Check first" })).toBeInTheDocument();
      const body = JSON.parse((fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1].body as string);
      expect(body.digital_link).toContain("/01/09506000134352/21/A1?bhs=abcd");
    });
  });

  describe("accounts", () => {
    afterEach(() => {
      vi.unstubAllGlobals();
      window.localStorage.clear();
    });

    const sessionView = {
      token: "bt_test",
      expires_at: new Date(Date.now() + 86_400_000).toISOString(),
      account: { id: "a-1", email: "owner@example.com", display_name: null, role: "OWNER" },
      manufacturer: { id: "mfr-1", name: "Kisan Crop Sciences", status: "ACTIVE", created_at: "" },
    };

    function stubApi() {
      const calls: { url: string; init?: RequestInit }[] = [];
      vi.stubGlobal(
        "fetch",
        vi.fn(async (url: string, init?: RequestInit) => {
          calls.push({ url, init });
          if (url.includes("/auth/")) return new Response(JSON.stringify(sessionView), { status: 200 });
          if (url.endsWith("/me")) {
            return new Response(
              JSON.stringify({ actor_id: "owner@example.com", manufacturer_id: "mfr-1", capabilities: ["MANAGE_KEYS"] }),
              { status: 200 },
            );
          }
          return new Response(JSON.stringify([]), { status: 200 });
        }),
      );
      return calls;
    }

    it("signs in with an email and password and keeps the session token", async () => {
      const calls = stubApi();
      await renderAt("/app/login");

      fireEvent.change(screen.getByPlaceholderText("you@company.com"), { target: { value: "owner@example.com" } });
      fireEvent.change(document.querySelector('input[type="password"]') as HTMLInputElement, {
        target: { value: "correct horse 42" },
      });
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
      });

      expect(await screen.findAllByText("Kisan Crop Sciences")).not.toHaveLength(0);
      expect(calls.some((call) => call.url.endsWith("/auth/sign-in"))).toBe(true);
      const stored = JSON.parse(window.localStorage.getItem("bharosa.session") ?? "{}");
      expect(stored.token).toBe("bt_test");
      const workspaceCall = calls.find((call) => call.url.includes("/products"));
      expect((workspaceCall?.init?.headers as Record<string, string>).Authorization).toBe("Bearer bt_test");
    });

    it("offers registration from the sign-in page", async () => {
      await renderAt("/app/register");
      expect(screen.getByRole("heading", { name: "Create your company's account" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Create account" })).toBeDisabled();
    });
  });
});
