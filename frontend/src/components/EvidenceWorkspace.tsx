import { useState } from "react";

export type EvidenceLink = {
  id: string;
  target_type: string;
  target_ref: string;
  signal: string;
  scope: string;
  relevance: string;
  confidence: string;
};

export type EvidenceInterpretation = {
  id: string;
  version_number: number;
  status: string;
  behaviour_code: string;
  behaviour_description: string;
  signal: string;
  scope: string;
  confidence: string;
  context_difficulty: string;
  prompt_contamination: string;
  ai_contribution: "NONE";
  mode: string;
  rationale: string;
  created_by: string;
  created_at: string;
  links: EvidenceLink[];
};

export type EvidenceReview = {
  id: string;
  reviewer_id: string;
  decision: string;
  rationale: string;
  created_at: string;
};

export type EvidenceCandidateResponse = {
  id: string;
  candidate_id: string;
  response_text: string;
  created_at: string;
};

export type EvidenceCase = {
  id: string;
  version: number;
  organization_context_id: string;
  subject_person_id: string;
  source_observation_id: string;
  source_context: string;
  source_reference: string;
  source_runtime_event_id: string | null;
  observation_type: string;
  observed_fact: string;
  observed_payload: Record<string, unknown>;
  occurred_at: string;
  source_independence_group: string;
  provenance: Record<string, unknown>;
  integrity_state: string;
  status: string;
  context_request: string | null;
  interpretation: EvidenceInterpretation | null;
  reviews: EvidenceReview[];
  candidate_responses: EvidenceCandidateResponse[];
  created_at: string;
  updated_at: string;
  accepted_at: string | null;
  rejected_at: string | null;
};

export type CandidateEvidenceCase = {
  id: string;
  version: number;
  source_observation_id: string;
  source_context: string;
  source_reference: string;
  observation_type: string;
  observed_fact: string;
  observed_payload: Record<string, unknown>;
  occurred_at: string;
  integrity_state: string;
  status: string;
  context_request: string | null;
  accepted_interpretation: EvidenceInterpretation | null;
  candidate_responses: EvidenceCandidateResponse[];
  created_at: string;
  updated_at: string;
};

export type EvidenceInterpretationDraft = {
  behaviour_code: string;
  behaviour_description: string;
  signal: "POSITIVE" | "NEGATIVE" | "CRITICAL" | "NEUTRAL";
  scope: string;
  confidence: "LOW" | "MEDIUM" | "HIGH";
  context_difficulty: string;
  prompt_contamination: string;
  ai_contribution: string;
  mode: string;
  rationale: string;
  links: Array<{
    target_type: "CAPABILITY" | "COMPETENCY" | "GATE";
    target_ref: string;
    signal: "POSITIVE" | "NEGATIVE" | "CRITICAL" | "NEUTRAL";
    scope: string;
    relevance: "LOW" | "MEDIUM" | "HIGH";
    confidence: "LOW" | "MEDIUM" | "HIGH";
  }>;
};

type AssessorProps = {
  cases: EvidenceCase[];
  busy: boolean;
  onSubmit: (
    caseId: string,
    version: number,
    interpretation: EvidenceInterpretationDraft,
  ) => Promise<void>;
  onStartReview: (caseId: string, version: number, rationale: string) => Promise<void>;
  onRequestContext: (
    caseId: string,
    version: number,
    contextRequest: string,
  ) => Promise<void>;
  onAccept: (caseId: string, version: number, rationale: string) => Promise<void>;
  onReject: (caseId: string, version: number, rationale: string) => Promise<void>;
};

function AssessorEvidenceCard({
  item,
  busy,
  onSubmit,
  onStartReview,
  onRequestContext,
  onAccept,
  onReject,
}: AssessorProps & { item: EvidenceCase }) {
  const [behaviourCode, setBehaviourCode] = useState("METRIC_REASONING");
  const [behaviourDescription, setBehaviourDescription] = useState(
    "Candidate separates experiment measurement from interpretation and proof.",
  );
  const [signal, setSignal] = useState<
    "POSITIVE" | "NEGATIVE" | "CRITICAL" | "NEUTRAL"
  >("POSITIVE");
  const [scope, setScope] = useState("MISSION");
  const [confidence, setConfidence] = useState<"LOW" | "MEDIUM" | "HIGH">("HIGH");
  const [contextDifficulty, setContextDifficulty] = useState("D3");
  const [promptContamination, setPromptContamination] = useState("NONE");
  const aiContribution = "NONE" as const;
  const [mode, setMode] = useState("ASSESSMENT");
  const [rationale, setRationale] = useState(
    "The observed measurement is factual; this interpretation remains human-reviewed evidence only.",
  );
  const [targetRef, setTargetRef] = useState("METRICS_EXPERIMENTATION");
  const [reviewRationale, setReviewRationale] = useState(
    "Source lineage and interpretation contract reviewed.",
  );
  const [contextRequest, setContextRequest] = useState(
    "توضیح بده این Result چگونه روی تصمیم بعدی تو اثر گذاشت، بدون اینکه آن را Proof تلقی کنی.",
  );
  const [decisionRationale, setDecisionRationale] = useState(
    "Observation lineage is intact and the interpretation is supported by the reviewed context.",
  );

  return (
    <article className="assignment-card" data-testid={`evidence-case-${item.id}`}>
      <div className="assignment-head">
        <div>
          <strong>{item.observation_type}</strong>
          <div className="muted">{item.observed_fact}</div>
        </div>
        <span className="state">{item.status}</span>
      </div>
      <div className="muted">
        {item.integrity_state} · {item.source_context} · {item.source_reference}
      </div>
      <pre data-testid="evidence-observation-payload">
        {JSON.stringify(item.observed_payload, null, 2)}
      </pre>

      {item.status === "DRAFT" ? (
        <div className="stack">
          <label>
            کد رفتار
            <input
              aria-label="کد رفتار Evidence"
              value={behaviourCode}
              onChange={(event) => setBehaviourCode(event.target.value)}
            />
          </label>
          <label>
            شرح رفتار
            <textarea
              aria-label="شرح رفتار Evidence"
              value={behaviourDescription}
              onChange={(event) => setBehaviourDescription(event.target.value)}
            />
          </label>
          <label>
            Signal
            <select
              aria-label="Signal Evidence"
              value={signal}
              onChange={(event) =>
                setSignal(
                  event.target.value as "POSITIVE" | "NEGATIVE" | "CRITICAL" | "NEUTRAL",
                )
              }
            >
              <option value="POSITIVE">POSITIVE</option>
              <option value="NEGATIVE">NEGATIVE</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="NEUTRAL">NEUTRAL</option>
            </select>
          </label>
          <label>
            Scope
            <input
              aria-label="Scope Evidence"
              value={scope}
              onChange={(event) => setScope(event.target.value)}
            />
          </label>
          <label>
            Confidence
            <select
              aria-label="Confidence Evidence"
              value={confidence}
              onChange={(event) =>
                setConfidence(event.target.value as "LOW" | "MEDIUM" | "HIGH")
              }
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
            </select>
          </label>
          <label>
            Context difficulty
            <input
              aria-label="Context difficulty Evidence"
              value={contextDifficulty}
              onChange={(event) => setContextDifficulty(event.target.value)}
            />
          </label>
          <label>
            Prompt contamination
            <input
              aria-label="Prompt contamination Evidence"
              value={promptContamination}
              onChange={(event) => setPromptContamination(event.target.value)}
            />
          </label>
          <label>
            AI contribution
            <input aria-label="AI contribution Evidence" value={aiContribution} readOnly />
          </label>
          <label>
            Mode
            <input
              aria-label="Mode Evidence"
              value={mode}
              onChange={(event) => setMode(event.target.value)}
            />
          </label>
          <label>
            Target ref
            <input
              aria-label="Target ref Evidence"
              value={targetRef}
              onChange={(event) => setTargetRef(event.target.value)}
            />
          </label>
          <label>
            منطق Interpretation
            <textarea
              aria-label="منطق Interpretation Evidence"
              value={rationale}
              onChange={(event) => setRationale(event.target.value)}
            />
          </label>
          <button
            disabled={busy}
            onClick={() =>
              onSubmit(item.id, item.version, {
                behaviour_code: behaviourCode,
                behaviour_description: behaviourDescription,
                signal,
                scope,
                confidence,
                context_difficulty: contextDifficulty,
                prompt_contamination: promptContamination,
                ai_contribution: aiContribution,
                mode,
                rationale,
                links: [
                  {
                    target_type: "CAPABILITY",
                    target_ref: targetRef,
                    signal,
                    scope,
                    relevance: "HIGH",
                    confidence,
                  },
                ],
              })
            }
          >
            ثبت Interpretation
          </button>
        </div>
      ) : null}

      {item.interpretation ? (
        <div data-testid="assessor-interpretation">
          <strong>
            {item.interpretation.behaviour_code} · {item.interpretation.signal}
          </strong>
          <p>{item.interpretation.behaviour_description}</p>
          <div className="muted">
            Scope {item.interpretation.scope} · Confidence {item.interpretation.confidence} ·
            AI {item.interpretation.ai_contribution}
          </div>
        </div>
      ) : null}

      {item.status === "SUBMITTED" || item.status === "NEEDS_CONTEXT" ? (
        <div className="stack">
          <label>
            منطق Review
            <textarea
              aria-label="منطق Review Evidence"
              value={reviewRationale}
              onChange={(event) => setReviewRationale(event.target.value)}
            />
          </label>
          <button
            disabled={busy || (item.status === "NEEDS_CONTEXT" && item.candidate_responses.length === 0)}
            onClick={() => onStartReview(item.id, item.version, reviewRationale)}
          >
            {item.status === "NEEDS_CONTEXT" ? "بازگشت به Review" : "شروع Review"}
          </button>
        </div>
      ) : null}

      {item.status === "UNDER_REVIEW" ? (
        <div className="stack">
          <label>
            درخواست Context
            <textarea
              aria-label="درخواست Context Evidence"
              value={contextRequest}
              onChange={(event) => setContextRequest(event.target.value)}
            />
          </label>
          <button
            disabled={busy}
            onClick={() => onRequestContext(item.id, item.version, contextRequest)}
          >
            درخواست Context از Candidate
          </button>
          <label>
            منطق تصمیم Review
            <textarea
              aria-label="منطق تصمیم Evidence"
              value={decisionRationale}
              onChange={(event) => setDecisionRationale(event.target.value)}
            />
          </label>
          <div className="actions">
            <button
              disabled={busy}
              onClick={() => onAccept(item.id, item.version, decisionRationale)}
            >
              پذیرش Evidence
            </button>
            <button
              className="ghost"
              disabled={busy}
              onClick={() => onReject(item.id, item.version, decisionRationale)}
            >
              رد Evidence
            </button>
          </div>
        </div>
      ) : null}

      {item.context_request ? (
        <div data-testid="assessor-context-request">
          <strong>Context request</strong>
          <p>{item.context_request}</p>
        </div>
      ) : null}

      {item.candidate_responses.map((response) => (
        <div key={response.id} data-testid="assessor-candidate-response">
          <strong>Candidate context</strong>
          <p>{response.response_text}</p>
        </div>
      ))}
    </article>
  );
}

export function AssessorEvidenceWorkspace(props: AssessorProps) {
  return (
    <main className="page-shell">
      <section>
        <h1>فضای ارزیاب Evidence</h1>
        <p className="muted">
          Observation واقعیت immutable است؛ این فضا فقط Interpretation و Human Review را
          مدیریت می‌کند.
        </p>
      </section>
      <section className="assignment-list">
        {props.cases.length === 0 ? (
          <div className="center-state">Evidence Case در انتظار Review وجود ندارد.</div>
        ) : (
          props.cases.map((item) => (
            <AssessorEvidenceCard key={item.id} item={item} {...props} />
          ))
        )}
      </section>
    </main>
  );
}

type CandidateProps = {
  cases: CandidateEvidenceCase[];
  busy: boolean;
  onRespond: (
    caseId: string,
    version: number,
    responseText: string,
  ) => Promise<void>;
};

function CandidateEvidenceCard({
  item,
  busy,
  onRespond,
}: CandidateProps & { item: CandidateEvidenceCase }) {
  const [responseText, setResponseText] = useState("");

  return (
    <article className="assignment-card" data-testid={`candidate-evidence-case-${item.id}`}>
      <div className="assignment-head">
        <div>
          <strong>{item.observation_type}</strong>
          <div className="muted">{item.observed_fact}</div>
        </div>
        <span className="state">{item.status}</span>
      </div>
      <pre>{JSON.stringify(item.observed_payload, null, 2)}</pre>

      {item.context_request ? (
        <div data-testid="candidate-context-request">
          <strong>درخواست Context از ارزیاب</strong>
          <p>{item.context_request}</p>
        </div>
      ) : null}

      {item.status === "NEEDS_CONTEXT" ? (
        <div className="stack">
          <label>
            پاسخ Context
            <textarea
              aria-label="پاسخ Context Evidence"
              value={responseText}
              onChange={(event) => setResponseText(event.target.value)}
            />
          </label>
          <button
            disabled={busy || responseText.trim().length === 0}
            onClick={async () => {
              await onRespond(item.id, item.version, responseText);
              setResponseText("");
            }}
          >
            ارسال Context
          </button>
        </div>
      ) : null}

      {item.candidate_responses.map((response) => (
        <div key={response.id}>
          <strong>Context ثبت‌شده شما</strong>
          <p>{response.response_text}</p>
        </div>
      ))}

      {item.accepted_interpretation ? (
        <div data-testid="candidate-accepted-interpretation">
          <strong>
            Reviewed Evidence · {item.accepted_interpretation.behaviour_code} ·{" "}
            {item.accepted_interpretation.signal}
          </strong>
          <p>{item.accepted_interpretation.behaviour_description}</p>
          <p>{item.accepted_interpretation.rationale}</p>
        </div>
      ) : null}
    </article>
  );
}

export function CandidateEvidenceWorkspace(props: CandidateProps) {
  return (
    <section className="page-shell">
      <h2>Evidence و Context من</h2>
      <p className="muted">
        Context شما Evidence را بازنویسی نمی‌کند؛ Reviewed Evidence نیز به‌تنهایی Capability را
        Proven نمی‌کند.
      </p>
      <div className="assignment-list">
        {props.cases.map((item) => (
          <CandidateEvidenceCard key={item.id} item={item} {...props} />
        ))}
      </div>
    </section>
  );
}
