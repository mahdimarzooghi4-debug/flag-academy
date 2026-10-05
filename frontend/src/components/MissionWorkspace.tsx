import { useMemo, useState } from "react";

export type MissionCatalogItem = {
  version_id: string;
  template_id: string;
  code: string;
  title: string;
  purpose: string;
  difficulty: string;
  decision_points: Array<Record<string, unknown>>;
  information_options: Array<{ label?: string; access?: string }>;
  decision_options: Array<{ code?: string; label?: string }>;
};

export type MissionRuntimeEvent = {
  id: string;
  sequence_number: number;
  event_type: string;
  source: string;
  visibility: string;
  payload: Record<string, unknown>;
  world_version_before: number;
  world_version_after: number;
  occurred_at: string;
};

export type MissionObservation = {
  id: string;
  source_event_id: string;
  sequence_number: number;
  observation_type: string;
  factual_statement: string;
  payload: Record<string, unknown>;
  occurred_at: string;
};

export type MissionInstance = {
  id: string;
  version: number;
  mission_version_id: string;
  template_id: string;
  mission_code: string;
  title: string;
  status: string;
  world_state: Record<string, unknown>;
  world_state_version: number;
  simulation_seed: number;
  decision_points: Array<Record<string, unknown>>;
  information_options: Array<{ label?: string; access?: string }>;
  decision_options: Array<{ code?: string; label?: string }>;
  disclosed_information: Array<{ label?: string; content?: string; access?: string }>;
  audit_events: MissionRuntimeEvent[];
  observations: MissionObservation[];
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
};

type Props = {
  missions: MissionCatalogItem[];
  instances: MissionInstance[];
  onStart: (versionId: string) => Promise<void>;
  onRequestInformation: (
    instanceId: string,
    worldVersion: number,
    label: string,
  ) => Promise<void>;
  onDecide: (
    instanceId: string,
    worldVersion: number,
    decisionCode: string,
    reasoning: string,
  ) => Promise<void>;
  busy?: boolean;
};

export function MissionWorkspace({
  missions,
  instances,
  onStart,
  onRequestInformation,
  onDecide,
  busy,
}: Props) {
  const [reasoningByInstance, setReasoningByInstance] = useState<Record<string, string>>({});

  const instanceByVersion = useMemo(() => {
    const map = new Map<string, MissionInstance>();
    for (const instance of instances) {
      const current = map.get(instance.mission_version_id);
      if (!current || current.created_at < instance.created_at) {
        map.set(instance.mission_version_id, instance);
      }
    }
    return map;
  }, [instances]);

  return (
    <section className="panel">
      <div className="section-title">
        <div>
          <p className="eyebrow">MISSION RUNTIME</p>
          <h2>مأموریت‌های شبیه‌سازی</h2>
          <p className="muted">
            تصمیم‌ها World State را تغییر می‌دهند و Observation واقعی ثبت می‌شود؛
            این Observation هنوز Evidence یا تغییر Profile نیست.
          </p>
        </div>
        <span className="count">{missions.length}</span>
      </div>

      <div className="stack">
        {missions.map((mission) => {
          const instance = instanceByVersion.get(mission.version_id);
          const reasoning = instance ? reasoningByInstance[instance.id] ?? "" : "";

          return (
            <article
              key={mission.version_id}
              className="assignment-card mission-runtime-card"
            >
              <div className="assignment-head">
                <div>
                  <strong>{mission.title}</strong>
                  <p>{mission.code} · {mission.difficulty}</p>
                </div>
                <span className="state" data-testid="runtime-status">
                  {instance?.status ?? "READY TO START"}
                </span>
              </div>
              <p>{mission.purpose}</p>

              {!instance ? (
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => void onStart(mission.version_id)}
                >
                  شروع مأموریت
                </button>
              ) : (
                <>
                  <div className="runtime-meta">
                    <span>World v{instance.world_state_version}</span>
                    <span>Seed {instance.simulation_seed}</span>
                  </div>

                  {instance.status === "RUNNING" ? (
                    <>
                      <div className="runtime-block">
                        <strong>اطلاعات قابل درخواست</strong>
                        <div className="action-row">
                          {instance.information_options.map((item) => {
                            const label = item.label ?? "";
                            return (
                              <button
                                key={label}
                                className="ghost dark"
                                disabled={busy || !label}
                                onClick={() =>
                                  void onRequestInformation(
                                    instance.id,
                                    instance.world_state_version,
                                    label,
                                  )
                                }
                              >
                                درخواست {label}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {instance.disclosed_information.length > 0 ? (
                        <div className="runtime-block">
                          <strong>اطلاعات آشکارشده</strong>
                          {instance.disclosed_information.map((item, index) => (
                            <p key={`${item.label ?? "info"}-${index}`}>
                              <b>{item.label}</b>: {item.content}
                            </p>
                          ))}
                        </div>
                      ) : null}

                      <div className="form-stack">
                        <label htmlFor={`mission-reasoning-${instance.id}`}>
                          منطق تصمیم
                        </label>
                        <textarea
                          id={`mission-reasoning-${instance.id}`}
                          aria-label="منطق تصمیم"
                          value={reasoning}
                          onChange={(event) =>
                            setReasoningByInstance((current) => ({
                              ...current,
                              [instance.id]: event.target.value,
                            }))
                          }
                          placeholder="فرض‌ها، trade-off و دلیل تصمیم را ثبت کنید."
                        />
                      </div>
                      <div className="action-row">
                        {instance.decision_options.map((option) => {
                          const code = option.code ?? "";
                          const label = option.label ?? code;
                          return (
                            <button
                              key={code}
                              className="primary"
                              disabled={busy || !code || !reasoning.trim()}
                              onClick={() =>
                                void onDecide(
                                  instance.id,
                                  instance.world_state_version,
                                  code,
                                  reasoning.trim(),
                                )
                              }
                            >
                              {label}
                            </button>
                          );
                        })}
                      </div>
                    </>
                  ) : null}

                  <div className="runtime-block">
                    <strong>World State</strong>
                    <pre data-testid="world-state">
                      {JSON.stringify(instance.world_state, null, 2)}
                    </pre>
                  </div>

                  {instance.observations.length > 0 ? (
                    <div className="runtime-block">
                      <strong>Observation Timeline</strong>
                      <ol className="runtime-timeline">
                        {instance.observations.map((observation) => (
                          <li key={observation.id}>
                            <span className="mode">{observation.observation_type}</span>
                            <p>{observation.factual_statement}</p>
                          </li>
                        ))}
                      </ol>
                    </div>
                  ) : null}

                  <details className="runtime-block">
                    <summary>Audit events ({instance.audit_events.length})</summary>
                    <ol className="runtime-timeline">
                      {instance.audit_events.map((event) => (
                        <li key={event.id}>
                          #{event.sequence_number} {event.event_type} · World{" "}
                          {event.world_version_before}→{event.world_version_after}
                        </li>
                      ))}
                    </ol>
                  </details>
                </>
              )}
            </article>
          );
        })}
        {missions.length === 0 ? (
          <p className="muted">هنوز Mission فعال قابل اجرا وجود ندارد.</p>
        ) : null}
      </div>
    </section>
  );
}
