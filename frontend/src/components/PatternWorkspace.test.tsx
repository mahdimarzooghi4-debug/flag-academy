import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  AssessorPatternWorkspace,
  type PatternCandidate,
  type PatternCandidateReviewLineage,
  type PatternEvidenceSet,
} from "./PatternWorkspace";
import type { EvidenceCase } from "./EvidenceWorkspace";

const acceptedCase: EvidenceCase = {
  id: "90000000-0000-0000-0000-000000000001",
  version: 4,
  organization_context_id: "00000000-0000-0000-0000-000000000001",
  subject_person_id: "00000000-0000-0000-0000-000000000101",
  source_observation_id: "90000000-0000-0000-0000-000000000002",
  source_context: "MISSION_RUNTIME",
  source_reference: "MISSION_INSTANCE:mission-1",
  source_runtime_event_id: null,
  observation_type: "EXPERIMENT_RESULT_OBSERVED",
  observed_fact: "Experiment measurements were recorded.",
  observed_payload: {},
  occurred_at: "2026-10-06T07:00:00Z",
  source_independence_group: "MISSION_INSTANCE:mission-1",
  provenance: {},
  integrity_state: "VERIFIED",
  status: "ACCEPTED",
  context_request: null,
  interpretation: {
    id: "90000000-0000-0000-0000-000000000003",
    version_number: 1,
    status: "ACTIVE",
    behaviour_code: "METRIC_REASONING",
    behaviour_description: "Candidate reasons from measurements without inventing proof.",
    signal: "POSITIVE",
    scope: "RECOVERY_EXPERIMENT",
    confidence: "HIGH",
    context_difficulty: "HIGH",
    prompt_contamination: "NONE",
    ai_contribution: "NONE",
    mode: "ASSESSMENT",
    rationale: "Human-reviewed interpretation.",
    created_by: "90000000-0000-0000-0000-000000000004",
    created_at: "2026-10-06T07:10:00Z",
    links: [],
  },
  reviews: [],
  candidate_responses: [],
  created_at: "2026-10-06T07:00:00Z",
  updated_at: "2026-10-06T07:20:00Z",
  accepted_at: "2026-10-06T07:20:00Z",
  rejected_at: null,
};

describe("AssessorPatternWorkspace", () => {
  it("starts Pattern assembly from Accepted Evidence only", async () => {
    const evidenceSet: PatternEvidenceSet = {
      id: "90000000-0000-0000-0000-000000000010",
      evidence_set_key: "90000000-0000-0000-0000-000000000011",
      version_number: 1,
      subject_person_id: acceptedCase.subject_person_id,
      created_at: "2026-10-06T08:00:00Z",
      members: [
        {
          id: "90000000-0000-0000-0000-000000000012",
          evidence_case_id: acceptedCase.id,
          interpretation_id: acceptedCase.interpretation!.id,
          interpretation_version: 1,
          behaviour_code: "METRIC_REASONING",
          signal: "POSITIVE",
          scope: "RECOVERY_EXPERIMENT",
          confidence: "HIGH",
          accepted_at: "2026-10-06T07:20:00Z",
          target_links: [],
        },
      ],
    };
    const onCreateEvidenceSet = vi.fn(async () => evidenceSet);

    render(
      <AssessorPatternWorkspace
        cases={[
          acceptedCase,
          {
            ...acceptedCase,
            id: "90000000-0000-0000-0000-000000000099",
            status: "UNDER_REVIEW",
            observed_fact: "This case is not accepted yet.",
          },
        ]}
        patterns={[]}
        busy={false}
        onCreateEvidenceSet={onCreateEvidenceSet}
        onCreateCandidate={vi.fn()}
        onLoadCandidateLineage={vi.fn()}
        onReviewCandidate={vi.fn()}
        onLoadLineage={vi.fn()}
      />,
    );

    expect(screen.getByText("Experiment measurements were recorded.")).toBeInTheDocument();
    expect(screen.queryByText("This case is not accepted yet.")).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText(`انتخاب Evidence ${acceptedCase.id}`));
    fireEvent.click(screen.getByRole("button", { name: "ساخت Evidence Set" }));

    await waitFor(() =>
      expect(onCreateEvidenceSet).toHaveBeenCalledWith(
        acceptedCase.subject_person_id,
        [acceptedCase.id],
      ),
    );
    expect(await screen.findByTestId("pattern-evidence-set-created")).toHaveTextContent(
      "Evidence Set v1",
    );
    expect(screen.getByText("۲. Pattern Candidate")).toBeInTheDocument();
  });
});


it("requires pre-review lineage before Human Review can close", async () => {
  const evidenceSet: PatternEvidenceSet = {
    id: "90000000-0000-0000-0000-000000000010",
    evidence_set_key: "90000000-0000-0000-0000-000000000011",
    version_number: 1,
    subject_person_id: acceptedCase.subject_person_id,
    created_at: "2026-10-06T08:00:00Z",
    members: [
      {
        id: "90000000-0000-0000-0000-000000000012",
        evidence_case_id: acceptedCase.id,
        interpretation_id: acceptedCase.interpretation!.id,
        interpretation_version: 1,
        behaviour_code: "METRIC_REASONING",
        signal: "POSITIVE",
        scope: "RECOVERY_EXPERIMENT",
        confidence: "HIGH",
        accepted_at: "2026-10-06T07:20:00Z",
        target_links: [],
      },
    ],
  };
  const candidate: PatternCandidate = {
    id: "90000000-0000-0000-0000-000000000020",
    version: 1,
    subject_person_id: acceptedCase.subject_person_id,
    evidence_set_id: evidenceSet.id,
    behaviour_code: "METRIC_REASONING",
    behaviour_description: "Candidate reasons from measurements without inventing proof.",
    proposed_pattern_status: "REPEATED",
    scope: "RECOVERY_EXPERIMENT",
    rationale: "Human Pattern proposal.",
    created_at: "2026-10-06T08:10:00Z",
    evidence: [
      {
        evidence_set_member_id: evidenceSet.members[0].id,
        relationship: "SUPPORTING",
      },
    ],
  };
  const candidateLineage: PatternCandidateReviewLineage = {
    organization_context_id: acceptedCase.organization_context_id,
    subject_person_id: acceptedCase.subject_person_id,
    candidate: {
      id: candidate.id,
      version: 1,
      proposed_pattern_status: "REPEATED",
      behaviour_code: candidate.behaviour_code,
      behaviour_description: candidate.behaviour_description,
      scope: candidate.scope,
      rationale: candidate.rationale,
      created_by: "90000000-0000-0000-0000-000000000030",
      created_at: candidate.created_at,
    },
    evidence_set: {
      id: evidenceSet.id,
      evidence_set_key: evidenceSet.evidence_set_key,
      version_number: 1,
      created_by: "90000000-0000-0000-0000-000000000030",
      created_at: evidenceSet.created_at,
    },
    evidence: [
      {
        relationship: "SUPPORTING",
        evidence_set_member_id: evidenceSet.members[0].id,
        evidence_case_id: acceptedCase.id,
        interpretation_id: acceptedCase.interpretation!.id,
        interpretation_version: 1,
        behaviour_code: "METRIC_REASONING",
        signal: "POSITIVE",
        scope: "RECOVERY_EXPERIMENT",
        confidence: "HIGH",
        context_difficulty: "HIGH",
        prompt_contamination: "NONE",
        source_independence_group: "MISSION_INSTANCE:mission-1",
        accepted_at: "2026-10-06T07:20:00Z",
        target_links: [],
        source_lineage: {
          source_observation_id: acceptedCase.source_observation_id,
          source_context: "MISSION_RUNTIME",
          source_reference: "MISSION_INSTANCE:mission-1",
          observation_type: "EXPERIMENT_RESULT_OBSERVED",
        },
      },
    ],
  };
  const onLoadCandidateLineage = vi.fn(async () => candidateLineage);

  render(
    <AssessorPatternWorkspace
      cases={[acceptedCase]}
      patterns={[]}
      busy={false}
      onCreateEvidenceSet={vi.fn(async () => evidenceSet)}
      onCreateCandidate={vi.fn(async () => candidate)}
      onLoadCandidateLineage={onLoadCandidateLineage}
      onReviewCandidate={vi.fn()}
      onLoadLineage={vi.fn()}
    />,
  );

  fireEvent.click(screen.getByLabelText(`انتخاب Evidence ${acceptedCase.id}`));
  fireEvent.click(screen.getByRole("button", { name: "ساخت Evidence Set" }));
  await screen.findByTestId("pattern-evidence-set-created");

  fireEvent.change(screen.getByLabelText("Pattern status پیشنهادی"), {
    target: { value: "REPEATED" },
  });
  fireEvent.click(screen.getByRole("button", { name: "ساخت Pattern Candidate" }));

  const preReview = await screen.findByTestId("pattern-pre-review-lineage");
  expect(onLoadCandidateLineage).toHaveBeenCalledWith(candidate.id);
  expect(preReview).toHaveTextContent("EXPERIMENT_RESULT_OBSERVED");
  expect(preReview).toHaveTextContent("MISSION_RUNTIME");
  expect(preReview).toHaveTextContent("MISSION_INSTANCE:mission-1");
  expect(
    screen.getByRole("button", { name: "ثبت Reviewed Behaviour Pattern" }),
  ).toBeEnabled();
});
