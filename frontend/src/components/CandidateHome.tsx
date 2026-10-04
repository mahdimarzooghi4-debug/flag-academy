import { useState } from "react";
import type { CandidateHomeResponse } from "../api/client";

function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

type Props = {
  data: CandidateHomeResponse;
  onSubmitAssignment?: (assignmentId: string, content: string) => Promise<void>;
  submittingAssignmentId?: string;
};

export function CandidateHome({
  data,
  onSubmitAssignment,
  submittingAssignmentId,
}: Props) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null);

  const learningTasks = data.learning_tasks ?? [];
  const preWork = learningTasks.filter((item) => item.task_type === "PRE_WORK");
  const practice = learningTasks.filter((item) => item.task_type === "PRACTICE");
  const assignments = learningTasks.filter((item) => item.task_type === "ASSIGNMENT");

  async function submit(assignmentId: string) {
    const content = (drafts[assignmentId] ?? "").trim();
    if (!content || !onSubmitAssignment) return;
    await onSubmitAssignment(assignmentId, content);
    setSubmittedMessage("تکلیف ثبت شد. این ثبت به‌تنهایی به معنی اثبات شایستگی نیست.");
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">مسیر رشد من</p>
          <h1>{data.cohort?.name ?? "آکادمی پرچم"}</h1>
          <p className="muted">
            {data.journey?.track ?? "—"} · {data.current_wave?.name ?? "—"}
          </p>
        </div>
        <span className="status-chip">{data.journey?.state ?? "—"}</span>
      </section>

      <section className="grid-two">
        <article className="panel">
          <p className="eyebrow">LEARN</p>
          <h2>الان چه چیزی باید یاد بگیرم؟</h2>
          <div className="stack">
            {(data.what_to_learn ?? []).map((item) => (
              <div className="task-card" key={item.capability_version_id}>
                <div>
                  <strong>{item.name}</strong>
                  <p>{item.next_session?.title ?? "مسیر یادگیری برای این Capability فعال است."}</p>
                  <small>{formatDate(item.next_session?.starts_at)}</small>
                </div>
                <span className="state">{item.learning_state}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <p className="eyebrow">PROVE</p>
          <h2>الان چه چیزی باید اثبات کنم؟</h2>
          <div className="stack">
            {(data.what_to_prove ?? []).map((item) => (
              <div className="proof-row" key={item.capability_version_id}>
                <span>{item.name}</span>
                <span className="state state-muted">{item.proof_state}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="grid-two">
        <article className="panel">
          <p className="eyebrow">PRE-WORK</p>
          <h2>قبل از کلاس</h2>
          <div className="stack">
            {preWork.map((item) => (
              <div className="learning-card" key={item.id}>
                <strong>{item.title}</strong>
                <p>{item.body}</p>
                <span className="state">{item.status}</span>
              </div>
            ))}
            {preWork.length === 0 ? <p className="muted">پیش‌کاری فعالی ندارید.</p> : null}
          </div>
        </article>

        <article className="panel">
          <p className="eyebrow">PRACTICE</p>
          <h2>تمرین</h2>
          <div className="stack">
            {practice.map((item) => (
              <div className="learning-card" key={item.id}>
                <strong>{item.title}</strong>
                <p>{item.body}</p>
                <span className="state">{item.status}</span>
              </div>
            ))}
            {practice.length === 0 ? <p className="muted">تمرین فعالی ندارید.</p> : null}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">ASSIGNMENT</p>
            <h2>تکلیف‌ها</h2>
          </div>
          <span className="count">{assignments.length}</span>
        </div>
        {submittedMessage ? <p className="success-note">{submittedMessage}</p> : null}
        <div className="stack">
          {assignments.map((item) => {
            const isSubmitted =
              item.status === "SUBMITTED" || item.status === "FEEDBACK_PROVIDED";
            return (
              <div className="assignment-card" key={item.id}>
                <div className="assignment-head">
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.body}</p>
                    <small>مهلت: {formatDate(item.due_at)}</small>
                  </div>
                  <span className="state">{item.status}</span>
                </div>

                {isSubmitted ? (
                  <div className="submission-summary">
                    <strong>ارسال شما ثبت شده است.</strong>
                    {item.feedback_text ? (
                      <p data-testid="candidate-feedback">
                        <b>بازخورد مدرس:</b> {item.feedback_text}
                      </p>
                    ) : (
                      <p className="muted">در انتظار بازخورد مدرس.</p>
                    )}
                  </div>
                ) : (
                  <div className="form-stack">
                    <label htmlFor={`assignment-${item.id}`}>پاسخ تکلیف</label>
                    <textarea
                      id={`assignment-${item.id}`}
                      value={drafts[item.id] ?? ""}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [item.id]: event.target.value,
                        }))
                      }
                      placeholder="پاسخ خود را بنویسید..."
                    />
                    <button
                      className="primary"
                      disabled={
                        !onSubmitAssignment ||
                        submittingAssignmentId === item.id ||
                        !(drafts[item.id] ?? "").trim()
                      }
                      onClick={() => void submit(item.id)}
                    >
                      {submittingAssignmentId === item.id ? "در حال ثبت..." : "ثبت تکلیف"}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">تقویم</p>
            <h2>جلسه‌های پیش‌رو</h2>
          </div>
          <span className="count">{data.upcoming_sessions?.length ?? 0}</span>
        </div>
        <div className="stack">
          {(data.upcoming_sessions ?? []).map((session) => (
            <div className="session-row" key={session.session_id}>
              <strong>{session.title}</strong>
              <span>{formatDate(session.starts_at)}</span>
              <span className="mode">{session.delivery_mode}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
