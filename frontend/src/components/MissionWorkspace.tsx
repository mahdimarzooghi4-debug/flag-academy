import { useMemo, useState } from "react";

export type MissionCatalogItem = {
  assignment_id: string;
  assignment_status: string;
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

export type MissionScheduledEffect = {
  id: string;
  effect_code: string;
  status: string;
  due_at: string;
  message?: string | null;
  applied_at?: string | null;
  cancelled_at?: string | null;
};

export type MissionActorInstance = {
  id: string;
  actor_key: string;
  display_name: string;
  state: Record<string, unknown>;
  state_version: number;
  communication_options: Array<{ code: string; label: string }>;
};

export type MissionInstance = {
  id: string;
  version: number;
  assignment_id?: string | null;
  mission_version_id: string;
  template_id: string;
  mission_code: string;
  title: string;
  status: string;
  runtime_phase: string;
  world_state: Record<string, unknown>;
  world_state_version: number;
  decision_points: Array<Record<string, unknown>>;
  information_options: Array<{ label?: string; access?: string }>;
  decision_options: Array<{ code?: string; label?: string }>;
  escalation_options: Array<{ code: string; label: string; actor_key: string }>;
  actors: MissionActorInstance[];
  scheduled_effects: MissionScheduledEffect[];
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
  onStart: (versionId: string, assignmentId: string) => Promise<void>;
  onRequestInformation: (
    instanceId: string,
    worldVersion: number,
    label: string,
  ) => Promise<void>;
  onCommunicate: (
    instanceId: string,
    worldVersion: number,
    actorKey: string,
    actorVersion: number,
    communicationCode: string,
    utterance: string,
  ) => Promise<void>;
  onEscalate: (
    instanceId: string,
    worldVersion: number,
    actorKey: string,
    actorVersion: number,
    escalationCode: string,
    rationale: string,
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
  onCommunicate,
  onEscalate,
  onDecide,
  busy,
}: Props) {
  const [reasoningByInstance, setReasoningByInstance] = useState<Record<string, string>>({});
  const [utteranceByActor, setUtteranceByActor] = useState<Record<string, string>>({});
  const [escalationRationaleByInstance, setEscalationRationaleByInstance] =
    useState<Record<string, string>>({});

  const instanceByAssignment = useMemo(() => {
    const map = new Map<string, MissionInstance>();
    for (const instance of instances) {
      if (instance.assignment_id) {
        map.set(instance.assignment_id, instance);
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
          const instance = instanceByAssignment.get(mission.assignment_id);
          const reasoning = instance ? reasoningByInstance[instance.id] ?? "" : "";

          return (
            <article
              key={mission.assignment_id}
              className="assignment-card mission-runtime-card"
            >
              <div className="assignment-head">
                <div>
                  <strong>{mission.title}</strong>
                  <p>
                    {mission.code} · {mission.difficulty} · Assignment {mission.assignment_status}
                  </p>
                </div>
                <span className="state" data-testid="runtime-status">
                  {instance ? `${instance.status} · ${instance.runtime_phase}` : "READY TO START"}
                </span>
              </div>
              <p>{mission.purpose}</p>

              {!instance ? (
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => void onStart(mission.version_id, mission.assignment_id)}
                >
                  شروع مأموریت
                </button>
              ) : (
                <>
                  <div className="runtime-meta">
                    <span>World v{instance.world_state_version}</span>
                    <span>Candidate-visible state</span>
                  </div>

                  {instance.scheduled_effects.length > 0 ? (
                    <div className="runtime-block">
                      <strong>Delayed consequences</strong>
                      <div className="stack">
                        {instance.scheduled_effects.map((effect) => (
                          <div key={effect.id} data-testid={`scheduled-effect-${effect.effect_code}`}>
                            <p>
                              <b>{effect.effect_code}</b> · {effect.status}
                            </p>
                            {effect.message ? <p>{effect.message}</p> : null}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {instance.status === "RUNNING" ? (
                    <>
                      {instance.actors.length > 0 ? (
                        <div className="runtime-block">
                          <strong>تعامل با Actorها</strong>
                          <div className="stack">
                            {instance.actors.map((actor) => {
                              const utterance = utteranceByActor[actor.id] ?? "";
                              const responses = instance.audit_events.filter(
                                (event) =>
                                  event.event_type === "actor.responded" &&
                                  event.payload.actor_key === actor.actor_key,
                              );
                              return (
                                <div key={actor.id} className="actor-runtime-card">
                                  <div className="assignment-head">
                                    <div>
                                      <b>{actor.display_name}</b>
                                      <p>{actor.actor_key} · Actor v{actor.state_version}</p>
                                    </div>
                                  </div>
                                  <pre data-testid={`actor-state-${actor.actor_key}`}>
                                    {JSON.stringify(actor.state, null, 2)}
                                  </pre>
                                  <label>
                                    پیام به {actor.display_name}
                                    <textarea
                                      aria-label={`پیام به ${actor.display_name}`}
                                      value={utterance}
                                      onChange={(event) =>
                                        setUtteranceByActor((current) => ({
                                          ...current,
                                          [actor.id]: event.target.value,
                                        }))
                                      }
                                      placeholder="پیام واقعی خود را به Actor بنویسید."
                                    />
                                  </label>
                                  <div className="action-row">
                                    {actor.communication_options.map((option) => (
                                      <button
                                        key={option.code}
                                        className="ghost dark"
                                        disabled={busy || !utterance.trim()}
                                        onClick={() =>
                                          void onCommunicate(
                                            instance.id,
                                            instance.world_state_version,
                                            actor.actor_key,
                                            actor.state_version,
                                            option.code,
                                            utterance.trim(),
                                          )
                                        }
                                      >
                                        {option.label}
                                      </button>
                                    ))}
                                  </div>
                                  {responses.map((response) => (
                                    <p key={response.id} className="success-note">
                                      پاسخ {actor.display_name}: {String(response.payload.reply ?? "")}
                                    </p>
                                  ))}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ) : null}

                      {instance.escalation_options.length > 0 ? (
                        <div className="runtime-block">
                          <strong>Escalation</strong>
                          <label>
                            دلیل Escalation
                            <textarea
                              aria-label="دلیل Escalation"
                              value={escalationRationaleByInstance[instance.id] ?? ""}
                              onChange={(event) =>
                                setEscalationRationaleByInstance((current) => ({
                                  ...current,
                                  [instance.id]: event.target.value,
                                }))
                              }
                              placeholder="چرا این موضوع باید به سطح بالاتری Escalate شود؟"
                            />
                          </label>
                          <div className="action-row">
                            {instance.escalation_options.map((option) => {
                              const targetActor = instance.actors.find(
                                (actor) => actor.actor_key === option.actor_key,
                              );
                              const rationale =
                                escalationRationaleByInstance[instance.id] ?? "";
                              return (
                                <button
                                  key={option.code}
                                  className="ghost dark"
                                  disabled={
                                    busy ||
                                    !targetActor ||
                                    !rationale.trim()
                                  }
                                  onClick={() => {
                                    if (!targetActor) return;
                                    void onEscalate(
                                      instance.id,
                                      instance.world_state_version,
                                      targetActor.actor_key,
                                      targetActor.state_version,
                                      option.code,
                                      rationale.trim(),
                                    );
                                  }}
                                >
                                  {option.label}
                                </button>
                              );
                            })}
                          </div>
                          {instance.audit_events
                            .filter((event) => event.event_type === "escalation.accepted")
                            .map((event) => (
                              <p key={event.id} className="success-note">
                                نتیجه Escalation: {String(event.payload.response ?? "")}
                              </p>
                            ))}
                        </div>
                      ) : null}

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
                              disabled={
                                busy ||
                                instance.runtime_phase === "WAITING_FOR_WORLD" ||
                                !code ||
                                !reasoning.trim()
                              }
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
                    <strong>Candidate-visible World State</strong>
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
