import { useEffect, useMemo, useState } from "react";
import type { PatternSummary } from "./PatternWorkspace";

export type ProfileClaimState =
  | "UNPROVEN"
  | "EMERGING"
  | "DEMONSTRATED"
  | "PROVEN";

export type ProfileCapabilityLevel = "L0" | "L1" | "L2" | "L3" | "L4";
export type ProfilePatternRelationship = "SUPPORTING" | "CONTRADICTORY";

export type ProfileCapabilityOption = {
  id: string;
  code: string;
  name: string;
};

export type ProfileUpdatePatternSummary = {
  pattern_id: string;
  pattern_version: number;
  relationship: string;
  pattern_status: string;
  behaviour_code: string;
  scope: string;
  reviewed_at: string;
};

export type ProfileUpdateCase = {
  id: string;
  version: number;
  subject_person_id: string;
  track_code: string;
  capability_id: string;
  state: string;
  current_claim_id: string | null;
  current_claim_version: number | null;
  current_claim_state: string | null;
  current_level: string | null;
  current_proven_scope: string | null;
  current_evidence_recency: string | null;
  current_confidence_in_claim: string | null;
  current_next_evidence_needed: string | null;
  proposed_claim_state: string;
  proposed_level: string;
  proposed_proven_scope: string;
  proposed_evidence_recency: string;
  proposed_confidence_in_claim: string;
  proposed_next_evidence_needed: string;
  rationale: string;
  reviewed_claim_state: string | null;
  reviewed_level: string | null;
  reviewed_proven_scope: string | null;
  reviewed_evidence_recency: string | null;
  reviewed_confidence_in_claim: string | null;
  reviewed_next_evidence_needed: string | null;
  review_rationale: string | null;
  created_by: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  applied_by: string | null;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
  patterns: ProfileUpdatePatternSummary[];
};

export type ProfileUpdateLineage = {
  profile_update_case: ProfileUpdateCase;
  patterns: Array<
    ProfileUpdatePatternSummary & {
      evidence: Array<{
        evidence_set_member_id: string;
        evidence_case_id: string;
        interpretation_id: string;
        interpretation_version: number;
        evidence_relationship: string;
        signal: string;
        scope: string;
        confidence: string;
        context_difficulty: string;
        prompt_contamination: string;
        source_independence_group: string;
        accepted_at: string;
        source_observation_id: string;
        source_context: string;
        source_reference: string;
        observation_type: string;
      }>;
    }
  >;
};

export type CapabilityClaim = {
  id: string;
  version: number;
  capability_id: string;
  state: string;
  level: string;
  proven_scope: string;
  evidence_recency: string;
  confidence_in_claim: string;
  reviewed_at: string;
  reviewed_by: string;
  next_evidence_needed: string;
  source_profile_update_case_id: string;
  updated_at: string;
  patterns: Array<{
    pattern_id: string;
    pattern_version: number;
    relationship: string;
  }>;
};

export type PersonFlagProfile = {
  subject_person_id: string;
  profiles: Array<{
    id: string;
    version: number;
    subject_person_id: string;
    track_code: string;
    updated_at: string;
    claims: CapabilityClaim[];
  }>;
};

type CreateProfileUpdateInput = {
  subjectPersonId: string;
  trackCode: string;
  capabilityId: string;
  patterns: Array<{
    patternId: string;
    relationship: ProfilePatternRelationship;
  }>;
  proposedClaimState: ProfileClaimState;
  proposedLevel: ProfileCapabilityLevel;
  proposedProvenScope: string;
  proposedEvidenceRecency: string;
  proposedConfidenceInClaim: string;
  proposedNextEvidenceNeeded: string;
  rationale: string;
};

type ApproveProfileUpdateInput = {
  reviewedClaimState: ProfileClaimState;
  reviewedLevel: ProfileCapabilityLevel;
  reviewedProvenScope: string;
  reviewedEvidenceRecency: string;
  reviewedConfidenceInClaim: string;
  reviewedNextEvidenceNeeded: string;
  rationale: string;
};

type Props = {
  cases: ProfileUpdateCase[];
  patterns: PatternSummary[];
  capabilities: ProfileCapabilityOption[];
  busy: boolean;
  onCreate: (input: CreateProfileUpdateInput) => Promise<ProfileUpdateCase>;
  onRequestReview: (
    caseId: string,
    expectedVersion: number,
  ) => Promise<ProfileUpdateCase>;
  onLoadLineage: (caseId: string) => Promise<ProfileUpdateLineage>;
  onApprove: (
    caseId: string,
    expectedVersion: number,
    input: ApproveProfileUpdateInput,
  ) => Promise<ProfileUpdateCase>;
  onApply: (
    caseId: string,
    expectedVersion: number,
  ) => Promise<CapabilityClaim>;
  onLoadFlagProfile: (subjectPersonId: string) => Promise<PersonFlagProfile>;
};

const CLAIM_STATES: ProfileClaimState[] = [
  "UNPROVEN",
  "EMERGING",
  "DEMONSTRATED",
  "PROVEN",
];
const LEVELS: ProfileCapabilityLevel[] = ["L0", "L1", "L2", "L3", "L4"];

export function AssessorProfileWorkspace({
  cases,
  patterns,
  capabilities,
  busy,
  onCreate,
  onRequestReview,
  onLoadLineage,
  onApprove,
  onApply,
  onLoadFlagProfile,
}: Props) {
  const subjectIds = useMemo(
    () => Array.from(new Set(patterns.map((item) => item.subject_person_id))),
    [patterns],
  );
  const [subjectPersonId, setSubjectPersonId] = useState(subjectIds[0] ?? "");
  const [selectedPatternIds, setSelectedPatternIds] = useState<string[]>([]);
  const [relationships, setRelationships] = useState<
    Record<string, ProfilePatternRelationship>
  >({});
  const [trackCode, setTrackCode] = useState("");
  const [capabilityId, setCapabilityId] = useState(capabilities[0]?.id ?? "");
  const [proposedClaimState, setProposedClaimState] =
    useState<ProfileClaimState>("UNPROVEN");
  const [proposedLevel, setProposedLevel] =
    useState<ProfileCapabilityLevel>("L0");
  const [proposedProvenScope, setProposedProvenScope] = useState("");
  const [proposedEvidenceRecency, setProposedEvidenceRecency] = useState("");
  const [proposedConfidenceInClaim, setProposedConfidenceInClaim] =
    useState("");
  const [proposedNextEvidenceNeeded, setProposedNextEvidenceNeeded] =
    useState("");
  const [proposalRationale, setProposalRationale] = useState("");

  const [activeCaseId, setActiveCaseId] = useState("");
  const [caseSnapshot, setCaseSnapshot] = useState<ProfileUpdateCase | null>(
    null,
  );
  const activeCase =
    caseSnapshot ??
    cases.find((item) => item.id === activeCaseId) ??
    null;

  const [lineage, setLineage] = useState<ProfileUpdateLineage | null>(null);
  const [lineageLoading, setLineageLoading] = useState(false);
  const [lineageError, setLineageError] = useState("");

  const [reviewedClaimState, setReviewedClaimState] =
    useState<ProfileClaimState>("UNPROVEN");
  const [reviewedLevel, setReviewedLevel] =
    useState<ProfileCapabilityLevel>("L0");
  const [reviewedProvenScope, setReviewedProvenScope] = useState("");
  const [reviewedEvidenceRecency, setReviewedEvidenceRecency] = useState("");
  const [reviewedConfidenceInClaim, setReviewedConfidenceInClaim] =
    useState("");
  const [reviewedNextEvidenceNeeded, setReviewedNextEvidenceNeeded] =
    useState("");
  const [reviewRationale, setReviewRationale] = useState("");

  const [appliedClaim, setAppliedClaim] = useState<CapabilityClaim | null>(null);
  const [flagProfile, setFlagProfile] = useState<PersonFlagProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");

  useEffect(() => {
    if (!subjectPersonId && subjectIds.length > 0) {
      setSubjectPersonId(subjectIds[0]);
    }
  }, [subjectIds, subjectPersonId]);

  useEffect(() => {
    if (!capabilityId && capabilities.length > 0) {
      setCapabilityId(capabilities[0].id);
    }
  }, [capabilities, capabilityId]);

  useEffect(() => {
    if (!activeCaseId) return;
    const latest = cases.find((item) => item.id === activeCaseId);
    if (latest && (!caseSnapshot || latest.version >= caseSnapshot.version)) {
      setCaseSnapshot(latest);
    }
  }, [activeCaseId, caseSnapshot, cases]);

  const subjectPatterns = patterns.filter(
    (item) => item.subject_person_id === subjectPersonId,
  );
  const subjectCases = cases.filter(
    (item) => item.subject_person_id === subjectPersonId,
  );

  const resetSubject = (nextSubjectId: string) => {
    setSubjectPersonId(nextSubjectId);
    setSelectedPatternIds([]);
    setRelationships({});
    setActiveCaseId("");
    setCaseSnapshot(null);
    setLineage(null);
    setLineageError("");
    setAppliedClaim(null);
    setFlagProfile(null);
  };

  const seedReviewFields = (item: ProfileUpdateCase) => {
    setReviewedClaimState(
      (item.reviewed_claim_state ??
        item.proposed_claim_state) as ProfileClaimState,
    );
    setReviewedLevel(
      (item.reviewed_level ?? item.proposed_level) as ProfileCapabilityLevel,
    );
    setReviewedProvenScope(
      item.reviewed_proven_scope ?? item.proposed_proven_scope,
    );
    setReviewedEvidenceRecency(
      item.reviewed_evidence_recency ?? item.proposed_evidence_recency,
    );
    setReviewedConfidenceInClaim(
      item.reviewed_confidence_in_claim ??
        item.proposed_confidence_in_claim,
    );
    setReviewedNextEvidenceNeeded(
      item.reviewed_next_evidence_needed ??
        item.proposed_next_evidence_needed,
    );
    setReviewRationale(
      item.review_rationale ??
        "Canonical Profile lineage reviewed by the assessor before approval.",
    );
  };

  const loadLineage = async (caseId: string) => {
    setLineageLoading(true);
    setLineageError("");
    try {
      setLineage(await onLoadLineage(caseId));
    } catch (error) {
      setLineageError(
        error instanceof Error
          ? error.message
          : "دریافت Profile lineage ناموفق بود.",
      );
    } finally {
      setLineageLoading(false);
    }
  };

  const openExistingCase = async (item: ProfileUpdateCase) => {
    setSubjectPersonId(item.subject_person_id);
    setActiveCaseId(item.id);
    setCaseSnapshot(item);
    setAppliedClaim(null);
    seedReviewFields(item);
    setLineage(null);
    setLineageError("");
    if (
      item.state === "REVIEW_REQUIRED" ||
      item.state === "APPROVED" ||
      item.state === "APPLIED"
    ) {
      await loadLineage(item.id);
    }
  };

  const createProposal = async () => {
    const created = await onCreate({
      subjectPersonId,
      trackCode,
      capabilityId,
      patterns: selectedPatternIds.map((patternId) => ({
        patternId,
        relationship: relationships[patternId] ?? "SUPPORTING",
      })),
      proposedClaimState,
      proposedLevel,
      proposedProvenScope,
      proposedEvidenceRecency,
      proposedConfidenceInClaim,
      proposedNextEvidenceNeeded,
      rationale: proposalRationale,
    });
    setActiveCaseId(created.id);
    setCaseSnapshot(created);
    seedReviewFields(created);
    setLineage(null);
    setAppliedClaim(null);
  };

  const requestReview = async () => {
    if (!activeCase) return;
    const updated = await onRequestReview(activeCase.id, activeCase.version);
    setCaseSnapshot(updated);
    seedReviewFields(updated);
    await loadLineage(updated.id);
  };

  const approve = async () => {
    if (!activeCase || !lineage) return;
    const updated = await onApprove(activeCase.id, activeCase.version, {
      reviewedClaimState,
      reviewedLevel,
      reviewedProvenScope,
      reviewedEvidenceRecency,
      reviewedConfidenceInClaim,
      reviewedNextEvidenceNeeded,
      rationale: reviewRationale,
    });
    setCaseSnapshot(updated);
  };

  const loadCurrentProfile = async (personId = subjectPersonId) => {
    if (!personId) return;
    setProfileLoading(true);
    setProfileError("");
    try {
      setFlagProfile(await onLoadFlagProfile(personId));
    } catch (error) {
      setProfileError(
        error instanceof Error
          ? error.message
          : "دریافت Current Flag Profile ناموفق بود.",
      );
    } finally {
      setProfileLoading(false);
    }
  };

  const apply = async () => {
    if (!activeCase) return;
    const claim = await onApply(activeCase.id, activeCase.version);
    setAppliedClaim(claim);
    setCaseSnapshot({
      ...activeCase,
      version: activeCase.version + 1,
      state: "APPLIED",
    });
    await loadCurrentProfile(activeCase.subject_person_id);
  };

  const hasSupportingPattern =
    selectedPatternIds.some(
      (patternId) => (relationships[patternId] ?? "SUPPORTING") === "SUPPORTING",
    );

  return (
    <main className="page-shell pattern-shell" data-testid="assessor-profile-workspace">
      <section>
        <p className="eyebrow">FLAG PROFILE</p>
        <h1>فضای ارزیاب Profile</h1>
        <p className="muted">
          Reviewed Pattern فقط Proposal می‌سازد. Current Capability Claim تنها
          بعد از Human Review و Apply صریح تغییر می‌کند.
        </p>
      </section>

      <section className="panel stack">
        <div className="assignment-head">
          <div>
            <strong>۱. Profile Update Proposal</strong>
            <p className="muted">
              Patternها و target Claim را انسان صریح انتخاب می‌کند؛ سیستم State،
              Level یا Scope را infer نمی‌کند.
            </p>
          </div>
          <span className="state">{selectedPatternIds.length} PATTERN</span>
        </div>

        {subjectIds.length === 0 ? (
          <div className="center-state compact">
            هنوز Reviewed Pattern برای ساخت Profile Update وجود ندارد.
          </div>
        ) : (
          <>
            <label>
              Candidate
              <select
                aria-label="Candidate برای Profile"
                value={subjectPersonId}
                onChange={(event) => resetSubject(event.target.value)}
              >
                {subjectIds.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </label>

            <div className="pattern-evidence-list">
              {subjectPatterns.map((pattern) => (
                <label className="pattern-evidence-choice" key={pattern.id}>
                  <input
                    type="checkbox"
                    aria-label={`انتخاب Pattern ${pattern.id}`}
                    checked={selectedPatternIds.includes(pattern.id)}
                    onChange={(event) => {
                      setActiveCaseId("");
                      setCaseSnapshot(null);
                      setLineage(null);
                      setAppliedClaim(null);
                      setSelectedPatternIds((current) =>
                        event.target.checked
                          ? [...current, pattern.id]
                          : current.filter((id) => id !== pattern.id),
                      );
                    }}
                  />
                  <span>
                    <strong>
                      {pattern.behaviour_code} · {pattern.pattern_status}
                    </strong>
                    <small>{pattern.scope}</small>
                  </span>
                  <select
                    aria-label={`رابطه Pattern ${pattern.id}`}
                    value={relationships[pattern.id] ?? "SUPPORTING"}
                    onChange={(event) =>
                      setRelationships((current) => ({
                        ...current,
                        [pattern.id]: event.target
                          .value as ProfilePatternRelationship,
                      }))
                    }
                  >
                    <option value="SUPPORTING">SUPPORTING</option>
                    <option value="CONTRADICTORY">CONTRADICTORY</option>
                  </select>
                </label>
              ))}
            </div>

            <div className="form-grid">
              <label>
                Track code
                <input
                  aria-label="Track code Profile"
                  value={trackCode}
                  onChange={(event) => setTrackCode(event.target.value)}
                />
              </label>
              <label>
                Capability
                <select
                  aria-label="Capability برای Profile"
                  value={capabilityId}
                  onChange={(event) => setCapabilityId(event.target.value)}
                >
                  {capabilities.map((capability) => (
                    <option key={capability.id} value={capability.id}>
                      {capability.code} · {capability.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Proposed Claim State
                <select
                  aria-label="Proposed Claim State"
                  value={proposedClaimState}
                  onChange={(event) =>
                    setProposedClaimState(
                      event.target.value as ProfileClaimState,
                    )
                  }
                >
                  {CLAIM_STATES.map((state) => (
                    <option key={state} value={state}>
                      {state}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Proposed Level
                <select
                  aria-label="Proposed Capability Level"
                  value={proposedLevel}
                  onChange={(event) =>
                    setProposedLevel(
                      event.target.value as ProfileCapabilityLevel,
                    )
                  }
                >
                  {LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Proven Scope
                <input
                  aria-label="Proposed Proven Scope"
                  value={proposedProvenScope}
                  onChange={(event) =>
                    setProposedProvenScope(event.target.value)
                  }
                />
              </label>
              <label>
                Evidence Recency
                <input
                  aria-label="Proposed Evidence Recency"
                  value={proposedEvidenceRecency}
                  onChange={(event) =>
                    setProposedEvidenceRecency(event.target.value)
                  }
                />
              </label>
              <label>
                Claim Confidence
                <input
                  aria-label="Proposed Claim Confidence"
                  value={proposedConfidenceInClaim}
                  onChange={(event) =>
                    setProposedConfidenceInClaim(event.target.value)
                  }
                />
              </label>
              <label className="full">
                Next Evidence Needed
                <textarea
                  aria-label="Proposed Next Evidence Needed"
                  value={proposedNextEvidenceNeeded}
                  onChange={(event) =>
                    setProposedNextEvidenceNeeded(event.target.value)
                  }
                />
              </label>
              <label className="full">
                Proposal rationale
                <textarea
                  aria-label="منطق Profile Proposal"
                  value={proposalRationale}
                  onChange={(event) => setProposalRationale(event.target.value)}
                />
              </label>
            </div>

            <button
              className="primary"
              disabled={
                busy ||
                capabilities.length === 0 ||
                selectedPatternIds.length === 0 ||
                !hasSupportingPattern ||
                !trackCode.trim() ||
                !capabilityId ||
                !proposedProvenScope.trim() ||
                !proposedEvidenceRecency.trim() ||
                !proposedConfidenceInClaim.trim() ||
                !proposedNextEvidenceNeeded.trim() ||
                !proposalRationale.trim()
              }
              onClick={() => void createProposal()}
            >
              ساخت Profile Update Proposal
            </button>
            {!hasSupportingPattern && selectedPatternIds.length > 0 ? (
              <p className="error">
                حداقل یک Reviewed Pattern باید SUPPORTING باشد.
              </p>
            ) : null}
          </>
        )}

        {activeCase?.state === "PROPOSED" ? (
          <div className="success-note" data-testid="profile-update-proposed">
            Proposal v{activeCase.version} ساخته شد · {activeCase.state}
          </div>
        ) : null}
      </section>

      {activeCase ? (
        <section className="panel stack">
          <div className="assignment-head">
            <div>
              <strong>۲. Human Review Gate</strong>
              <p className="muted">
                Proposal ابتدا صریح وارد REVIEW_REQUIRED می‌شود؛ Approval تا
                بارگذاری canonical lineage بسته می‌ماند.
              </p>
            </div>
            <span className="state">
              {activeCase.state} · v{activeCase.version}
            </span>
          </div>

          {activeCase.state === "PROPOSED" ? (
            <button
              className="primary"
              disabled={busy}
              onClick={() => void requestReview()}
            >
              ارسال برای Human Review
            </button>
          ) : null}

          {lineageLoading ? (
            <p className="muted">در حال دریافت canonical Profile lineage...</p>
          ) : null}
          {lineageError ? <p className="error">{lineageError}</p> : null}
          {lineage ? (
            <div
              className="pattern-lineage"
              data-testid="profile-pre-review-lineage"
            >
              <div className="assignment-head">
                <div>
                  <strong>Lineage قبل از Approval</strong>
                  <p className="muted">
                    Current Claim: {activeCase.current_claim_state ?? "NONE"} ·
                    Proposed: {activeCase.proposed_claim_state} /{" "}
                    {activeCase.proposed_level}
                  </p>
                </div>
                <span className="state">
                  {lineage.patterns.length} PATTERN
                </span>
              </div>
              <div className="pattern-lineage-evidence">
                {lineage.patterns.map((pattern) => (
                  <article className="runtime-block" key={pattern.pattern_id}>
                    <div className="assignment-head">
                      <strong>{pattern.behaviour_code}</strong>
                      <span className="state">{pattern.relationship}</span>
                    </div>
                    <p>
                      {pattern.pattern_status} · {pattern.scope} · Pattern v
                      {pattern.pattern_version}
                    </p>
                    {pattern.evidence.map((evidence) => (
                      <div key={evidence.evidence_set_member_id}>
                        <p>
                          {evidence.evidence_relationship} · {evidence.signal} ·{" "}
                          {evidence.scope} · {evidence.confidence} ·
                          Interpretation v{evidence.interpretation_version}
                        </p>
                        <small>
                          {evidence.observation_type} · {evidence.source_context} ·{" "}
                          {evidence.source_reference} · Independence{" "}
                          {evidence.source_independence_group}
                        </small>
                      </div>
                    ))}
                  </article>
                ))}
              </div>
            </div>
          ) : null}

          {activeCase.state === "REVIEW_REQUIRED" ? (
            <div className="stack">
              <div className="form-grid">
                <label>
                  Reviewed Claim State
                  <select
                    aria-label="Reviewed Claim State"
                    value={reviewedClaimState}
                    onChange={(event) =>
                      setReviewedClaimState(
                        event.target.value as ProfileClaimState,
                      )
                    }
                  >
                    {CLAIM_STATES.map((state) => (
                      <option key={state} value={state}>
                        {state}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Reviewed Level
                  <select
                    aria-label="Reviewed Capability Level"
                    value={reviewedLevel}
                    onChange={(event) =>
                      setReviewedLevel(
                        event.target.value as ProfileCapabilityLevel,
                      )
                    }
                  >
                    {LEVELS.map((level) => (
                      <option key={level} value={level}>
                        {level}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Reviewed Proven Scope
                  <input
                    aria-label="Reviewed Proven Scope"
                    value={reviewedProvenScope}
                    onChange={(event) =>
                      setReviewedProvenScope(event.target.value)
                    }
                  />
                </label>
                <label>
                  Reviewed Evidence Recency
                  <input
                    aria-label="Reviewed Evidence Recency"
                    value={reviewedEvidenceRecency}
                    onChange={(event) =>
                      setReviewedEvidenceRecency(event.target.value)
                    }
                  />
                </label>
                <label>
                  Reviewed Claim Confidence
                  <input
                    aria-label="Reviewed Claim Confidence"
                    value={reviewedConfidenceInClaim}
                    onChange={(event) =>
                      setReviewedConfidenceInClaim(event.target.value)
                    }
                  />
                </label>
                <label className="full">
                  Reviewed Next Evidence Needed
                  <textarea
                    aria-label="Reviewed Next Evidence Needed"
                    value={reviewedNextEvidenceNeeded}
                    onChange={(event) =>
                      setReviewedNextEvidenceNeeded(event.target.value)
                    }
                  />
                </label>
                <label className="full">
                  Human Review rationale
                  <textarea
                    aria-label="منطق Human Review Profile"
                    value={reviewRationale}
                    onChange={(event) =>
                      setReviewRationale(event.target.value)
                    }
                  />
                </label>
              </div>
              <button
                className="primary"
                disabled={
                  busy ||
                  !lineage ||
                  !reviewedProvenScope.trim() ||
                  !reviewedEvidenceRecency.trim() ||
                  !reviewedConfidenceInClaim.trim() ||
                  !reviewedNextEvidenceNeeded.trim() ||
                  !reviewRationale.trim()
                }
                onClick={() => void approve()}
              >
                تأیید Human Review Profile
              </button>
              {!lineage ? (
                <p className="muted">
                  Approval تا بارگذاری موفق Lineage کامل غیرفعال است.
                </p>
              ) : null}
            </div>
          ) : null}

          {activeCase.state === "APPROVED" ? (
            <button
              className="primary"
              disabled={busy}
              onClick={() => void apply()}
            >
              Apply Current Capability Claim
            </button>
          ) : null}

          {appliedClaim ? (
            <div className="success-note" data-testid="profile-claim-applied">
              Current Claim applied · {appliedClaim.state} · {appliedClaim.level}
              {" · "}
              {appliedClaim.proven_scope}
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="panel stack">
        <div className="assignment-head">
          <div>
            <strong>۳. Existing Profile Update Cases</strong>
            <p className="muted">
              پرونده‌های قبلی را باز کنید تا workflow پس از refresh قابل ادامه
              باشد.
            </p>
          </div>
          <span className="state">{subjectCases.length} CASE</span>
        </div>
        {subjectCases.length === 0 ? (
          <p className="muted">برای Candidate انتخاب‌شده پرونده‌ای وجود ندارد.</p>
        ) : (
          <div className="assignment-list">
            {subjectCases.map((item) => (
              <article className="assignment-card" key={item.id}>
                <div className="assignment-head">
                  <div>
                    <strong>{item.state}</strong>
                    <p className="muted">
                      {item.proposed_claim_state} · {item.proposed_level} ·{" "}
                      {item.proposed_proven_scope}
                    </p>
                  </div>
                  <span className="state">v{item.version}</span>
                </div>
                <button
                  className="ghost dark"
                  disabled={busy}
                  onClick={() => void openExistingCase(item)}
                >
                  باز کردن Profile Update Case
                </button>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel stack">
        <div className="assignment-head">
          <div>
            <strong>۴. Current Flag Profile</strong>
            <p className="muted">
              این نما مستقیماً از read endpoint رسمی Current Flag Profile refresh
              می‌شود.
            </p>
          </div>
          <button
            className="ghost dark"
            disabled={busy || profileLoading || !subjectPersonId}
            onClick={() => void loadCurrentProfile()}
          >
            Refresh Current Profile
          </button>
        </div>
        {profileLoading ? <p className="muted">در حال دریافت Current Profile...</p> : null}
        {profileError ? <p className="error">{profileError}</p> : null}
        {flagProfile ? (
          <div data-testid="current-flag-profile">
            {flagProfile.profiles.length === 0 ? (
              <p className="muted">Current Claim ثبت نشده است.</p>
            ) : (
              flagProfile.profiles.map((profile) => (
                <article className="runtime-block" key={profile.id}>
                  <div className="assignment-head">
                    <strong>{profile.track_code}</strong>
                    <span className="state">PROFILE v{profile.version}</span>
                  </div>
                  {profile.claims.map((claim) => (
                    <div key={claim.id} data-testid="current-capability-claim">
                      <p>
                        {claim.state} · {claim.level} · {claim.proven_scope}
                      </p>
                      <small>
                        Recency {claim.evidence_recency} · Next{" "}
                        {claim.next_evidence_needed}
                      </small>
                    </div>
                  ))}
                </article>
              ))
            )}
          </div>
        ) : null}
      </section>
    </main>
  );
}
