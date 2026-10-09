import { useState } from "react";
import type { CandidateHomeResponse } from "../api/client";

function practiceKindLabel(value?: string | null) {
  if (value === "CASE_STUDY") return "مطالعه موردی";
  if (value === "GUIDED_EXERCISE") return "تمرین هدایت‌شده";
  if (value === "WORKSHOP") return "کارگاه";
  if (value === "GROUP_EXERCISE") return "تمرین گروهی";
  return "تمرین";
}

function learningStateLabel(value: string) {
  if (value === "TO_LEARN") return "هنوز شروع نشده";
  if (value === "IN_LEARNING") return "در حال یادگیری";
  if (value === "LEARNING_COMPLETED") return "الزامات آموزشی تکمیل شده";
  return value;
}

function proofStateLabel(value: string) {
  if (value === "UNPROVEN") return "هنوز اثبات نشده";
  return value;
}

function activityStateLabel(value: string) {
  if (value === "NOT_STARTED") return "شروع نشده";
  if (value === "IN_PROGRESS") return "در حال انجام";
  if (value === "COMPLETED") return "تکمیل‌شده";
  if (value === "SUBMITTED") return "ارسال‌شده";
  if (value === "FEEDBACK_PROVIDED") return "بازخورد ثبت‌شده";
  return value;
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

type Props = {
  data: CandidateHomeResponse;
  onUpdateLearningUnit?: (
    learningUnitId: string,
    action: "start" | "complete",
  ) => Promise<void>;
  updatingLearningUnitId?: string;
  onSubmitPracticeAttempt?: (learningUnitId: string, response: string) => Promise<void>;
  submittingPracticeUnitId?: string;
  onSubmitAssignment?: (assignmentId: string, content: string) => Promise<void>;
  submittingAssignmentId?: string;
};

export function CandidateHome({
  data,
  onUpdateLearningUnit,
  updatingLearningUnitId,
  onSubmitPracticeAttempt,
  submittingPracticeUnitId,
  onSubmitAssignment,
  submittingAssignmentId,
}: Props) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null);

  const learningTasks = data.learning_tasks ?? [];
  const preWork = learningTasks.filter((item) => item.task_type === "PRE_WORK");
  const practice = learningTasks.filter((item) => item.task_type === "PRACTICE");
  const assignments = learningTasks.filter((item) => item.task_type === "ASSIGNMENT");

  async function updateUnit(learningUnitId: string, action: "start" | "complete") {
    if (!onUpdateLearningUnit) return;
    await onUpdateLearningUnit(learningUnitId, action);
  }

  async function submitPractice(learningUnitId: string) {
    const response = (drafts[`practice-${learningUnitId}`] ?? "").trim();
    if (!response || !onSubmitPracticeAttempt) return;
    await onSubmitPracticeAttempt(learningUnitId, response);
    setSubmittedMessage("تمرین ثبت شد. این ثبت به‌تنهایی به معنی پذیرش شاهد رسمی نیست.");
  }

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
        <span className="status-chip">{data.journey?.state === "ACTIVE" ? "در جریان" : data.journey?.state ?? "—"}</span>
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
                  <p>{item.next_session?.title ?? "جلسه بعدی ثبت نشده است."}</p>
                  <small>{formatDate(item.next_session?.starts_at)}</small>
                </div>
                <span className="state">{learningStateLabel(item.learning_state)}</span>
              </div>
            ))}
            {(data.what_to_learn ?? []).length === 0 ? (
              <p className="muted" role="status">هنوز برنامه یادگیری قابل‌نمایشی ثبت نشده است.</p>
            ) : null}
          </div>
        </article>

        <article className="panel">
          <p className="eyebrow">PROVE</p>
          <h2>الان چه چیزی باید اثبات کنم؟</h2>
          <div className="stack">
            {(data.what_to_prove ?? []).map((item) => (
              <div className="proof-row" key={item.capability_version_id}>
                <span>{item.name}</span>
                <span className="state state-muted">{proofStateLabel(item.proof_state)}</span>
              </div>
            ))}
            {(data.what_to_prove ?? []).length === 0 ? (
              <p className="muted" role="status">هنوز داده‌ای برای نمایش اثبات رسمی ثبت نشده است؛ نبود داده به معنای ضعف نیست.</p>
            ) : null}
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
                <div className="assignment-head">
                  <strong>{item.title}</strong>
                  <span className="state">{activityStateLabel(item.status)}</span>
                </div>
                <p>{item.body}</p>
                {item.status === "NOT_STARTED" ? (
                  <button
                    className="primary"
                    disabled={!onUpdateLearningUnit || updatingLearningUnitId === item.id}
                    onClick={() => void updateUnit(item.id, "start")}
                  >
                    {updatingLearningUnitId === item.id ? "در حال ثبت..." : "شروع"}
                  </button>
                ) : item.status === "IN_PROGRESS" ? (
                  <button
                    className="primary"
                    disabled={!onUpdateLearningUnit || updatingLearningUnitId === item.id}
                    onClick={() => void updateUnit(item.id, "complete")}
                  >
                    {updatingLearningUnitId === item.id ? "در حال ثبت..." : "تکمیل فعالیت"}
                  </button>
                ) : item.status === "COMPLETED" ? (
                  <p className="success-note">این فعالیت یادگیری تکمیل شده است.</p>
                ) : (
                  <p className="muted" role="status">وضعیت فعالیت نیازمند بررسی است؛ امکان ثبت تغییر وجود ندارد.</p>
                )}
              </div>
            ))}
            {preWork.length === 0 ? <p className="muted">پیش‌کاری فعالی ندارید.</p> : null}
          </div>
        </article>

        <article className="panel">
          <p className="eyebrow">PRACTICE</p>
          <h2>تمرین و Replay</h2>
          <div className="stack">
            {practice.map((item) => {
              const attempts = item.practice_attempts ?? [];
              const canSubmit = attempts.length === 0 || item.replay_available === true;
              const draftKey = `practice-${item.id}`;
              return (
                <div className="learning-card" key={item.id}>
                  <div className="assignment-head">
                    <div>
                      <strong>{item.title}</strong>
                      <p className="muted">{practiceKindLabel(item.practice_kind)}</p>
                    </div>
                    <span className="state">
                      {attempts.length > 0 ? `تلاش ثبت‌شده: ${attempts.length.toLocaleString("fa-IR")}` : activityStateLabel(item.status)}
                    </span>
                  </div>
                  <p>{item.body}</p>

                  {attempts.length > 0 ? (
                    <div className="attempt-history" data-testid="candidate-practice-history">
                      {attempts.map((attempt) => (
                        <div className="submission-summary" key={attempt.id}>
                          <div className="assignment-head">
                            <b>تلاش {attempt.attempt_number}</b>
                            <span className="state">{activityStateLabel(attempt.status)}</span>
                          </div>
                          <p>{attempt.response_text}</p>
                          {(attempt.feedback_history ?? []).map((feedback) => (
                            <p
                              key={feedback.id}
                              data-testid={`candidate-practice-feedback-${attempt.attempt_number}`}
                            >
                              <b>بازخورد مدرس:</b> {feedback.feedback_text}
                            </p>
                          ))}
                          {(attempt.feedback_history ?? []).length === 0 ? (
                            <p className="muted">در انتظار بازخورد مدرس.</p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}

                  {canSubmit ? (
                    <div className="form-stack">
                      <label htmlFor={draftKey}>
                        {attempts.length === 0 ? "پاسخ تمرین" : "پاسخ Replay"}
                      </label>
                      <textarea
                        id={draftKey}
                        value={drafts[draftKey] ?? ""}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [draftKey]: event.target.value,
                          }))
                        }
                        placeholder={
                          attempts.length === 0
                            ? "رویکرد، تصمیم و منطق خود را بنویسید..."
                            : "با استفاده از بازخورد قبلی، تلاش بعدی خود را بنویسید..."
                        }
                      />
                      <button
                        className="primary"
                        disabled={
                          !onSubmitPracticeAttempt ||
                          submittingPracticeUnitId === item.id ||
                          !(drafts[draftKey] ?? "").trim()
                        }
                        onClick={() => void submitPractice(item.id)}
                      >
                        {submittingPracticeUnitId === item.id
                          ? "در حال ثبت..."
                          : attempts.length === 0
                            ? "ثبت تمرین"
                            : "ثبت Replay"}
                      </button>
                    </div>
                  ) : (
                    <p className="muted">برای Replay بعدی ابتدا باید بازخورد تلاش فعلی ثبت شود.</p>
                  )}
                </div>
              );
            })}
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
                  <span className="state">{activityStateLabel(item.status)}</span>
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
