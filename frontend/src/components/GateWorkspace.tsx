import { useEffect, useMemo, useState } from "react";

import type { PersonFlagProfile } from "./ProfileWorkspace";

export type GateAssessmentSummary = {
  id: string;
  version: number;
  subject_person_id: string;
  state: string;
  gate_definition_version_id: string;
  gate_definition_version_number: number;
  gate_code: string;
  gate_name: string;
  pending_review_id: string | null;
};

export type GateOpenReviewResult = {
  assessment: GateAssessmentSummary;
  gate_review_id: string;
  profile_snapshot_id: string;
  profile_snapshot_version: number;
};

export type GateEvidenceLineage = {
  evidence_case_id: string;
  interpretation_id: string;
  interpretation_version: number;
  evidence_relationship: string;
  signal: string;
  scope: string;
  confidence: string;
  accepted_at: string;
  source_observation_id: string;
  source_context: string;
  source_reference: string;
  observation_type: string;
};

export type GatePatternLineage = {
  source_pattern_id: string;
  source_pattern_version: number;
  relationship: string;
  pattern_status: string;
  behaviour_code: string;
  scope: string;
  reviewed_at: string;
  evidence: GateEvidenceLineage[];
};

export type GateClaimRead = {
  source_claim_id: string;
  source_claim_version: number;
  capability_id: string;
  state: string;
  level: string;
  proven_scope: string;
  evidence_recency: string;
  reviewed_at: string;
  next_evidence_needed: string;
  supporting_patterns: GatePatternLineage[];
  contradictory_patterns: GatePatternLineage[];
};

export type GatePreDecision = {
  gate_assessment_id: string;
  gate_assessment_version: number;
  gate_assessment_state: string;
  gate_review_id: string;
  subject_person_id: string;
  opened_at: string;
  definition: {
    gate_definition_version_id: string;
    gate_code: string;
    version_number: number;
    name: string;
    decision_question: string;
    requirements: string[];
    outcomes: string[];
  };
  pinned_profile: {
    profile_snapshot_id: string;
    snapshot_version: number;
    source_flag_profile_version: number;
    source_track_code: string;
    captured_at: string;
    claims: GateClaimRead[];
    evidence_gaps: string[];
  };
};

export type GateDecisionResult = {
  assessment: GateAssessmentSummary;
  gate_review_id: string;
  decision_id: string;
  decision_state: string;
  decided_at: string;
};

export type CandidateGateItem = {
  gate_code: string;
  gate_name: string;
  status: string;
  evidence_gaps: string[];
  remediation_status: string | null;
};

export type CandidateGateProjection = {
  gates: CandidateGateItem[];
};

type DecisionInput = {
  decisionState: "PASS_CONFIRMED" | "FAIL";
  rationale: string;
  expectedVersion: number;
  expectedGateDefinitionVersionId: string;
  expectedProfileSnapshotId: string;
  expectedProfileSnapshotVersion: number;
};

type Props = {
  assessments: GateAssessmentSummary[];
  busy: boolean;
  onLoadCurrentProfile: (subjectPersonId: string) => Promise<PersonFlagProfile>;
  onOpenReview: (
    assessmentId: string,
    trackCode: string,
    expectedVersion: number,
  ) => Promise<GateOpenReviewResult>;
  onLoadPreDecision: (reviewId: string) => Promise<GatePreDecision>;
  onDecide: (
    reviewId: string,
    input: DecisionInput,
  ) => Promise<GateDecisionResult>;
};

function PatternLineage({ pattern }: { pattern: GatePatternLineage }) {
  return (
    <div className="assignment-card">
      <div className="assignment-head">
        <strong>{pattern.behaviour_code}</strong>
        <span className="state">{pattern.relationship}</span>
      </div>
      <p>
        {pattern.pattern_status} · {pattern.scope} · Pattern v
        {pattern.source_pattern_version}
      </p>
      {pattern.evidence.map((evidence) => (
        <div
          className="compact-list"
          key={`${pattern.source_pattern_id}-${evidence.evidence_case_id}`}
        >
          <strong>{evidence.observation_type}</strong>
          <span>
            {evidence.signal} · {evidence.scope} · {evidence.confidence}
          </span>
          <span>
            {evidence.source_context} · {evidence.source_reference}
          </span>
          <span>
            Interpretation v{evidence.interpretation_version}
          </span>
        </div>
      ))}
    </div>
  );
}

export function AssessorGateWorkspace({
  assessments,
  busy,
  onLoadCurrentProfile,
  onOpenReview,
  onLoadPreDecision,
  onDecide,
}: Props) {
  const [selectedId, setSelectedId] = useState(assessments[0]?.id ?? "");
  const selected =
    assessments.find((item) => item.id === selectedId) ?? assessments[0] ?? null;
  const [profile, setProfile] = useState<PersonFlagProfile | null>(null);
  const [trackCode, setTrackCode] = useState("");
  const [preDecision, setPreDecision] = useState<GatePreDecision | null>(null);
  const [decisionState, setDecisionState] =
    useState<"PASS_CONFIRMED" | "FAIL">("PASS_CONFIRMED");
  const [rationale, setRationale] = useState("");
  const [decision, setDecision] = useState<GateDecisionResult | null>(null);
  const [localBusy, setLocalBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!selectedId && assessments.length > 0) {
      setSelectedId(assessments[0].id);
    }
  }, [assessments, selectedId]);

  const activeAssessment = decision?.assessment ?? selected;
  const currentTracks = profile?.profiles ?? [];
  const currentClaims = useMemo(
    () => currentTracks.flatMap((item) => item.claims),
    [currentTracks],
  );

  const loadProfile = async () => {
    if (!selected) return;
    setError("");
    setLocalBusy(true);
    try {
      const next = await onLoadCurrentProfile(selected.subject_person_id);
      setProfile(next);
      const firstTrack = next.profiles[0]?.track_code ?? "";
      setTrackCode(firstTrack);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "بارگذاری Profile ناموفق بود.");
    } finally {
      setLocalBusy(false);
    }
  };

  const loadPreDecision = async (reviewId: string) => {
    setError("");
    setLocalBusy(true);
    try {
      setPreDecision(await onLoadPreDecision(reviewId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "بارگذاری Lineage ناموفق بود.");
    } finally {
      setLocalBusy(false);
    }
  };

  const openReview = async () => {
    if (!selected || !trackCode) return;
    setError("");
    setDecision(null);
    setLocalBusy(true);
    try {
      const opened = await onOpenReview(
        selected.id,
        trackCode,
        selected.version,
      );
      setPreDecision(await onLoadPreDecision(opened.gate_review_id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Open Review ناموفق بود.");
    } finally {
      setLocalBusy(false);
    }
  };

  const completeDecision = async () => {
    if (!preDecision || !rationale.trim()) return;
    setError("");
    setLocalBusy(true);
    try {
      const result = await onDecide(preDecision.gate_review_id, {
        decisionState,
        rationale: rationale.trim(),
        expectedVersion: preDecision.gate_assessment_version,
        expectedGateDefinitionVersionId:
          preDecision.definition.gate_definition_version_id,
        expectedProfileSnapshotId:
          preDecision.pinned_profile.profile_snapshot_id,
        expectedProfileSnapshotVersion:
          preDecision.pinned_profile.snapshot_version,
      });
      setDecision(result);
      setPreDecision(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "ثبت تصمیم Gate ناموفق بود.");
    } finally {
      setLocalBusy(false);
    }
  };

  if (!selected || !activeAssessment) {
    return (
      <main className="page-shell" data-testid="assessor-gate-workspace">
        <section className="hero-card">
          <p className="eyebrow">GATE ASSESSMENT</p>
          <h1>فضای ارزیاب Gate</h1>
          <p>Gate Assessment فعالی برای این سازمان وجود ندارد.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell" data-testid="assessor-gate-workspace">
      <section className="hero-card">
        <p className="eyebrow">GATE ASSESSMENT</p>
        <h1>فضای ارزیاب Gate</h1>
        <p>
          Current Profile → immutable snapshot → Human Review → accountable decision
        </p>
      </section>

      <section className="panel">
        <label>
          Gate Assessment
          <select
            aria-label="Gate Assessment"
            value={selected.id}
            onChange={(event) => {
              setSelectedId(event.target.value);
              setProfile(null);
              setTrackCode("");
              setPreDecision(null);
              setDecision(null);
              setRationale("");
            }}
          >
            {assessments.map((item) => (
              <option key={item.id} value={item.id}>
                Gate {item.gate_code} — {item.gate_name} — {item.state}
              </option>
            ))}
          </select>
        </label>
        <div className="assignment-head">
          <strong>
            Gate {activeAssessment.gate_code} — {activeAssessment.gate_name}
          </strong>
          <span className="state">{activeAssessment.state}</span>
        </div>
        <p>
          Definition v{activeAssessment.gate_definition_version_number} · Assessment v
          {activeAssessment.version}
        </p>
        <button
          disabled={busy || localBusy}
          onClick={() => void loadProfile()}
        >
          بارگذاری Current Profile
        </button>
      </section>

      {profile ? (
        <section className="panel" data-testid="gate-current-profile">
          <h2>Current Flag Profile</h2>
          <label>
            Track code Gate
            <select
              aria-label="Track code Gate"
              value={trackCode}
              onChange={(event) => setTrackCode(event.target.value)}
            >
              {currentTracks.map((item) => (
                <option key={item.id} value={item.track_code}>
                  {item.track_code} · Profile v{item.version}
                </option>
              ))}
            </select>
          </label>
          {currentClaims.map((claim) => (
            <div className="assignment-card" key={claim.id}>
              <div className="assignment-head">
                <strong>{claim.capability_id}</strong>
                <span className="state">
                  {claim.state} · {claim.level}
                </span>
              </div>
              <p>{claim.proven_scope}</p>
              <p>{claim.next_evidence_needed}</p>
            </div>
          ))}
          {activeAssessment.state === "AT_RISK" ? (
            <button
              disabled={busy || localBusy || !trackCode}
              onClick={() => void openReview()}
            >
              Open Human Gate Review
            </button>
          ) : activeAssessment.pending_review_id ? (
            <button
              disabled={busy || localBusy}
              onClick={() =>
                void loadPreDecision(activeAssessment.pending_review_id as string)
              }
            >
              بارگذاری Pinned Review
            </button>
          ) : null}
        </section>
      ) : null}

      {preDecision ? (
        <section className="panel" data-testid="gate-pre-decision">
          <div className="assignment-head">
            <h2>
              Gate {preDecision.definition.gate_code} — {preDecision.definition.name}
            </h2>
            <span className="state">{preDecision.gate_assessment_state}</span>
          </div>
          <p>{preDecision.definition.decision_question}</p>
          <p>
            Definition v{preDecision.definition.version_number} · Snapshot v
            {preDecision.pinned_profile.snapshot_version} · Profile v
            {preDecision.pinned_profile.source_flag_profile_version}
          </p>

          <h3>Requirements</h3>
          <ul>
            {preDecision.definition.requirements.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>

          <h3>Pinned Claims & Lineage</h3>
          {preDecision.pinned_profile.claims.map((claim) => (
            <div className="assignment-card" key={claim.source_claim_id}>
              <div className="assignment-head">
                <strong>{claim.capability_id}</strong>
                <span className="state">
                  {claim.state} · {claim.level}
                </span>
              </div>
              <p>
                Claim v{claim.source_claim_version} · {claim.proven_scope} ·
                {claim.evidence_recency}
              </p>
              <p>
                <strong>Next evidence:</strong> {claim.next_evidence_needed}
              </p>
              {claim.supporting_patterns.map((pattern) => (
                <PatternLineage
                  key={`support-${pattern.source_pattern_id}`}
                  pattern={pattern}
                />
              ))}
              {claim.contradictory_patterns.map((pattern) => (
                <PatternLineage
                  key={`contradict-${pattern.source_pattern_id}`}
                  pattern={pattern}
                />
              ))}
            </div>
          ))}

          <h3>Evidence gaps</h3>
          <ul>
            {preDecision.pinned_profile.evidence_gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>

          <label>
            Human Gate decision
            <select
              aria-label="Human Gate decision"
              value={decisionState}
              onChange={(event) =>
                setDecisionState(
                  event.target.value as "PASS_CONFIRMED" | "FAIL",
                )
              }
            >
              <option value="PASS_CONFIRMED">PASS_CONFIRMED</option>
              <option value="FAIL">FAIL</option>
            </select>
          </label>
          <label>
            منطق Human Gate Decision
            <textarea
              aria-label="منطق Human Gate Decision"
              value={rationale}
              onChange={(event) => setRationale(event.target.value)}
            />
          </label>
          <button
            disabled={busy || localBusy || !rationale.trim()}
            onClick={() => void completeDecision()}
          >
            ثبت Human Gate Decision
          </button>
        </section>
      ) : null}

      {decision ? (
        <section className="panel" data-testid="gate-decision-completed">
          <h2>Gate decision ثبت شد</h2>
          <div className="assignment-head">
            <strong>Accountable Human Review</strong>
            <span className="state">{decision.decision_state}</span>
          </div>
          <p>Assessment v{decision.assessment.version}</p>
        </section>
      ) : null}

      {error ? <div className="center-state error">{error}</div> : null}
    </main>
  );
}

export function CandidateGatePanel({
  projection,
}: {
  projection: CandidateGateProjection;
}) {
  return (
    <main className="page-shell" data-testid="candidate-gate-projection">
      <section className="panel">
        <p className="eyebrow">GATE STATUS</p>
        <h2>وضعیت Gateهای من</h2>
        {projection.gates.length === 0 ? (
          <p>Gate Assessment فعالی وجود ندارد.</p>
        ) : (
          projection.gates.map((gate) => (
            <div className="assignment-card" key={gate.gate_code}>
              <div className="assignment-head">
                <strong>
                  Gate {gate.gate_code} — {gate.gate_name}
                </strong>
                <span className="state">{gate.status}</span>
              </div>
              {gate.remediation_status ? (
                <p>Remediation: {gate.remediation_status}</p>
              ) : null}
              {gate.evidence_gaps.length > 0 ? (
                <>
                  <strong>Evidence بعدی</strong>
                  <ul>
                    {gate.evidence_gaps.map((gap) => (
                      <li key={gap}>{gap}</li>
                    ))}
                  </ul>
                </>
              ) : null}
            </div>
          ))
        )}
      </section>
    </main>
  );
}
