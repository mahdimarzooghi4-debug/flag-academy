import { useState } from "react";
import type { InstructorHomeResponse } from "../api/client";

type Props = {
  data: InstructorHomeResponse;
  onRecordPracticeFeedback?: (
    practiceAttemptId: string,
    feedback: string,
  ) => Promise<void>;
  submittingPracticeFeedbackId?: string;
  onRecordFeedback?: (submissionId: string, feedback: string) => Promise<void>;
  submittingFeedbackId?: string;
};

export function InstructorHome({
  data,
  onRecordPracticeFeedback,
  submittingPracticeFeedbackId,
  onRecordFeedback,
  submittingFeedbackId,
}: Props) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  async function savePracticeFeedback(practiceAttemptId: string) {
    const feedback = (drafts[`practice-${practiceAttemptId}`] ?? "").trim();
    if (!feedback || !onRecordPracticeFeedback) return;
    await onRecordPracticeFeedback(practiceAttemptId, feedback);
    setSavedMessage(
      "بازخورد تمرین ثبت شد. این بازخورد توسعه‌ای است و Evidence مستقل محسوب نمی‌شود.",
    );
  }

  async function saveFeedback(submissionId: string) {
    const feedback = (drafts[submissionId] ?? "").trim();
    if (!feedback || !onRecordFeedback) return;
    await onRecordFeedback(submissionId, feedback);
    setSavedMessage(
      "بازخورد ثبت شد. بازخورد آموزشی مستقیماً Capability را Proven نمی‌کند.",
    );
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">فضای مدرس</p>
          <h1>{data.assigned_cohort?.name ?? "کلاس‌های من"}</h1>
          <p className="muted">{data.current_wave?.name ?? "—"}</p>
        </div>
        <div className="metric">
          <strong>{data.candidate_count ?? 0}</strong>
          <span>فراگیر</span>
        </div>
      </section>

      <section className="grid-two">
        <article className="panel">
          <p className="eyebrow">کلاس‌ها</p>
          <h2>کلاس‌های واگذارشده</h2>
          <div className="stack">
            {(data.assigned_classes ?? []).map((item) => (
              <div className="proof-row" key={item.id}>
                <span>{item.title}</span>
                <span className="state">فعال</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <p className="eyebrow">تمرکز آموزشی</p>
          <h2>{data.capability_focus ?? "—"}</h2>
          <p className="muted">
            بازخورد مدرس به یادگیری کمک می‌کند، اما به‌تنهایی Capability را Proven نمی‌کند.
          </p>
        </article>
      </section>

      <section className="grid-two">
        <article className="panel">
          <p className="eyebrow">LEARNING UNITS</p>
          <h2>محتوای کلاس</h2>
          <div className="stack">
            {(data.learning_units ?? []).map((item) => (
              <div className="learning-card" key={item.id}>
                <div className="assignment-head">
                  <strong>{item.title}</strong>
                  <span className="state">{item.phase}</span>
                </div>
                <p>{item.body}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <p className="eyebrow">ASSIGNMENTS</p>
          <h2>تکلیف‌های کلاس</h2>
          <div className="stack">
            {(data.assignments ?? []).map((item) => (
              <div className="learning-card" key={item.id}>
                <strong>{item.title}</strong>
                <p>{item.instructions}</p>
                <span className="state">{item.status}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">PRACTICE ATTEMPTS</p>
            <h2>تمرین‌های ثبت‌شده</h2>
          </div>
          <span className="count">{data.practice_attempts?.length ?? 0}</span>
        </div>
        <div className="stack">
          {(data.practice_attempts ?? []).map((item) => (
            <div className="assignment-card" key={item.id}>
              <div className="assignment-head">
                <div>
                  <strong>{item.practice_title} — تلاش {item.attempt_number}</strong>
                  <p className="muted">
                    {item.candidate_name}
                    {item.replay_of_attempt_id ? " · Replay" : " · اولین تلاش"}
                  </p>
                </div>
                <span className="state">{item.status}</span>
              </div>
              <div className="submission-body">
                <b>پاسخ تمرین</b>
                <p>{item.response_text}</p>
              </div>
              {(item.feedback_history ?? []).length > 0 ? (
                <div className="submission-summary">
                  <b>تاریخچه بازخورد</b>
                  {(item.feedback_history ?? []).map((feedback) => (
                    <p
                      key={feedback.id}
                      data-testid={`instructor-practice-feedback-${item.attempt_number}`}
                    >
                      {feedback.feedback_text}
                    </p>
                  ))}
                </div>
              ) : (
                <div className="form-stack">
                  <label htmlFor={`practice-feedback-${item.id}`}>
                    بازخورد تمرین {item.attempt_number}
                  </label>
                  <textarea
                    id={`practice-feedback-${item.id}`}
                    value={drafts[`practice-${item.id}`] ?? ""}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [`practice-${item.id}`]: event.target.value,
                      }))
                    }
                    placeholder="بازخورد توسعه‌ای و قابل اقدام بنویسید..."
                  />
                  <button
                    className="primary"
                    disabled={
                      !onRecordPracticeFeedback ||
                      submittingPracticeFeedbackId === item.id ||
                      !(drafts[`practice-${item.id}`] ?? "").trim()
                    }
                    onClick={() => void savePracticeFeedback(item.id)}
                  >
                    {submittingPracticeFeedbackId === item.id
                      ? "در حال ثبت..."
                      : "ثبت بازخورد تمرین"}
                  </button>
                </div>
              )}
            </div>
          ))}
          {(data.practice_attempts ?? []).length === 0 ? (
            <p className="muted">هنوز تمرینی برای بازخورد ثبت نشده است.</p>
          ) : null}
        </div>
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">SUBMISSIONS</p>
            <h2>ارسال‌های فراگیران</h2>
          </div>
          <span className="count">{data.submissions?.length ?? 0}</span>
        </div>
        {savedMessage ? <p className="success-note">{savedMessage}</p> : null}
        <div className="stack">
          {(data.submissions ?? []).map((item) => (
            <div className="assignment-card" key={item.id}>
              <div className="assignment-head">
                <div>
                  <strong>{item.assignment_title}</strong>
                  <p className="muted">{item.candidate_name}</p>
                </div>
                <span className="state">{item.status}</span>
              </div>
              <div className="submission-body">
                <b>پاسخ فراگیر</b>
                <p>{item.content_text}</p>
              </div>
              {item.feedback_text ? (
                <div className="submission-summary">
                  <b>آخرین بازخورد</b>
                  <p data-testid="instructor-feedback">{item.feedback_text}</p>
                </div>
              ) : (
                <div className="form-stack">
                  <label htmlFor={`feedback-${item.id}`}>بازخورد مدرس</label>
                  <textarea
                    id={`feedback-${item.id}`}
                    value={drafts[item.id] ?? ""}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [item.id]: event.target.value,
                      }))
                    }
                    placeholder="بازخورد مشخص و قابل اقدام بنویسید..."
                  />
                  <button
                    className="primary"
                    disabled={
                      !onRecordFeedback ||
                      submittingFeedbackId === item.id ||
                      !(drafts[item.id] ?? "").trim()
                    }
                    onClick={() => void saveFeedback(item.id)}
                  >
                    {submittingFeedbackId === item.id ? "در حال ثبت..." : "ثبت بازخورد"}
                  </button>
                </div>
              )}
            </div>
          ))}
          {(data.submissions ?? []).length === 0 ? (
            <p className="muted">هنوز ارسالی برای بررسی وجود ندارد.</p>
          ) : null}
        </div>
      </section>
    </main>
  );
}
