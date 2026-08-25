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
  });
});
