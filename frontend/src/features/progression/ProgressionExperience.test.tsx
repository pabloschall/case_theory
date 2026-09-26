import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../../services/api";
import { ProgressionExperience } from "./ProgressionExperience";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ProgressionExperience", () => {
  it("reveals a newly earned badge and acknowledges it once dismissed", async () => {
    vi.spyOn(api, "progression").mockResolvedValue({
      lifetime_xp: 10,
      show_rank: true,
      show_badges: true,
      rank: {
        code: "observer",
        name: "Observer",
        threshold: 0,
        icon_key: "eye",
      },
      next_rank: {
        code: "source_scout",
        name: "Source Scout",
        threshold: 100,
        icon_key: "compass",
      },
      progress_percent: 10,
      xp_to_next_rank: 90,
      badges: [],
      pending_badges: [
        {
          code: "first_citation",
          name: "First Citation",
          description: "You added your first qualifying public source.",
          criteria: "Add a public evidence link.",
          category: "research_craft",
          icon_key: "bookmark",
          earned_at: "2026-09-25T12:00:00Z",
        },
      ],
      pending_receipts: [],
    });
    const acknowledge = vi
      .spyOn(api, "acknowledgeProgression")
      .mockResolvedValue(undefined);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ProgressionExperience enabled />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: "First Citation" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "First Citation badge" }),
    ).toHaveAttribute("src", "/badges/first-citation.png");
    fireEvent.click(
      screen.getByRole("button", { name: "Continue researching" }),
    );
    await waitFor(() => expect(acknowledge).toHaveBeenCalled());
    expect(acknowledge.mock.calls[0][0]).toEqual({
      badge_codes: ["first_citation"],
    });
  });
});
