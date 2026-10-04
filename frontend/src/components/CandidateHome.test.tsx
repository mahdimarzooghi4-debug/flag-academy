import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CandidateHome } from "./CandidateHome";

describe("CandidateHome", () => {
  it("separates learning from proof", () => {
    render(
      <CandidateHome
        data={{
          journey: { track: "PRODUCT_MANAGER", state: "ACTIVE" },
          cohort: { name: "PM Flag Cohort" },
          current_wave: { name: "Think & Own" },
          what_to_learn: [{ capability_version_id: "1", name: "Ownership", learning_state: "TO_LEARN" }],
          what_to_prove: [{ capability_version_id: "1", name: "Ownership", proof_state: "UNPROVEN" }],
          upcoming_sessions: [],
        }}
      />,
    );
    expect(screen.getByText("الان چه چیزی باید یاد بگیرم؟")).toBeInTheDocument();
    expect(screen.getByText("الان چه چیزی باید اثبات کنم؟")).toBeInTheDocument();
    expect(screen.getByText("UNPROVEN")).toBeInTheDocument();
  });
});
