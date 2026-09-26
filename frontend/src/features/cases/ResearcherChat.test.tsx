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
      action: null,
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

  it("shows and confirms a structured action returned by the researcher", async () => {
    const action = {
      action_type: "timeline" as const,
      label: "Add to timeline",
      method: "POST" as const,
      endpoint: "/cases/case-1/timeline",
      payload: {
        occurred_on: "2024-03-12",
        title: "Officials published an update",
        description: "The official case page published a dated update.",
        evidence_ids: [],
        person_ids: [],
      },
    };
    vi.spyOn(api, "researchChat").mockResolvedValue({
      answer: "I prepared a timeline event for your review.",
      sources: [
        { title: "Official case page", url: "https://example.gov/case" },
      ],
      action,
    });
    const executeAction = vi
      .spyOn(api, "executeResearchAction")
      .mockResolvedValue({});

    render(<ResearcherChat caseId="case-1" title="Fictional Case" />);
    fireEvent.change(screen.getByLabelText("Ask the researcher"), {
      target: { value: "Add that date to the timeline" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByText("POST /cases/case-1/timeline"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add to timeline" }));

    await waitFor(() =>
      expect(executeAction).toHaveBeenCalledWith("case-1", action),
    );
    expect(await screen.findByRole("button", { name: "Created" })).toBeDisabled();
  });
});
