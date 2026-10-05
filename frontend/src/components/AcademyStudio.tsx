import { useMemo, useState } from "react";
import type { MissionTemplateResponse } from "../api/client";

export type CapabilityOption = {
  version_id: string;
  name: string;
};

export type MissionAssignmentCandidate = {
  id: string;
  display_name: string;
};

export type MissionAssignmentSummary = {
  id: string;
  version: number;
  candidate_id: string;
  candidate_name: string;
  mission_version_id: string;
  mission_code: string;
  mission_title: string;
  status: string;
  assignment_reason: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
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
  assignmentCandidates: MissionAssignmentCandidate[];
  assignments: MissionAssignmentSummary[];
  onCreate: (input: MissionCreateInput) => Promise<void>;
  onValidate: (versionId: string) => Promise<{ valid: boolean; errors: string[]; warnings: string[] }>;
  onTransition: (
    versionId: string,
    expectedVersion: number,
    action: "pilot" | "mark-validated" | "activate",
  ) => Promise<void>;
  onAssign: (versionId: string, candidateId: string) => Promise<void>;
  busy?: boolean;
};

export function AcademyStudio({
  capabilities,
  templates,
  assignmentCandidates,
  assignments,
  onCreate,
  onValidate,
  onTransition,
  onAssign,
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
  const [assignmentMessage, setAssignmentMessage] = useState<string | null>(null);
  const [assignmentCandidateId, setAssignmentCandidateId] = useState(
    assignmentCandidates[0]?.id ?? "",
  );

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
        runtime_v1: {
          initial_state: {
            business: { rollout_status: "DEGRADED" },
            technical: {
              error_rate_percent: 13,
              rollback_available: true,
              rollback_started: false,
              root_cause_code: "DOWNSTREAM_DEPENDENCY",
            },
            risk: { level: "HIGH" },
            stakeholder: {
              executive_attention: "NONE",
              executive_checkpoint: "NOT_SCHEDULED",
              recovery_signal: "NOT_BROADCAST",
            },
            mission: {
              decision_status: "OPEN",
              escalation_status: "NONE",
              delegation_status: "NOT_DELEGATED",
              accountability_owner: "CANDIDATE",
            },
            delivery: {
              recovery_coordinator: "CANDIDATE",
            },
          },
          candidate_visible_paths: [
            "business.rollout_status",
            "technical.error_rate_percent",
            "technical.rollback_available",
            "technical.rollback_started",
            "risk.level",
            "stakeholder.executive_attention",
            "stakeholder.recovery_signal",
            "stakeholder.executive_checkpoint",
            "mission.decision_status",
            "mission.escalation_status",
            "mission.delegation_status",
            "mission.accountability_owner",
            "delivery.recovery_coordinator",
          ],
          actor_runtime: {
            business_sponsor: {
              definition_name: "Business Sponsor",
              initial_state: {
                trust_toward_candidate: 35,
                current_frustration: 70,
                commitment: "CONDITIONAL",
                private_escalation_threshold: "LOW",
              },
              candidate_visible_paths: [
                "trust_toward_candidate",
                "current_frustration",
                "commitment",
              ],
              communication_options: [
                {
                  code: "OWN_AND_ALIGN_RECOVERY",
                  label: "پذیرش مالکیت و هم‌راستا کردن برنامه بازیابی",
                  reply:
                    "مالکیت روشن شد. برنامه بازیابی را با checkpoint مشخص جلو ببرید؛ من rollout را تا ارزیابی بعدی متوقف نگه می‌دارم.",
                  effect: {
                    trust_toward_candidate: 60,
                    current_frustration: 40,
                    commitment: "SUPPORTIVE",
                  },
                },
              ],
            },
            delivery_lead: {
              definition_name: "Delivery Lead",
              initial_state: {
                capacity_status: "AVAILABLE",
                commitment: "UNASSIGNED",
                delegated_responsibility: "NONE",
                private_delivery_risk: "MEDIUM",
              },
              candidate_visible_paths: [
                "capacity_status",
                "commitment",
                "delegated_responsibility",
              ],
              communication_options: [],
            },
          },
          delegation_options: [
            {
              code: "DELEGATE_RECOVERY_COORDINATION",
              label: "واگذاری هماهنگی بازیابی به Delivery Lead",
              actor_key: "delivery_lead",
              response:
                "هماهنگی rollback و جمع‌آوری وضعیت را می‌پذیرم؛ accountability نتیجه همچنان با شما می‌ماند.",
              world_effect: {
                mission: { delegation_status: "ACTIVE" },
                delivery: { recovery_coordinator: "DELIVERY_LEAD" },
              },
              actor_effect: {
                commitment: "OWNS_RECOVERY_COORDINATION",
                delegated_responsibility: "RECOVERY_COORDINATION",
              },
            },
          ],
          escalation_options: [
            {
              code: "EXECUTIVE_RECOVERY_ESCALATION",
              label: "Escalate برنامه بازیابی به Business Sponsor",
              actor_key: "business_sponsor",
              response:
                "Escalation پذیرفته شد. Executive attention فعال است و تصمیم بازیابی در checkpoint بعدی بازبینی می‌شود.",
              world_effect: {
                stakeholder: { executive_attention: "ENGAGED" },
                mission: { escalation_status: "EXECUTIVE_REVIEW" },
              },
              actor_effect: {
                commitment: "EXECUTIVE_SPONSORSHIP",
              },
              scheduled_effects: [
                {
                  code: "EXECUTIVE_CHECKPOINT_DUE",
                  label: "Executive recovery checkpoint",
                  due_after_seconds: 900,
                  effect: {
                    stakeholder: { executive_checkpoint: "DUE" },
                    mission: { escalation_status: "CHECKPOINT_DUE" },
                  },
                  visibility: "CANDIDATE",
                  cancellable: false,
                  cancel_condition: {},
                },
                {
                  code: "RECOVERY_DECISION_DEADLINE",
                  label: "Recovery decision deadline",
                  due_after_seconds: 1800,
                  effect: {
                    risk: { level: "CRITICAL" },
                    mission: {
                      decision_status: "EXPIRED",
                      escalation_status: "DEADLINE_MISSED",
                    },
                  },
                  terminal_status: "TIME_EXPIRED",
                  visibility: "CANDIDATE",
                  cancellable: true,
                  cancel_condition: {
                    type: "WORLD_STATE_EQUALS",
                    path: "mission.decision_status",
                    equals: "COMMITTED",
                    reason_code: "DECISION_COMMITTED",
                  },
                },
                {
                  code: "RECOVERY_COMMITMENT_BROADCAST",
                  label: "Recovery commitment broadcast",
                  trigger_condition: {
                    type: "WORLD_STATE_EQUALS",
                    path: "mission.decision_status",
                    equals: "COMMITTED",
                  },
                  effect: {
                    stakeholder: { recovery_signal: "BROADCAST" },
                  },
                  visibility: "CANDIDATE",
                  cancellable: true,
                  cancel_condition: {
                    type: "WORLD_STATE_EQUALS",
                    path: "mission.decision_status",
                    equals: "EXPIRED",
                    reason_code: "DECISION_EXPIRED",
                  },
                },
              ],
            },
          ],
          no_action_options: [
            {
              code: "WAIT_30_MINUTES",
              label: "۳۰ دقیقه بدون اقدام جدید صبر می‌کنم",
              wait_seconds: 1800,
            },
          ],
          decision_options: [
            {
              code: "ROLLBACK_AND_RECOVER",
              label: "Rollback کنترل‌شده و برنامه بازیابی",
            },
          ],
          decision_effects: {
            ROLLBACK_AND_RECOVER: {
              business: { rollout_status: "RECOVERING" },
              technical: { rollback_started: true },
              risk: { level: "MEDIUM" },
              mission: { decision_status: "COMMITTED" },
            },
          },
          complete_after_decision: true,
        },
      },
      actors: [
        {
          name: "Business Sponsor",
          goal: actorGoal.trim(),
          authority: "Can pause rollout and request an executive update.",
        },
        {
          name: "Delivery Lead",
          goal: "هماهنگی اجرای recovery و گزارش وضعیت عملیاتی",
          authority: "Can coordinate rollback execution and operational follow-up.",
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
        {assignmentMessage ? <p className="success-note">{assignmentMessage}</p> : null}
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
                  {version.status === "ACTIVE" ? (
                    <div className="mission-assignment-box">
                      <label>
                        Candidate برای Assignment
                        <select
                          aria-label="Candidate برای Assignment"
                          value={assignmentCandidateId}
                          onChange={(event) => setAssignmentCandidateId(event.target.value)}
                        >
                          {assignmentCandidates.map((candidate) => (
                            <option key={candidate.id} value={candidate.id}>
                              {candidate.display_name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        className="primary"
                        disabled={busy || !assignmentCandidateId}
                        onClick={async () => {
                          await onAssign(version.id, assignmentCandidateId);
                          setAssignmentMessage("Mission Assignment ثبت شد.");
                        }}
                      >
                        اختصاص مأموریت
                      </button>
                      <div className="assignment-list">
                        {assignments
                          .filter((item) => item.mission_version_id === version.id)
                          .map((item) => (
                            <small key={item.id}>
                              {item.candidate_name} · {item.status}
                            </small>
                          ))}
                      </div>
                    </div>
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
