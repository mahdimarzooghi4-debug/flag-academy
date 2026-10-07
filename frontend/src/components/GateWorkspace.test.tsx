import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  AssessorGateWorkspace,
  CandidateGatePanel,
  type GateAssessmentSummary,
  type GatePreDecision,
} from "./GateWorkspace";

const assessment: GateAssessmentSummary = {
  id: "a-1",
  version: 4,
  subject_person_id: "person-1",
  state: "AT_RISK",
  gate_definition_version_id: "gdv-1",
  gate_definition_version_number: 1,
  gate_code: "A",
  gate_name: "Foundation Readiness",
  pending_review_id: null,
};

const preDecision: GatePreDecision = {
  gate_assessment_id: "a-1",
  gate_assessment_version: 5,
  gate_assessment_state: "REVIEW_REQUIRED",
  gate_review_id: "review-1",
  subject_person_id: "person-1",
  opened_at: "2026-10-07T10:00:00Z",
  definition: {
    gate_definition_version_id: "gdv-1",
    gate_code: "A",
    version_number: 1,
    name: "Foundation Readiness",
    decision_question: "آیا فرد آماده ورود جدی به Product Core است؟",
    requirements: ["Ownership = PASS"],
    outcomes: ["ENTER PRODUCT CORE", "NOT YET"],
  },
  pinned_profile: {
    profile_snapshot_id: "snapshot-1",
    snapshot_version: 2,
    source_flag_profile_version: 3,
    source_track_code: "PRODUCT_MANAGER",
    captured_at: "2026-10-07T10:00:00Z",
    claims: [
      {
        source_claim_id: "claim-1",
        source_claim_version: 3,
        capability_id: "capability-1",
        state: "DEMONSTRATED",
        level: "L2",
        proven_scope: "PROJECT",
        evidence_recency: "CURRENT",
        reviewed_at: "2026-10-07T09:00:00Z",
        next_evidence_needed: "Authority-pressure evidence.",
        supporting_patterns: [
          {
            source_pattern_id: "pattern-1",
            source_pattern_version: 1,
            relationship: "SUPPORTING",
            pattern_status: "REPEATED",
            behaviour_code: "METRIC_REASONING",
            scope: "PROJECT",
            reviewed_at: "2026-10-07T09:00:00Z",
            evidence: [
              {
                evidence_case_id: "evidence-1",
                interpretation_id: "interpretation-1",
                interpretation_version: 1,
                evidence_relationship: "SUPPORTING",
                signal: "POSITIVE",
                scope: "PROJECT",
                confidence: "MODERATE",
                accepted_at: "2026-10-07T08:00:00Z",
                source_observation_id: "observation-1",
                source_context: "MISSION_RUNTIME",
                source_reference: "MISSION_INSTANCE:1",
                observation_type: "EXPERIMENT_RESULT_OBSERVED",
              },
            ],
          },
        ],
        contradictory_patterns: [],
      },
    ],
    evidence_gaps: ["Authority-pressure evidence."],
  },
};

describe("GateWorkspace", () => {
  it("keeps candidate projection on the strict safe allowlist", () => {
    render(
      <CandidateGatePanel
        projection={{
          gates: [
            {
              gate_code: "A",
              gate_name: "Foundation Readiness",
              status: "PASS_CONFIRMED",
              evidence_gaps: ["Authority-pressure evidence."],
              remediation_status: null,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Gate A — Foundation Readiness")).toBeInTheDocument();
    expect(screen.getByText("PASS_CONFIRMED")).toBeInTheDocument();
    expect(screen.getByText("Authority-pressure evidence.")).toBeInTheDocument();
    expect(screen.queryByText(/reviewer/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/rationale/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/MISSION_INSTANCE/)).not.toBeInTheDocument();
  });

  it("runs current profile to pinned lineage to accountable decision", async () => {
    const onLoadCurrentProfile = vi.fn().mockResolvedValue({
      subject_person_id: "person-1",
      profiles: [
        {
          id: "profile-1",
          version: 3,
          subject_person_id: "person-1",
          track_code: "PRODUCT_MANAGER",
          updated_at: "2026-10-07T09:30:00Z",
          claims: [
            {
              id: "claim-1",
              version: 3,
              capability_id: "capability-1",
              state: "DEMONSTRATED",
              level: "L2",
              proven_scope: "PROJECT",
              evidence_recency: "CURRENT",
              confidence_in_claim: "MODERATE",
              reviewed_at: "2026-10-07T09:00:00Z",
              reviewed_by: "reviewer-1",
              next_evidence_needed: "Authority-pressure evidence.",
              source_profile_update_case_id: "case-1",
              updated_at: "2026-10-07T09:00:00Z",
              patterns: [],
            },
          ],
        },
      ],
    });
    const onOpenReview = vi.fn().mockResolvedValue({
      assessment: { ...assessment, state: "REVIEW_REQUIRED", version: 5 },
      gate_review_id: "review-1",
      profile_snapshot_id: "snapshot-1",
      profile_snapshot_version: 2,
    });
    const onLoadPreDecision = vi.fn().mockResolvedValue(preDecision);
    const onDecide = vi.fn().mockResolvedValue({
      assessment: { ...assessment, state: "PASS_CONFIRMED", version: 6 },
      gate_review_id: "review-1",
      decision_id: "decision-1",
      decision_state: "PASS_CONFIRMED",
      decided_at: "2026-10-07T10:05:00Z",
    });

    render(
      <AssessorGateWorkspace
        assessments={[assessment]}
        busy={false}
        onLoadCurrentProfile={onLoadCurrentProfile}
        onOpenReview={onOpenReview}
        onLoadPreDecision={onLoadPreDecision}
        onDecide={onDecide}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "بارگذاری Current Profile" }));
    await screen.findByText("DEMONSTRATED · L2");
    fireEvent.click(screen.getByRole("button", { name: "Open Human Gate Review" }));

    await screen.findByText("METRIC_REASONING");
    expect(screen.getByText("EXPERIMENT_RESULT_OBSERVED")).toBeInTheDocument();
    expect(screen.getByText(/MISSION_RUNTIME/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("منطق Human Gate Decision"), {
      target: { value: "Pinned lineage reviewed by accountable human." },
    });
    fireEvent.click(screen.getByRole("button", { name: "ثبت Human Gate Decision" }));

    await waitFor(() => expect(onDecide).toHaveBeenCalledTimes(1));
    expect(onDecide.mock.calls[0][1]).toMatchObject({
      decisionState: "PASS_CONFIRMED",
      expectedVersion: 5,
      expectedGateDefinitionVersionId: "gdv-1",
      expectedProfileSnapshotId: "snapshot-1",
      expectedProfileSnapshotVersion: 2,
    });
    expect(await screen.findByText("Gate decision ثبت شد")).toBeInTheDocument();
  });
});
