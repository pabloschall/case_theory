import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../../services/api";
import { ResearcherChat } from "./ResearcherChat";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ResearcherChat", () => {
  it("saves a research answer and its sources to My Notes", async () => {
    vi.spyOn(api, "researchChat").mockResolvedValue({
      answer: "Officials say the investigation remains open.",
      sources: [
        { title: "Official case page", url: "https://example.gov/case" },
      ],
    });
    const createNote = vi.spyOn(api, "createNotebookNote").mockResolvedValue({
      id: "note-1",
      case_id: "case-1",
      title: "Research: What do officials say?",
      body: "Officials say the investigation remains open.",
      author: {
        id: "user-1",
        username: "researcher",
        display_name: "Researcher",
      },
      can_edit: true,
      created_at: "2026-09-25T12:00:00Z",
      updated_at: "2026-09-25T12:00:00Z",
    });

    render(<ResearcherChat caseId="case-1" title="Fictional Case" />);
    expect(
      screen.getByRole("heading", { name: "Researcher" }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Ask the researcher"), {
      target: { value: "What do officials say?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await screen.findByText("Officials say the investigation remains open.");
    fireEvent.click(screen.getByRole("button", { name: "Add to My Notes" }));

    await waitFor(() =>
      expect(createNote).toHaveBeenCalledWith("case-1", {
        title: "Research: What do officials say?",
        body: "Officials say the investigation remains open.\n\nSources\n- Official case page: https://example.gov/case",
      }),
    );
    expect(
      await screen.findByRole("button", { name: "Saved to My Notes" }),
    ).toBeDisabled();
  });
});
