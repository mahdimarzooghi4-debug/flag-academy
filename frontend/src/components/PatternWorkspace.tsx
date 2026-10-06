import { useEffect, useMemo, useState } from "react";
import type { EvidenceCase } from "./EvidenceWorkspace";

export type PatternStatus =
  | "EMERGING"
  | "REPEATED"
  | "STABLE"
  | "CONTRADICTED"
  | "REGRESSED"
  | "RECOVERING";

export type PatternEvidenceRelationship = "SUPPORTING" | "CONTRADICTORY";

export type PatternEvidenceSet = {
  id: string;
  evidence_set_key: string;
  version_number: number;
  subject_person_id: string;
  created_at: string;
  members: Array<{
    id: string;
    evidence_case_id: string;
    interpretation_id: string;
    interpretation_version: number;
    behaviour_code: string;
    signal: string;
    scope: string;
    confidence: string;
    accepted_at: string;
    target_links: Array<Record<string, unknown>>;
  }>;
};

export type PatternCandidate = {
  id: string;
  version: number;
  subject_person_id: string;
  evidence_set_id: string;
  behaviour_code: string;
  behaviour_description: string;
  proposed_pattern_status: string;
  scope: string;
  rationale: string;
  created_at: string;
  evidence: Array<{
    evidence_set_member_id: string;
    relationship: string;
  }>;
};

export type PatternSummary = {
  id: string;
  version: number;
  subject_person_id: string;
  behaviour_code: string;
  behaviour_description: string;
  pattern_status: string;
  scope: string;
  reviewed_by: string;
  reviewed_at: string;
  updated_at: string;
};

export type ReviewedPatternLineage = {
  id: string;
  version: number;
  organization_context_id: string;
  subject_person_id: string;
  behaviour_code: string;
  behaviour_description: string;
  pattern_status: string;
  scope: string;
  rationale: string;
  reviewed_by: string;
  reviewed_at: string;
  created_at: string;
  updated_at: string;
  candidate: {
    id: string;
    version: number;
    proposed_pattern_status: string;
    behaviour_code: string;
    behaviour_description: string;
    scope: string;
    rationale: string;
    created_by: string;
    created_at: string;
  };
  evidence_set: {
    id: string;
    evidence_set_key: string;
    version_number: number;
    created_by: string;
    created_at: string;
  };
  review: {
    id: string;
    reviewer_id: string;
    resulting_pattern_status: string;
    rationale: string;
    created_at: string;
  };
  evidence: Array<{
    relationship: string;
    evidence_set_member_id: string;
    evidence_case_id: string;
    interpretation_id: string;
    interpretation_version: number;
    behaviour_code: string;
    signal: string;
    scope: string;
    confidence: string;
    context_difficulty: string;
    prompt_contamination: string;
    source_independence_group: string;
    accepted_at: string;
    target_links: Array<Record<string, unknown>>;
    source_lineage: {
      source_observation_id: string;
      source_context: string;
      source_reference: string;
      observation_type: string;
    };
  }>;
};

type CreateCandidateInput = {
  subjectPersonId: string;
  evidenceSetId: string;
  behaviourCode: string;
  behaviourDescription: string;
  proposedPatternStatus: PatternStatus;
  scope: string;
  rationale: string;
  evidence: Array<{
    evidenceSetMemberId: string;
    relationship: PatternEvidenceRelationship;
  }>;
};

type Props = {
  cases: EvidenceCase[];
  patterns: PatternSummary[];
  busy: boolean;
  onCreateEvidenceSet: (
    subjectPersonId: string,
    evidenceCaseIds: string[],
  ) => Promise<PatternEvidenceSet>;
  onCreateCandidate: (input: CreateCandidateInput) => Promise<PatternCandidate>;
  onReviewCandidate: (
    candidateId: string,
    expectedVersion: number,
    status: PatternStatus,
    rationale: string,
  ) => Promise<PatternSummary>;
  onLoadLineage: (patternId: string) => Promise<ReviewedPatternLineage>;
};

const PATTERN_STATUSES: PatternStatus[] = [
  "EMERGING",
  "REPEATED",
  "STABLE",
  "CONTRADICTED",
  "REGRESSED",
  "RECOVERING",
];

export function AssessorPatternWorkspace({
  cases,
  patterns,
  busy,
  onCreateEvidenceSet,
  onCreateCandidate,
  onReviewCandidate,
  onLoadLineage,
}: Props) {
  const acceptedCases = useMemo(
    () =>
      cases.filter(
        (item) =>
          item.status === "ACCEPTED" &&
          item.interpretation?.status === "ACTIVE",
      ),
    [cases],
  );
  const subjectIds = useMemo(
    () => Array.from(new Set(acceptedCases.map((item) => item.subject_person_id))),
    [acceptedCases],
  );

  const [subjectPersonId, setSubjectPersonId] = useState(subjectIds[0] ?? "");
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<string[]>([]);
  const [evidenceSet, setEvidenceSet] = useState<PatternEvidenceSet | null>(null);
  const [relationships, setRelationships] = useState<
    Record<string, PatternEvidenceRelationship>
  >({});
  const [behaviourCode, setBehaviourCode] = useState("");
  const [behaviourDescription, setBehaviourDescription] = useState("");
  const [proposedStatus, setProposedStatus] = useState<PatternStatus>("EMERGING");
  const [scope, setScope] = useState("");
  const [candidateRationale, setCandidateRationale] = useState("");
  const [candidate, setCandidate] = useState<PatternCandidate | null>(null);
  const [reviewStatus, setReviewStatus] = useState<PatternStatus>("EMERGING");
  const [reviewRationale, setReviewRationale] = useState("");
  const [reviewedPattern, setReviewedPattern] = useState<PatternSummary | null>(null);
  const [lineage, setLineage] = useState<ReviewedPatternLineage | null>(null);
  const [lineageLoading, setLineageLoading] = useState(false);
  const [lineageError, setLineageError] = useState("");

  useEffect(() => {
    if (!subjectPersonId && subjectIds.length > 0) {
      setSubjectPersonId(subjectIds[0]);
    }
  }, [subjectIds, subjectPersonId]);

  const subjectCases = acceptedCases.filter(
    (item) => item.subject_person_id === subjectPersonId,
  );

  const resetDraft = (nextSubjectId: string) => {
    setSubjectPersonId(nextSubjectId);
    setSelectedEvidenceIds([]);
    setEvidenceSet(null);
    setRelationships({});
    setCandidate(null);
    setReviewedPattern(null);
    setLineage(null);
  };

  const createEvidenceSet = async () => {
    const created = await onCreateEvidenceSet(subjectPersonId, selectedEvidenceIds);
    setEvidenceSet(created);
    setCandidate(null);
    setReviewedPattern(null);
    setRelationships(
      Object.fromEntries(
        created.members.map((member) => [member.id, "SUPPORTING" as const]),
      ),
    );

    const firstCase = acceptedCases.find(
      (item) => item.id === created.members[0]?.evidence_case_id,
    );
    if (firstCase?.interpretation) {
      setBehaviourCode(firstCase.interpretation.behaviour_code);
      setBehaviourDescription(firstCase.interpretation.behaviour_description);
      setScope(firstCase.interpretation.scope);
    }
    setCandidateRationale(
      "Accepted Evidence reviewed together as an explicit human Pattern Candidate.",
    );
  };

  const createCandidate = async () => {
    if (!evidenceSet) return;
    const created = await onCreateCandidate({
      subjectPersonId,
      evidenceSetId: evidenceSet.id,
      behaviourCode,
      behaviourDescription,
      proposedPatternStatus: proposedStatus,
      scope,
      rationale: candidateRationale,
      evidence: evidenceSet.members.map((member) => ({
        evidenceSetMemberId: member.id,
        relationship: relationships[member.id] ?? "SUPPORTING",
      })),
    });
    setCandidate(created);
    setReviewStatus(created.proposed_pattern_status as PatternStatus);
    setReviewRationale(
      "Full Evidence lineage and explicit supporting/contradictory relationships reviewed by the assessor.",
    );
  };

  const reviewCandidate = async () => {
    if (!candidate) return;
    const reviewed = await onReviewCandidate(
      candidate.id,
      candidate.version,
      reviewStatus,
      reviewRationale,
    );
    setReviewedPattern(reviewed);
  };

  const inspectLineage = async (patternId: string) => {
    setLineageLoading(true);
    setLineageError("");
    try {
      setLineage(await onLoadLineage(patternId));
    } catch (error) {
      setLineageError(error instanceof Error ? error.message : "دریافت Lineage ناموفق بود.");
    } finally {
      setLineageLoading(false);
    }
  };

  const hasSupportingEvidence =
    evidenceSet?.members.some(
      (member) => (relationships[member.id] ?? "SUPPORTING") === "SUPPORTING",
    ) ?? false;

  return (
    <main className="page-shell pattern-shell" data-testid="assessor-pattern-workspace">
      <section>
        <p className="eyebrow">PATTERN ENGINE</p>
        <h1>فضای ارزیاب Pattern</h1>
        <p className="muted">
          فقط Accepted Evidence وارد این مسیر می‌شود. Pattern نتیجه Human Review است و هیچ
          Profile، Gate، Claim یا Proof state را مستقیماً تغییر نمی‌دهد.
        </p>
      </section>

      <section className="panel stack">
        <div className="assignment-head">
          <div>
            <strong>۱. Evidence Set</strong>
            <p className="muted">Evidenceهای پذیرفته‌شده یک Candidate را انتخاب کنید.</p>
          </div>
          <span className="state">{selectedEvidenceIds.length} SELECTED</span>
        </div>

        {subjectIds.length === 0 ? (
          <div className="center-state compact">
            هنوز Accepted Evidence با Interpretation فعال وجود ندارد.
          </div>
        ) : (
          <>
            <label>
              Candidate
              <select
                aria-label="Candidate برای Pattern"
                value={subjectPersonId}
                onChange={(event) => resetDraft(event.target.value)}
              >
                {subjectIds.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </label>
            <div className="pattern-evidence-list">
              {subjectCases.map((item) => (
                <label className="pattern-evidence-choice" key={item.id}>
                  <input
                    type="checkbox"
                    aria-label={`انتخاب Evidence ${item.id}`}
                    checked={selectedEvidenceIds.includes(item.id)}
                    onChange={(event) => {
                      setEvidenceSet(null);
                      setCandidate(null);
                      setReviewedPattern(null);
                      setSelectedEvidenceIds((current) =>
                        event.target.checked
                          ? [...current, item.id]
                          : current.filter((id) => id !== item.id),
                      );
                    }}
                  />
                  <span>
                    <strong>
                      {item.interpretation?.behaviour_code} · {item.interpretation?.signal}
                    </strong>
                    <small>
                      {item.observation_type} · {item.interpretation?.scope} ·{" "}
                      {item.interpretation?.confidence}
                    </small>
                    <span className="muted">{item.observed_fact}</span>
                  </span>
                </label>
              ))}
            </div>
            <button
              className="primary"
              disabled={busy || selectedEvidenceIds.length === 0}
              onClick={() => void createEvidenceSet()}
            >
              ساخت Evidence Set
            </button>
          </>
        )}

        {evidenceSet ? (
          <div className="success-note" data-testid="pattern-evidence-set-created">
            Evidence Set v{evidenceSet.version_number} ساخته شد · {evidenceSet.members.length} member
          </div>
        ) : null}
      </section>

      {evidenceSet ? (
        <section className="panel stack">
          <div className="assignment-head">
            <div>
              <strong>۲. Pattern Candidate</strong>
              <p className="muted">
                Supporting و Contradictory را صریح نگه دارید؛ سیستم آن‌ها را average نمی‌کند.
              </p>
            </div>
            <span className="state">HUMAN PROPOSAL</span>
          </div>

          <div className="pattern-relationship-list">
            {evidenceSet.members.map((member) => (
              <label key={member.id} className="pattern-evidence-choice">
                <span>
                  <strong>{member.behaviour_code}</strong>
                  <small>
                    {member.signal} · {member.scope} · {member.confidence}
                  </small>
                </span>
                <select
                  aria-label={`رابطه Evidence ${member.id}`}
                  value={relationships[member.id] ?? "SUPPORTING"}
                  onChange={(event) =>
                    setRelationships((current) => ({
                      ...current,
                      [member.id]: event.target.value as PatternEvidenceRelationship,
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
              Behaviour code
              <input
                aria-label="کد رفتار Pattern"
                value={behaviourCode}
                onChange={(event) => setBehaviourCode(event.target.value)}
              />
            </label>
            <label>
              Pattern status پیشنهادی
              <select
                aria-label="Pattern status پیشنهادی"
                value={proposedStatus}
                onChange={(event) => setProposedStatus(event.target.value as PatternStatus)}
              >
                {PATTERN_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </label>
            <label className="full">
              Behaviour description
              <textarea
                aria-label="شرح رفتار Pattern"
                value={behaviourDescription}
                onChange={(event) => setBehaviourDescription(event.target.value)}
              />
            </label>
            <label>
              Scope
              <input
                aria-label="Scope Pattern"
                value={scope}
                onChange={(event) => setScope(event.target.value)}
              />
            </label>
            <label className="full">
              Rationale
              <textarea
                aria-label="منطق Pattern Candidate"
                value={candidateRationale}
                onChange={(event) => setCandidateRationale(event.target.value)}
              />
            </label>
          </div>

          <button
            className="primary"
            disabled={
              busy ||
              !hasSupportingEvidence ||
              !behaviourCode.trim() ||
              !behaviourDescription.trim() ||
              !scope.trim() ||
              !candidateRationale.trim()
            }
            onClick={() => void createCandidate()}
          >
            ساخت Pattern Candidate
          </button>

          {!hasSupportingEvidence ? (
            <p className="error">حداقل یک Evidence باید SUPPORTING باقی بماند.</p>
          ) : null}

          {candidate ? (
            <div className="success-note" data-testid="pattern-candidate-created">
              Pattern Candidate v{candidate.version} ساخته شد · {candidate.proposed_pattern_status}
            </div>
          ) : null}
        </section>
      ) : null}

      {candidate ? (
        <section className="panel stack">
          <div className="assignment-head">
            <div>
              <strong>۳. Human Review</strong>
              <p className="muted">
                بستن Pattern فقط با تصمیم انسانی و یکی از statusهای رسمی DEC-401 انجام می‌شود.
              </p>
            </div>
            <span className="state">v{candidate.version}</span>
          </div>
          <label>
            Reviewed Pattern status
            <select
              aria-label="Reviewed Pattern status"
              value={reviewStatus}
              onChange={(event) => setReviewStatus(event.target.value as PatternStatus)}
            >
              {PATTERN_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label>
            منطق Human Review
            <textarea
              aria-label="منطق Human Review Pattern"
              value={reviewRationale}
              onChange={(event) => setReviewRationale(event.target.value)}
            />
          </label>
          <button
            className="primary"
            disabled={busy || !reviewRationale.trim()}
            onClick={() => void reviewCandidate()}
          >
            ثبت Reviewed Behaviour Pattern
          </button>
          {reviewedPattern ? (
            <div className="success-note" data-testid="reviewed-pattern-created">
              Reviewed Pattern ثبت شد · {reviewedPattern.pattern_status}
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="panel stack">
        <div className="assignment-head">
          <div>
            <strong>۴. Reviewed Patterns & Lineage</strong>
            <p className="muted">
              Lineage کامل برای Assessor قابل مشاهده است؛ Candidate projection جدا و محدود است.
            </p>
          </div>
          <span className="state">{patterns.length} REVIEWED</span>
        </div>

        {patterns.length === 0 ? (
          <p className="muted">هنوز Reviewed Pattern ثبت نشده است.</p>
        ) : (
          <div className="assignment-list">
            {patterns.map((pattern) => (
              <article className="assignment-card pattern-reviewed-card" key={pattern.id}>
                <div className="assignment-head">
                  <div>
                    <strong>{pattern.behaviour_code}</strong>
                    <p>{pattern.behaviour_description}</p>
                  </div>
                  <span className="state">{pattern.pattern_status}</span>
                </div>
                <small>{pattern.scope}</small>
                <button
                  className="ghost dark"
                  disabled={lineageLoading}
                  onClick={() => void inspectLineage(pattern.id)}
                >
                  مشاهده Lineage
                </button>
              </article>
            ))}
          </div>
        )}

        {lineageError ? <p className="error">{lineageError}</p> : null}
        {lineage ? (
          <div className="pattern-lineage" data-testid="pattern-lineage">
            <div className="assignment-head">
              <div>
                <strong>
                  {lineage.behaviour_code} · {lineage.pattern_status}
                </strong>
                <p className="muted">{lineage.rationale}</p>
              </div>
              <span className="state">PATTERN v{lineage.version}</span>
            </div>
            <div className="runtime-meta">
              <span>Candidate v{lineage.candidate.version}</span>
              <span>Evidence Set v{lineage.evidence_set.version_number}</span>
              <span>Reviewed {new Date(lineage.reviewed_at).toLocaleString("fa-IR")}</span>
            </div>
            <div className="pattern-lineage-evidence">
              {lineage.evidence.map((item) => (
                <article className="runtime-block" key={item.evidence_set_member_id}>
                  <div className="assignment-head">
                    <strong>{item.behaviour_code}</strong>
                    <span className="state">{item.relationship}</span>
                  </div>
                  <p>
                    {item.signal} · {item.scope} · {item.confidence} · Interpretation v
                    {item.interpretation_version}
                  </p>
                  <small>
                    {item.source_lineage.observation_type} ·{" "}
                    {item.source_lineage.source_context} ·{" "}
                    {item.source_lineage.source_reference}
                  </small>
                  <pre>{JSON.stringify(item.target_links, null, 2)}</pre>
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
