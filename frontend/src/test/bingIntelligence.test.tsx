import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BingIntelligence } from "../pages/Bing";
import { api } from "../lib/api";

afterEach(() => vi.restoreAllMocks());

describe("BingIntelligence", () => {
  it("requires operation-specific input and sends a bounded snapshot request", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "get").mockResolvedValue({ items: [] });
    const post = vi.spyOn(api, "post").mockResolvedValue({ id: 7 });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <BingIntelligence siteId={3} />
      </QueryClientProvider>,
    );

    await user.selectOptions(screen.getByLabelText("Datensatz"), "query_pages");
    const capture = screen.getByRole("button", { name: "Abrufen und speichern" });
    expect(capture).toBeDisabled();
    await user.type(screen.getByLabelText("Suchanfrage"), "küchenplanung");
    expect(capture).toBeEnabled();
    await user.click(capture);

    await waitFor(() => expect(post).toHaveBeenCalledWith("/sites/3/bing/snapshots", {
      operation: "query_pages", keyword: "küchenplanung", url: null,
    }));
  });
});
