import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CandidateHome } from "./CandidateHome";

describe("CandidateHome", () => {
  it("separates learning from proof", () => {
    render(
      <CandidateHome
        data={{
          journey: { track: "PRODUCT_MANAGER", state: "ACTIVE" },
          cohort: { id: "cohort-1", name: "PM Flag Cohort" },
          current_wave: { code: "WAVE_1", name: "Think & Own" },
          what_to_learn: [
            {
              capability_version_id: "1",
              name: "Ownership",
              learning_state: "TO_LEARN",
              next_session: null,
            },
          ],
          what_to_prove: [
            {
              capability_version_id: "1",
              name: "Ownership",
              proof_state: "UNPROVEN",
            },
          ],
          upcoming_sessions: [],
          learning_tasks: [],
          open_missions: [],
          profile_summary: { status: "UNPROVEN" },
          processing_states: [],
        }}
      />,
    );
    expect(screen.getByText("الان چه چیزی باید یاد بگیرم؟")).toBeInTheDocument();
    expect(screen.getByText("الان چه چیزی باید اثبات کنم؟")).toBeInTheDocument();
    expect(screen.getByText("UNPROVEN")).toBeInTheDocument();
  });
});
