import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  AssessorProfileWorkspace,
  type CapabilityClaim,
  type PersonFlagProfile,
  type ProfileUpdateCase,
  type ProfileUpdateLineage,
} from "./ProfileWorkspace";
import type { PatternSummary } from "./PatternWorkspace";

afterEach(() => cleanup());

const pattern: PatternSummary = {
  id: "90000000-0000-0000-0000-000000000001",
  version: 1,
  subject_person_id: "00000000-0000-0000-0000-000000000101",
  behaviour_code: "METRIC_REASONING",
  behaviour_description: "Candidate reasons from measurements.",
  pattern_status: "REPEATED",
  scope: "PROJECT",
  reviewed_by: "00000000-0000-0000-0000-000000000105",
  reviewed_at: "2026-10-06T09:00:00Z",
  updated_at: "2026-10-06T09:00:00Z",
};

const proposed: ProfileUpdateCase = {
  id: "91000000-0000-0000-0000-000000000001",
  version: 1,
  subject_person_id: pattern.subject_person_id,
  track_code: "PRODUCT_MANAGER",
  capability_id: "10000000-0000-0000-0000-000000000003",
  state: "PROPOSED",
  current_claim_id: null,
  current_claim_version: null,
  current_claim_state: null,
  current_level: null,
  current_proven_scope: null,
  current_evidence_recency: null,
  current_confidence_in_claim: null,
  current_next_evidence_needed: null,
  proposed_claim_state: "DEMONSTRATED",
  proposed_level: "L2",
  proposed_proven_scope: "PROJECT",
  proposed_evidence_recency: "CURRENT",
  proposed_confidence_in_claim: "MODERATE",
  proposed_next_evidence_needed: "Authority-pressure evidence.",
  rationale: "Human proposal.",
  reviewed_claim_state: null,
  reviewed_level: null,
  reviewed_proven_scope: null,
  reviewed_evidence_recency: null,
  reviewed_confidence_in_claim: null,
  reviewed_next_evidence_needed: null,
  review_rationale: null,
  created_by: "00000000-0000-0000-0000-000000000104",
  reviewed_by: null,
  reviewed_at: null,
  applied_by: null,
  applied_at: null,
  created_at: "2026-10-06T09:10:00Z",
  updated_at: "2026-10-06T09:10:00Z",
  patterns: [
    {
      pattern_id: pattern.id,
      pattern_version: 1,
      relationship: "SUPPORTING",
      pattern_status: "REPEATED",
      behaviour_code: "METRIC_REASONING",
      scope: "PROJECT",
      reviewed_at: pattern.reviewed_at,
    },
  ],
};

const reviewRequired: ProfileUpdateCase = {
  ...proposed,
  version: 2,
  state: "REVIEW_REQUIRED",
};

const approved: ProfileUpdateCase = {
  ...reviewRequired,
  version: 3,
  state: "APPROVED",
  reviewed_claim_state: "DEMONSTRATED",
  reviewed_level: "L2",
  reviewed_proven_scope: "PROJECT",
  reviewed_evidence_recency: "CURRENT",
  reviewed_confidence_in_claim: "MODERATE",
  reviewed_next_evidence_needed: "Authority-pressure evidence.",
  review_rationale: "Canonical lineage reviewed.",
  reviewed_by: "00000000-0000-0000-0000-000000000105",
  reviewed_at: "2026-10-06T09:20:00Z",
};

const lineage: ProfileUpdateLineage = {
  profile_update_case: reviewRequired,
  patterns: [
    {
      ...proposed.patterns[0],
      evidence: [
        {
          evidence_set_member_id: "90000000-0000-0000-0000-000000000011",
          evidence_case_id: "90000000-0000-0000-0000-000000000012",
          interpretation_id: "90000000-0000-0000-0000-000000000013",
          interpretation_version: 1,
          evidence_relationship: "SUPPORTING",
          signal: "POSITIVE",
          scope: "PROJECT",
          confidence: "HIGH",
          context_difficulty: "HIGH",
          prompt_contamination: "NONE",
          source_independence_group: "MISSION_INSTANCE:mission-1",
          accepted_at: "2026-10-06T09:00:00Z",
          source_observation_id: "90000000-0000-0000-0000-000000000014",
          source_context: "MISSION_RUNTIME",
          source_reference: "MISSION_INSTANCE:mission-1",
          observation_type: "EXPERIMENT_RESULT_OBSERVED",
        },
      ],
    },
  ],
};

const claim: CapabilityClaim = {
  id: "92000000-0000-0000-0000-000000000001",
  version: 1,
  capability_id: proposed.capability_id,
  state: "DEMONSTRATED",
  level: "L2",
  proven_scope: "PROJECT",
  evidence_recency: "CURRENT",
  confidence_in_claim: "MODERATE",
  reviewed_at: "2026-10-06T09:20:00Z",
  reviewed_by: "00000000-0000-0000-0000-000000000105",
  next_evidence_needed: "Authority-pressure evidence.",
  source_profile_update_case_id: proposed.id,
  updated_at: "2026-10-06T09:30:00Z",
  patterns: [
    {
      pattern_id: pattern.id,
      pattern_version: 1,
      relationship: "SUPPORTING",
    },
  ],
};

const currentProfile: PersonFlagProfile = {
  subject_person_id: pattern.subject_person_id,
  profiles: [
    {
      id: "93000000-0000-0000-0000-000000000001",
      version: 2,
      subject_person_id: pattern.subject_person_id,
      track_code: "PRODUCT_MANAGER",
      updated_at: "2026-10-06T09:30:00Z",
      claims: [claim],
    },
  ],
};

it("requires canonical lineage before approval and applies the reviewed claim", async () => {
  const onCreate = vi.fn(async () => proposed);
  const onRequestReview = vi.fn(async () => reviewRequired);
  const onLoadLineage = vi.fn(async () => lineage);
  const onApprove = vi.fn(async () => approved);
  const onApply = vi.fn(async () => claim);
  const onLoadFlagProfile = vi.fn(async () => currentProfile);

  render(
    <AssessorProfileWorkspace
      cases={[]}
      patterns={[pattern]}
      capabilities={[
        {
          id: proposed.capability_id,
          code: "METRICS_EXPERIMENTATION",
          name: "Metrics & Experimentation",
        },
      ]}
      busy={false}
      onCreate={onCreate}
      onRequestReview={onRequestReview}
      onLoadLineage={onLoadLineage}
      onApprove={onApprove}
      onApply={onApply}
      onLoadFlagProfile={onLoadFlagProfile}
    />,
  );

  fireEvent.click(screen.getByLabelText(`انتخاب Pattern ${pattern.id}`));
  fireEvent.change(screen.getByLabelText("Track code Profile"), {
    target: { value: "PRODUCT_MANAGER" },
  });
  fireEvent.change(screen.getByLabelText("Proposed Claim State"), {
    target: { value: "DEMONSTRATED" },
  });
  fireEvent.change(screen.getByLabelText("Proposed Capability Level"), {
    target: { value: "L2" },
  });
  fireEvent.change(screen.getByLabelText("Proposed Proven Scope"), {
    target: { value: "PROJECT" },
  });
  fireEvent.change(screen.getByLabelText("Proposed Evidence Recency"), {
    target: { value: "CURRENT" },
  });
  fireEvent.change(screen.getByLabelText("Proposed Claim Confidence"), {
    target: { value: "MODERATE" },
  });
  fireEvent.change(screen.getByLabelText("Proposed Next Evidence Needed"), {
    target: { value: "Authority-pressure evidence." },
  });
  fireEvent.change(screen.getByLabelText("منطق Profile Proposal"), {
    target: { value: "Human proposal." },
  });

  fireEvent.click(
    screen.getByRole("button", { name: "ساخت Profile Update Proposal" }),
  );
  await screen.findByTestId("profile-update-proposed");

  expect(
    screen.queryByTestId("profile-pre-review-lineage"),
  ).not.toBeInTheDocument();

  fireEvent.click(
    screen.getByRole("button", { name: "ارسال برای Human Review" }),
  );

  const preReview = await screen.findByTestId("profile-pre-review-lineage");
  expect(onLoadLineage).toHaveBeenCalledWith(proposed.id);
  expect(preReview).toHaveTextContent("EXPERIMENT_RESULT_OBSERVED");
  expect(preReview).toHaveTextContent("MISSION_RUNTIME");
  expect(preReview).toHaveTextContent("MISSION_INSTANCE:mission-1");

  const approveButton = screen.getByRole("button", {
    name: "تأیید Human Review Profile",
  });
  expect(approveButton).toBeEnabled();
  fireEvent.click(approveButton);

  await waitFor(() =>
    expect(onApprove).toHaveBeenCalledWith(
      proposed.id,
      2,
      expect.objectContaining({
        reviewedClaimState: "DEMONSTRATED",
        reviewedLevel: "L2",
        reviewedProvenScope: "PROJECT",
      }),
    ),
  );

  fireEvent.click(
    await screen.findByRole("button", {
      name: "Apply Current Capability Claim",
    }),
  );

  expect(await screen.findByTestId("profile-claim-applied")).toHaveTextContent(
    "DEMONSTRATED",
  );
  expect(onLoadFlagProfile).toHaveBeenCalledWith(pattern.subject_person_id);
  expect(await screen.findByTestId("current-capability-claim")).toHaveTextContent(
    "DEMONSTRATED · L2 · PROJECT",
  );
});
