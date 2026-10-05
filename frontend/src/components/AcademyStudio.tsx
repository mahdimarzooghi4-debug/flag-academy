import { useMemo, useState } from "react";
import type { MissionTemplateResponse } from "../api/client";

export type CapabilityOption = {
  version_id: string;
  name: string;
};

export type MissionCreateInput = {
  code: string;
  name: string;
  title: string;
  purpose: string;
  objective: string;
  primary_capability_version_id: string;
  mission_mode: "LEARN" | "PRACTICE" | "ASSESSMENT" | "REAL_PROJECT";
  difficulty: "D1" | "D2" | "D3" | "D4" | "D5";
  world_context: Record<string, unknown>;
  actors: Array<{ name: string; goal: string; authority: string }>;
  information_items: Array<{
    label: string;
    access: "DEFAULT" | "DISCOVERABLE" | "RESTRICTED" | "UNAVAILABLE" | "NOISY";
    content: string;
  }>;
  constraints: Array<{ label: string; description: string }>;
  decision_points: Array<{ code: string; prompt: string }>;
  consequence_rules: Array<{ trigger: string; effect: string }>;
  evidence_opportunities: Array<{ behaviour: string; source: string }>;
  replay_policy: Record<string, unknown>;
  safety_policy: Record<string, unknown>;
};

type Props = {
  capabilities: CapabilityOption[];
  templates: MissionTemplateResponse[];
  onCreate: (input: MissionCreateInput) => Promise<void>;
  onValidate: (versionId: string) => Promise<{ valid: boolean; errors: string[]; warnings: string[] }>;
  onTransition: (
    versionId: string,
    expectedVersion: number,
    action: "pilot" | "mark-validated" | "activate",
  ) => Promise<void>;
  busy?: boolean;
};

export function AcademyStudio({
  capabilities,
  templates,
  onCreate,
  onValidate,
  onTransition,
  busy,
}: Props) {
  const firstCapability = capabilities[0]?.version_id ?? "";
  const [code, setCode] = useState("OWNERSHIP_RECOVERY");
  const [name, setName] = useState("Ownership Recovery Mission");
  const [title, setTitle] = useState("بازگرداندن مالکیت پس از انتشار ناموفق");
  const [purpose, setPurpose] = useState(
    "تمرین تصمیم‌گیری مسئولانه پس از یک Outcome ناموفق بدون تبدیل سناریو به سؤال دارای جواب پنهان.",
  );
  const [objective, setObjective] = useState(
    "فراگیر باید وضعیت را روشن کند، مالکیت نتیجه را بپذیرد و Recovery Plan قابل دفاع بسازد.",
  );
  const [capabilityVersionId, setCapabilityVersionId] = useState(firstCapability);
  const [actorGoal, setActorGoal] = useState("کاهش ریسک و دریافت برنامه بازیابی روشن");
  const [information, setInformation] = useState(
    "نرخ موفقیت انتشار ۸۷٪ بوده و خطا از یک Dependency ناشناخته شروع شده است.",
  );
  const [constraint, setConstraint] = useState("Rollback کامل حداکثر تا ۳۰ دقیقه ممکن است.");
  const [decisionPrompt, setDecisionPrompt] = useState(
    "اکنون چه تصمیمی می‌گیری و چه اطلاعات دیگری می‌خواهی؟",
  );
  const [evidenceBehaviour, setEvidenceBehaviour] = useState(
    "مسئولیت Outcome را می‌پذیرد، trade-off را شفاف می‌کند و نقطه Escalation مشخص می‌سازد.",
  );
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const activeCapabilityId = capabilityVersionId || firstCapability;
  const sortedTemplates = useMemo(
    () => [...templates].sort((a, b) => a.code.localeCompare(b.code)),
    [templates],
  );

  async function create() {
    if (!activeCapabilityId) return;
    await onCreate({
      code: code.trim().toUpperCase().replace(/\s+/g, "_"),
      name: name.trim(),
      title: title.trim(),
      purpose: purpose.trim(),
      objective: objective.trim(),
      primary_capability_version_id: activeCapabilityId,
      mission_mode: "PRACTICE",
      difficulty: "D2",
      world_context: {
        setting: "production incident",
        truth_owner: "mission_runtime",
      },
      actors: [
        {
          name: "Business Sponsor",
          goal: actorGoal.trim(),
          authority: "Can pause rollout and request an executive update.",
        },
      ],
      information_items: [
        {
          label: "Incident signal",
          access: "DEFAULT",
          content: information.trim(),
        },
        {
          label: "Dependency trace",
          access: "DISCOVERABLE",
          content: "A downstream dependency shows intermittent timeout spikes.",
        },
      ],
      constraints: [{ label: "Time", description: constraint.trim() }],
      decision_points: [{ code: "DP1", prompt: decisionPrompt.trim() }],
      consequence_rules: [
        {
          trigger: "Candidate commits to an action",
          effect: "World state changes according to the declared recovery decision.",
        },
      ],
      evidence_opportunities: [
        {
          behaviour: evidenceBehaviour.trim(),
          source: "MISSION_OBSERVATION",
        },
      ],
      replay_policy: {
        allowed: true,
        immediate: true,
        same_behaviour_different_surface: true,
      },
      safety_policy: {
        reveal_hidden_targets: false,
        toxicity_allowed: false,
      },
    });
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">ACADEMY STUDIO</p>
          <h1>طراحی مأموریت</h1>
          <p className="muted">
            مأموریت تعریف می‌شود؛ Runtime و Evidence در Sprintهای بعدی آن را اجرا و تفسیر می‌کنند.
          </p>
        </div>
        <span className="status-chip">ADMIN</span>
      </section>

      <section className="panel">
        <p className="eyebrow">NEW MISSION</p>
        <h2>نسخه Draft بساز</h2>
        <div className="form-grid">
          <label>
            کد مأموریت
            <input aria-label="کد مأموریت" value={code} onChange={(e) => setCode(e.target.value)} />
          </label>
          <label>
            نام Template
            <input aria-label="نام Template" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="full">
            عنوان
            <input aria-label="عنوان مأموریت" value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="full">
            هدف طراحی
            <textarea aria-label="هدف طراحی" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
          </label>
          <label className="full">
            Objective
            <textarea aria-label="Objective" value={objective} onChange={(e) => setObjective(e.target.value)} />
          </label>
          <label>
            Capability اصلی
            <select
              aria-label="Capability اصلی"
              value={activeCapabilityId}
              onChange={(e) => setCapabilityVersionId(e.target.value)}
            >
              {capabilities.map((item) => (
                <option key={item.version_id} value={item.version_id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Actor Goal
            <input aria-label="Actor Goal" value={actorGoal} onChange={(e) => setActorGoal(e.target.value)} />
          </label>
          <label className="full">
            اطلاعات اولیه
            <textarea aria-label="اطلاعات اولیه" value={information} onChange={(e) => setInformation(e.target.value)} />
          </label>
          <label className="full">
            Constraint
            <input aria-label="Constraint" value={constraint} onChange={(e) => setConstraint(e.target.value)} />
          </label>
          <label className="full">
            Decision Point
            <textarea aria-label="Decision Point" value={decisionPrompt} onChange={(e) => setDecisionPrompt(e.target.value)} />
          </label>
          <label className="full">
            Evidence Opportunity
            <textarea
              aria-label="Evidence Opportunity"
              value={evidenceBehaviour}
              onChange={(e) => setEvidenceBehaviour(e.target.value)}
            />
          </label>
        </div>
        <button
          className="primary"
          disabled={busy || !activeCapabilityId || !code.trim() || !name.trim()}
          onClick={() => void create()}
        >
          {busy ? "در حال ثبت..." : "ساخت Draft"}
        </button>
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">MISSION LIBRARY</p>
            <h2>Templateها و نسخه‌ها</h2>
          </div>
          <span className="count">{templates.length}</span>
        </div>
        {validationMessage ? <p className="success-note">{validationMessage}</p> : null}
        <div className="stack">
          {sortedTemplates.map((template) => {
            const version = template.versions[template.versions.length - 1];
            if (!version) return null;
            return (
              <div className="assignment-card" key={template.id}>
                <div className="assignment-head">
                  <div>
                    <strong>{template.name}</strong>
                    <p>{template.code} · v{version.version_number}</p>
                  </div>
                  <span className="state" data-testid="mission-status">{version.status}</span>
                </div>
                <p>{version.title}</p>
                <p className="muted">
                  {version.mission_mode} · {version.difficulty} · Aggregate v{version.aggregate_version}
                </p>
                <div className="action-row">
                  <button
                    className="ghost dark"
                    onClick={async () => {
                      const result = await onValidate(version.id);
                      setValidationMessage(
                        result.valid
                          ? "تعریف مأموریت معتبر است."
                          : `خطاهای تعریف: ${result.errors.join(", ")}`,
                      );
                    }}
                  >
                    اعتبارسنجی تعریف
                  </button>
                  {version.status === "DRAFT" ? (
                    <button
                      className="primary"
                      onClick={() =>
                        void onTransition(version.id, version.aggregate_version, "pilot")
                      }
                    >
                      ورود به Pilot
                    </button>
                  ) : null}
                  {version.status === "PILOT" ? (
                    <button
                      className="primary"
                      onClick={() =>
                        void onTransition(version.id, version.aggregate_version, "mark-validated")
                      }
                    >
                      تأیید Validated
                    </button>
                  ) : null}
                  {version.status === "VALIDATED" ? (
                    <button
                      className="primary"
                      onClick={() =>
                        void onTransition(version.id, version.aggregate_version, "activate")
                      }
                    >
                      فعال‌سازی
                    </button>
                  ) : null}
                </div>
              </div>
            );
          })}
          {templates.length === 0 ? <p className="muted">هنوز مأموریتی ساخته نشده است.</p> : null}
        </div>
      </section>
    </main>
  );
}
