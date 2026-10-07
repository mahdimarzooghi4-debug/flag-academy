export type AIDatasetVersion = {
  id: string;
  dataset_id: string;
  dataset_name: string;
  purpose: string;
  version_number: number;
  dataset_digest: string;
  item_count: number;
  created_at: string;
};

export type AITrainingRun = {
  id: string;
  dataset_version_id: string;
  model_family: string;
  state: string;
  requested_at: string;
  model_artifact_id: string | null;
  model_version_id: string | null;
};

export type AIModelVersion = {
  id: string;
  training_run_id: string;
  dataset_version_id: string;
  model_family: string;
  semantic_version: string;
  attestation_sha256: string;
  attestation_byte_size: number;
  attested_at: string;
  created_at: string;
};

export type AIEvaluationRun = {
  id: string;
  model_version_id: string;
  evaluation_dataset_version_id: string;
  evaluation_policy_key: string;
  evaluation_policy_version: string;
  state: string;
  requested_at: string;
  result_digest: string | null;
  result_byte_size: number | null;
  result_attested_at: string | null;
};

export type AIPromotionDecision = {
  id: string;
  model_version_id: string;
  evaluation_run_id: string;
  reviewer_id: string;
  rationale: string;
  decision: string;
  target_environment: string;
  prior_active_model_version_id: string | null;
  decided_at: string;
};

export type AIGovernanceData = {
  organization_context_id: string;
  dataset_versions: AIDatasetVersion[];
  training_runs: AITrainingRun[];
  model_versions: AIModelVersion[];
  evaluation_runs: AIEvaluationRun[];
  promotion_decisions: AIPromotionDecision[];
};

function shortId(value: string | null | undefined) {
  if (!value) return "—";
  return value.length <= 12 ? value : `${value.slice(0, 8)}…${value.slice(-4)}`;
}

function shortDigest(value: string | null | undefined) {
  if (!value) return "—";
  return `${value.slice(0, 12)}…`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function Metric({
  value,
  label,
}: {
  value: number;
  label: string;
}) {
  return (
    <div className="ai-metric">
      <strong>{value.toLocaleString("fa-IR")}</strong>
      <span>{label}</span>
    </div>
  );
}

function PipelineStep({
  index,
  title,
  subtitle,
  state,
}: {
  index: number;
  title: string;
  subtitle: string;
  state: string;
}) {
  return (
    <div className="ai-pipeline-step">
      <span className="ai-step-index">{index.toLocaleString("fa-IR")}</span>
      <div>
        <strong>{title}</strong>
        <p>{subtitle}</p>
      </div>
      <span className="state">{state}</span>
    </div>
  );
}

export function AIGovernanceWorkspace({
  data,
}: {
  data: AIGovernanceData;
}) {
  const latestDataset = data.dataset_versions[0];
  const latestTraining = data.training_runs[0];
  const latestModel = data.model_versions[0];
  const latestEvaluation = data.evaluation_runs[0];
  const latestPromotion = data.promotion_decisions[0];

  return (
    <main className="page-shell ai-governance-shell" data-testid="ai-governance-workspace">
      <section className="hero-card ai-hero-card">
        <div>
          <p className="eyebrow">AI GOVERNANCE</p>
          <h1>کنترل‌پلین هوش مصنوعی پرچم</h1>
          <p className="muted">
            مسیر واقعی داده، آموزش، مدل، ارزیابی و تصمیم انسانی؛ فقط برای مشاهده و حسابرسی.
          </p>
        </div>
        <div className="ai-hero-badges">
          <span className="status-chip">READ ONLY</span>
          <span className="state state-muted">NO RUNTIME ACTIVATION</span>
        </div>
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">CONTROL PLANE</p>
            <h2>وضعیت زنجیره حاکمیتی</h2>
          </div>
          <small className="ai-context-id">
            Org {shortId(data.organization_context_id)}
          </small>
        </div>
        <div className="ai-metrics-grid">
          <Metric value={data.dataset_versions.length} label="نسخه Dataset" />
          <Metric value={data.training_runs.length} label="Training Run" />
          <Metric value={data.model_versions.length} label="Model Version" />
          <Metric value={data.evaluation_runs.length} label="Evaluation Run" />
          <Metric value={data.promotion_decisions.length} label="Human Decision" />
        </div>
      </section>

      <section className="panel">
        <p className="eyebrow">GOVERNED LINEAGE</p>
        <h2>پنج مرحله تا مجوز انسانی</h2>
        <div className="ai-pipeline">
          <PipelineStep
            index={1}
            title="Dataset"
            subtitle={
              latestDataset
                ? `${latestDataset.dataset_name} · v${latestDataset.version_number}`
                : "هنوز Dataset ثبت نشده است"
            }
            state={latestDataset ? "IMMUTABLE" : "EMPTY"}
          />
          <PipelineStep
            index={2}
            title="Training"
            subtitle={
              latestTraining
                ? `${latestTraining.model_family} · Dataset ${shortId(latestTraining.dataset_version_id)}`
                : "هنوز Training Run ثبت نشده است"
            }
            state={latestTraining?.state ?? "EMPTY"}
          />
          <PipelineStep
            index={3}
            title="Model Registry"
            subtitle={
              latestModel
                ? `${latestModel.model_family} · ${latestModel.semantic_version}`
                : "هنوز Model Version ثبت نشده است"
            }
            state={latestModel ? "ATTESTED" : "EMPTY"}
          />
          <PipelineStep
            index={4}
            title="Offline Evaluation"
            subtitle={
              latestEvaluation
                ? `${latestEvaluation.evaluation_policy_key} · ${latestEvaluation.evaluation_policy_version}`
                : "هنوز Evaluation Run ثبت نشده است"
            }
            state={latestEvaluation?.state ?? "EMPTY"}
          />
          <PipelineStep
            index={5}
            title="Human Promotion"
            subtitle={
              latestPromotion
                ? `${latestPromotion.target_environment} · Reviewer ${shortId(latestPromotion.reviewer_id)}`
                : "هنوز تصمیم انسانی ثبت نشده است"
            }
            state={latestPromotion?.decision ?? "EMPTY"}
          />
        </div>
      </section>

      <section className="grid-two">
        <div className="panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">DATASETS</p>
              <h2>نسخه‌های داده</h2>
            </div>
            <span className="count">{data.dataset_versions.length}</span>
          </div>
          <div className="stack">
            {data.dataset_versions.map((item) => (
              <article className="ai-record-card" key={item.id}>
                <div className="assignment-head">
                  <div>
                    <strong>{item.dataset_name}</strong>
                    <p>{item.purpose} · v{item.version_number}</p>
                  </div>
                  <span className="state">IMMUTABLE</span>
                </div>
                <div className="ai-record-meta">
                  <span>{item.item_count.toLocaleString("fa-IR")} item</span>
                  <span>SHA {shortDigest(item.dataset_digest)}</span>
                  <span>{formatDate(item.created_at)}</span>
                </div>
              </article>
            ))}
            {data.dataset_versions.length === 0 ? (
              <p className="muted">هنوز Dataset Version وجود ندارد.</p>
            ) : null}
          </div>
        </div>

        <div className="panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">TRAINING</p>
              <h2>اجرای آموزش</h2>
            </div>
            <span className="count">{data.training_runs.length}</span>
          </div>
          <div className="stack">
            {data.training_runs.map((item) => (
              <article className="ai-record-card" key={item.id}>
                <div className="assignment-head">
                  <div>
                    <strong>{item.model_family}</strong>
                    <p>Run {shortId(item.id)}</p>
                  </div>
                  <span className="state">{item.state}</span>
                </div>
                <div className="ai-record-meta">
                  <span>Dataset {shortId(item.dataset_version_id)}</span>
                  <span>Artifact {shortId(item.model_artifact_id)}</span>
                  <span>Model {shortId(item.model_version_id)}</span>
                  <span>{formatDate(item.requested_at)}</span>
                </div>
              </article>
            ))}
            {data.training_runs.length === 0 ? (
              <p className="muted">هنوز Training Run وجود ندارد.</p>
            ) : null}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">MODEL REGISTRY</p>
            <h2>نسخه‌های مدل Attested</h2>
          </div>
          <span className="count">{data.model_versions.length}</span>
        </div>
        <div className="ai-table-wrap">
          <table className="ai-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Version</th>
                <th>Training</th>
                <th>Dataset</th>
                <th>SHA-256</th>
                <th>Size</th>
                <th>Attested</th>
              </tr>
            </thead>
            <tbody>
              {data.model_versions.map((item) => (
                <tr key={item.id}>
                  <td>{item.model_family}</td>
                  <td>{item.semantic_version}</td>
                  <td>{shortId(item.training_run_id)}</td>
                  <td>{shortId(item.dataset_version_id)}</td>
                  <td className="ltr-cell">{shortDigest(item.attestation_sha256)}</td>
                  <td>{item.attestation_byte_size.toLocaleString("fa-IR")} B</td>
                  <td>{formatDate(item.attested_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.model_versions.length === 0 ? (
            <p className="muted">هنوز Model Version ثبت نشده است.</p>
          ) : null}
        </div>
      </section>

      <section className="grid-two">
        <div className="panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">OFFLINE EVALUATION</p>
              <h2>شواهد ارزیابی</h2>
            </div>
            <span className="count">{data.evaluation_runs.length}</span>
          </div>
          <div className="stack">
            {data.evaluation_runs.map((item) => (
              <article className="ai-record-card" key={item.id}>
                <div className="assignment-head">
                  <div>
                    <strong>
                      {item.evaluation_policy_key} · {item.evaluation_policy_version}
                    </strong>
                    <p>Evaluation {shortId(item.id)}</p>
                  </div>
                  <span className="state">{item.state}</span>
                </div>
                <div className="ai-record-meta">
                  <span>Model {shortId(item.model_version_id)}</span>
                  <span>Eval Dataset {shortId(item.evaluation_dataset_version_id)}</span>
                  <span>Result SHA {shortDigest(item.result_digest)}</span>
                  <span>
                    {item.result_byte_size === null
                      ? "No result"
                      : `${item.result_byte_size.toLocaleString("fa-IR")} B`}
                  </span>
                  <span>{formatDate(item.result_attested_at ?? item.requested_at)}</span>
                </div>
              </article>
            ))}
            {data.evaluation_runs.length === 0 ? (
              <p className="muted">هنوز Evaluation Run وجود ندارد.</p>
            ) : null}
          </div>
        </div>

        <div className="panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">HUMAN PROMOTION</p>
              <h2>تصمیم‌های انسانی</h2>
            </div>
            <span className="count">{data.promotion_decisions.length}</span>
          </div>
          <div className="stack">
            {data.promotion_decisions.map((item) => (
              <article className="ai-promotion-card" key={item.id}>
                <div className="assignment-head">
                  <div>
                    <strong>{item.target_environment}</strong>
                    <p>Reviewer {shortId(item.reviewer_id)}</p>
                  </div>
                  <span className="state">{item.decision}</span>
                </div>
                <p className="ai-rationale">{item.rationale}</p>
                <div className="ai-record-meta">
                  <span>Model {shortId(item.model_version_id)}</span>
                  <span>Evaluation {shortId(item.evaluation_run_id)}</span>
                  <span>Prior {shortId(item.prior_active_model_version_id)}</span>
                  <span>{formatDate(item.decided_at)}</span>
                </div>
                <div className="ai-governance-note">
                  مجوز انسانی ثبت شده است؛ این رکورد به‌تنهایی Runtime را فعال نمی‌کند.
                </div>
              </article>
            ))}
            {data.promotion_decisions.length === 0 ? (
              <p className="muted">هنوز Human Promotion Decision وجود ندارد.</p>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  );
}
