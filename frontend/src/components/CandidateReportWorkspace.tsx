import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { makeApi } from "../api/client";

export type CandidateClass = {
  class_offering_id: string;
  cohort_id: string;
  title: string;
  primary_capability_version_id: string;
  status: string;
};

type Attendance = {
  session_id: string;
  title: string;
  starts_at: string;
  status: "PRESENT" | "ABSENT" | "NOT_RECORDED";
  attendance_record_id: string | null;
};

type LearningSource = {
  source_type: string;
  source_id: string;
  parent_id?: string | null;
  title?: string | null;
  state?: string | null;
  state_source_id?: string | null;
};

type FeedbackSource = {
  source_type: string;
  source_id: string;
  feedback_text: string;
  created_at: string;
};

type Subject = {
  capability_version_id: string;
  capability_name: string | null;
  capability_version_number: number | null;
  learning_state: string | null;
  proof_state: string | null;
  next_learning_focus: string | null;
  reviewed_claim: {
    claim_id: string;
    claim_version: number;
    claim_state: string;
    level: string;
    reviewed_at: string;
  } | null;
  learning_sources: LearningSource[];
  feedback_sources: FeedbackSource[];
};

export type CandidateClassReport = {
  class_offering_id: string;
  cohort_id: string;
  person_id: string;
  attendance_scope: "CLASS_OFFERING";
  attendance: Attendance[];
  subjects: Subject[];
};

function learningLabel(state: string | null) {
  if (state === "TO_LEARN") return "هنوز شروع نشده";
  if (state === "IN_LEARNING") return "در حال یادگیری";
  if (state === "LEARNING_COMPLETED") return "الزامات آموزشی تکمیل شده";
  return "وضعیت آموزشی مشخص نیست";
}

function attendanceLabel(status: Attendance["status"]) {
  if (status === "PRESENT") return "حاضر";
  if (status === "ABSENT") return "غایب (ثبت‌شده)";
  return "حضور و غیاب هنوز ثبت نشده";
}

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "medium",
  }).format(new Date(value));
}

export function CandidateReportCardView({
  classes,
  selectedClassId,
  onSelectClass,
  report,
  loading,
  error,
}: {
  classes: CandidateClass[];
  selectedClassId?: string;
  onSelectClass: (id: string) => void;
  report?: CandidateClassReport;
  loading: boolean;
  error?: string;
}) {
  return (
    <main className="page-shell" data-testid="candidate-report-workspace">
      <section className="panel">
        <p className="eyebrow">REPORT CARD</p>
        <h2>کارنامه کیفی درس‌های من</h2>
        <p className="muted">
          این کارنامه فعالیت آموزشی و بازخورد ثبت‌شده را نمایش می‌دهد؛ نمره، رتبه یا تصمیم
          خودکار درباره شایستگی صادر نمی‌کند.
        </p>
        {classes.length === 0 ? (
          <p className="muted" role="status">در این گروه آموزشی هنوز کلاسی ثبت نشده است.</p>
        ) : (
          <div className="form-stack">
            <label htmlFor="candidate-report-class">انتخاب کلاس</label>
            <select
              id="candidate-report-class"
              value={selectedClassId ?? ""}
              onChange={(event) => onSelectClass(event.target.value)}
            >
              {classes.map((item) => (
                <option key={item.class_offering_id} value={item.class_offering_id}>
                  {item.title}
                </option>
              ))}
            </select>
          </div>
        )}
      </section>
      {error ? <section className="panel error" role="alert">{error}</section> : null}
      {loading ? <section className="panel" role="status">در حال دریافت کارنامه...</section> : null}
      {report && !error && !loading ? (
        <>
          <section className="panel">
            <h2>حضور و غیاب کلاس</h2>
            <p className="muted">ثبت‌نشدن حضور، به معنی غیبت نیست.</p>
            <div className="stack">
              {report.attendance.map((entry) => (
                <div className="task-card" key={entry.session_id}>
                  <div>
                    <strong>{entry.title}</strong>
                    <p className="muted">{dateLabel(entry.starts_at)}</p>
                  </div>
                  <span className="state state-muted">{attendanceLabel(entry.status)}</span>
                </div>
              ))}
              {report.attendance.length === 0 ? (
                <p className="muted">هنوز جلسه‌ای برای این کلاس ثبت نشده است.</p>
              ) : null}
            </div>
          </section>
          <section className="panel">
            <h2>درس‌ها و بازخوردها</h2>
            {report.subjects.length === 0 ? (
              <p className="muted">هنوز درس قابل‌نمایشی برای این کلاس ثبت نشده است.</p>
            ) : null}
            <div className="stack">
              {report.subjects.map((subject) => (
                <article className="report-subject-card" key={subject.capability_version_id}>
                  <div className="assignment-head">
                    <h3>{subject.capability_name ?? "عنوان درس در دسترس نیست"}</h3>
                    <span className="state">{learningLabel(subject.learning_state)}</span>
                  </div>
                  <p className="muted">
                    نسخه درس: {subject.capability_version_number ?? "نامشخص"}
                  </p>
                  <p>
                    <strong>اثبات رسمی مستقل:</strong>{" "}
                    {subject.proof_state ?? "وضعیت معتبر در این کارنامه ارائه نشده است."}
                  </p>
                  {subject.reviewed_claim ? (
                    <p>
                      <strong>Claim بازبینی‌شده انسانی:</strong>{" "}
                      {subject.reviewed_claim.claim_state} · {subject.reviewed_claim.level} ·{" "}
                      {dateLabel(subject.reviewed_claim.reviewed_at)}
                      <small className="muted" dir="ltr">
                        {" "}({subject.reviewed_claim.claim_id})
                      </small>
                    </p>
                  ) : (
                    <p className="muted">برای این درس Claim بازبینی‌شده‌ای در دسترس نیست.</p>
                  )}
                  <p className="muted">
                    تمرکز آموزشی بعدی: {subject.next_learning_focus ?? "هنوز تعیین نشده است."}
                  </p>
                  <h4>فعالیت‌های ثبت‌شده</h4>
                  {subject.learning_sources.length === 0 ? (
                    <p className="muted">داده فعالیت آموزشی ثبت نشده است.</p>
                  ) : (
                    <ul className="runtime-timeline">
                      {subject.learning_sources.map((item) => (
                        <li key={`${item.source_type}-${item.source_id}`}>
                          {item.title ?? item.source_type} · {item.state ?? "بدون وضعیت ثبت‌شده"}
                          <small className="muted" dir="ltr">{" "}({item.source_id})</small>
                        </li>
                      ))}
                    </ul>
                  )}
                  <h4>بازخورد مدرس</h4>
                  {subject.feedback_sources.length === 0 ? (
                    <p className="muted">هنوز بازخوردی ثبت نشده است.</p>
                  ) : (
                    <ul className="runtime-timeline">
                      {subject.feedback_sources.map((item) => (
                        <li key={item.source_id}>
                          {item.feedback_text}
                          <small className="muted">
                            {" "}· {dateLabel(item.created_at)}
                          </small>
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}

export function CandidateReportWorkspace({
  accessToken,
  organizationId,
  personId,
  cohortId,
}: {
  accessToken: string;
  organizationId: string;
  personId: string;
  cohortId: string;
}) {
  const api = makeApi(accessToken);
  const [chosenClassId, setChosenClassId] = useState<string>();
  const classes = useQuery({
    queryKey: ["candidate-class-offerings", organizationId, personId, cohortId],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/cohorts/{cohort_id}/class-offerings", {
        params: { path: { cohort_id: cohortId } },
      });
      if (error || !data) throw new Error("دریافت فهرست کلاس‌های مجاز ناموفق بود.");
      return data as CandidateClass[];
    },
  });
  const selectedClassId = classes.data?.some(
    (item) => item.class_offering_id === chosenClassId,
  )
    ? chosenClassId
    : classes.data?.[0]?.class_offering_id;

  const report = useQuery({
    queryKey: ["candidate-class-report", organizationId, personId, selectedClassId],
    enabled: Boolean(selectedClassId),
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/class-offerings/{class_offering_id}/report-cards/{person_id}",
        {
          params: {
            path: {
              class_offering_id: selectedClassId ?? "",
              person_id: personId,
            },
          },
        },
      );
      if (error || !data) throw new Error("دریافت کارنامه کلاس ناموفق بود.");
      return data as CandidateClassReport;
    },
  });

  if (classes.isPending) {
    return <main className="page-shell" role="status">در حال دریافت کلاس‌ها...</main>;
  }
  if (classes.isError) {
    return <main className="page-shell error" role="alert">{classes.error.message}</main>;
  }

  return (
    <CandidateReportCardView
      classes={classes.data}
      selectedClassId={selectedClassId}
      onSelectClass={setChosenClassId}
      report={report.data}
      loading={Boolean(selectedClassId) && report.isPending}
      error={report.isError ? report.error.message : undefined}
    />
  );
}
