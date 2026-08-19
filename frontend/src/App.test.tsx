import { act, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import App from "./App";

async function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
  // The shell probes GET /ready on mount; let that settle before asserting.
  await act(async () => undefined);
}

describe("App", () => {
  it("renders the console shell", async () => {
    await renderAt("/");
    expect(screen.getByText("Bharosa")).toBeInTheDocument();
    expect(screen.getByText("Tenant and actor")).toBeInTheDocument();
  });

  it("serves public verification outside the console shell", async () => {
    await renderAt("/verify");
    expect(screen.getByRole("heading", { name: "Check a pack" })).toBeInTheDocument();
    expect(screen.queryByText("Signing keys")).not.toBeInTheDocument();
  });
});
