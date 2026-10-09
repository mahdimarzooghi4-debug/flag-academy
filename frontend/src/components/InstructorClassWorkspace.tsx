import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { makeApi, type InstructorHomeResponse } from "../api/client";
import type { CandidateClassReport } from "./CandidateReportWorkspace";

export type InstructorRoster = {
  class_offering_id: string;
  cohort_id: string;
  title: string;
  members: { person_id: string; member_type: string }[];
  instructor_person_ids: string[];
};

export type InstructorSession = {
  session_id: string;
  class_offering_id: string;
  title: string;
  starts_at: string;
  ends_at: string;
  delivery_mode: string;
  status: string;
};

export type InstructorAttendance = {
  session_id: string;
  items: {
    id: string;
    person_id: string;
    status: string;
    version: number;
  }[];
};

export type InstructorClassActivity = {
  class_offering_id: string;
  items: {
    source_id: string;
    source_type: string;
    source_parent_id: string | null;
    person_id: string;
    occurred_at: string;
    state: string | null;
  }[];
  is_truncated: boolean;
};

function qualitativeState(value: string | null) {
  if (value === "TO_LEARN") return "آغاز نشده";
  if (value === "IN_LEARNING") return "در حال یادگیری";
  if (value === "LEARNING_COMPLETED") return "الزامات آموزشی تکمیل شده";
  return "وضعیت آموزشی مشخص نیست";
}

function attendanceLabel(value: string | undefined) {
  if (value === "PRESENT") return "حاضر";
  if (value === "ABSENT") return "غایب (ثبت‌شده)";
  if (value === undefined) return "ثبت نشده؛ به معنی غیبت نیست";
  return "وضعیت ثبت‌شده نامعتبر است";
}

export function InstructorClassView({
  classes,
  classId,
  onClassChange,
  roster,
  sessions,
  sessionId,
  onSessionChange,
  attendance,
  activity,
  personId,
  onPersonChange,
  report,
  busy = false,
  errors = [],
  practiceFeedbackPending,
  assignmentFeedbackPending,
}: {
  classes: InstructorHomeResponse["assigned_classes"];
  classId?: string;
  onClassChange: (id: string) => void;
  roster?: InstructorRoster;
  sessions?: InstructorSession[];
  sessionId?: string;
  onSessionChange: (id: string) => void;
  attendance?: InstructorAttendance;
  activity?: InstructorClassActivity;
  personId?: string;
  onPersonChange: (id: string) => void;
  report?: CandidateClassReport;
  busy?: boolean;
  errors?: string[];
  practiceFeedbackPending: number;
  assignmentFeedbackPending: number;
}) {
  const learners = (roster?.members ?? []).filter((m) => m.member_type === "CANDIDATE");
  const recorded = new Map(
    attendance?.items.map((item) => [item.person_id, item.status]) ?? [],
  );

  return (
    <main className="page-shell" data-testid="instructor-class-workspace">
      <section className="panel">
        <p className="eyebrow">CLASS WORKSPACE</p>
        <h2>عملیات کلاس من</h2>
        <p className="muted">
          این نما تنها داده‌های کلاس تخصیص‌یافته را می‌خواند. تصمیم درباره شایستگی
          و تأیید Evidence در این صفحه انجام نمی‌شود.
        </p>
        {classes.length === 0 ? (
          <p className="muted">هنوز کلاسی به این مدرس واگذار نشده است.</p>
        ) : (
          <div className="form-stack">
            <label htmlFor="instructor-class-select">کلاس تخصیص‌یافته</label>
            <select
              id="instructor-class-select"
              value={classId ?? ""}
              onChange={(event) => onClassChange(event.target.value)}
            >
              {classes.map((item) => (
                <option key={item.id} value={item.id}>{item.title}</option>
              ))}
            </select>
          </div>
        )}
        {busy ? <p role="status">در حال دریافت اطلاعات کلاس...</p> : null}
        {errors.map((error, index) => (
          <p className="error" role="alert" key={index}>{error}</p>
        ))}
      </section>

      {classId && !busy && errors.length === 0 ? (
        <>
          <section className="grid-two">
            <article className="panel">
              <h2>فراگیران کلاس</h2>
              {!roster ? <p className="muted">فهرست هنوز در دسترس نیست.</p> : null}
              {roster && learners.length === 0 ? (
                <p className="muted">هنوز فراگیری در این کلاس ثبت نشده است.</p>
              ) : null}
              <div className="stack">
                {learners.map((learner) => (
                  <div className="task-card" key={learner.person_id}>
                    <span dir="ltr">{learner.person_id}</span>
                    <span className="state state-muted">فراگیر</span>
                  </div>
                ))}
              </div>
            </article>
            <article className="panel">
              <h2>صف بازخورد مدرس</h2>
              <p className="muted">
                این شمارش‌ها از نمای موجود مدرس برای همه کلاس‌های تخصیص‌یافته آمده‌اند.
                ثبت بازخورد در همان فضای عملیاتی اصلی مدرس انجام می‌شود.
              </p>
              <p>تلاش‌های تمرینی بدون بازخورد: {practiceFeedbackPending}</p>
              <p>تکالیف ارسالی بدون بازخورد: {assignmentFeedbackPending}</p>
            </article>
          </section>

          <section className="panel">
            <h2>حضور و غیاب جلسه</h2>
            {sessions?.length ? (
              <div className="form-stack">
                <label htmlFor="instructor-session-select">انتخاب جلسه</label>
                <select
                  id="instructor-session-select"
                  value={sessionId ?? ""}
                  onChange={(event) => onSessionChange(event.target.value)}
                >
                  {sessions.map((item) => (
                    <option key={item.session_id} value={item.session_id}>
                      {item.title}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <p className="muted">هنوز جلسه‌ای برای کلاس ثبت نشده است.</p>
            )}
            <div className="stack">
              {sessionId && roster && attendance
                ? learners.map((learner) => (
                    <div className="task-card" key={learner.person_id}>
                      <span dir="ltr">{learner.person_id}</span>
                      <span className="state state-muted">
                        {attendanceLabel(recorded.get(learner.person_id))}
                      </span>
                    </div>
                  ))
                : null}
            </div>
            <p className="muted">ثبت یا اصلاح حضور فقط در مسیر مجاز مدیر آکادمی انجام می‌شود.</p>
          </section>

          <section className="panel">
            <h2>آخرین فعالیت‌های کلاس</h2>
            {activity?.items.length === 0 ? (
              <p className="muted">هنوز فعالیتی در منابع معتبر این کلاس ثبت نشده است.</p>
            ) : null}
            <div className="stack">
              {(activity?.items ?? []).map((item) => (
                <div className="instructor-activity-row" key={`${item.source_type}-${item.source_id}`}>
                  <strong>{item.source_type}</strong>
                  <p className="muted" dir="ltr">{item.person_id} · {item.source_id}</p>
                  <p>{item.state ?? "وضعیت ثبت نشده"}</p>
                </div>
              ))}
            </div>
            {activity?.is_truncated ? (
              <p className="muted">فقط تازه‌ترین فعالیت‌ها نمایش داده شده‌اند.</p>
            ) : null}
          </section>

          <section className="panel">
            <h2>کارنامه کیفی فراگیر</h2>
            {learners.length > 0 ? (
              <div className="form-stack">
                <label htmlFor="instructor-report-person">انتخاب فراگیر کلاس</label>
                <select
                  id="instructor-report-person"
                  value={personId ?? ""}
                  onChange={(event) => onPersonChange(event.target.value)}
                >
                  {learners.map((learner) => (
                    <option key={learner.person_id} value={learner.person_id}>
                      {learner.person_id}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <p className="muted">هنوز فراگیری برای انتخاب وجود ندارد.</p>
            )}
            {report ? (
              <div className="stack">
                {report.subjects.map((subject) => (
                  <article className="instructor-report-card" key={subject.capability_version_id}>
                    <strong>{subject.capability_name ?? "عنوان درس در دسترس نیست"}</strong>
                    <p>{qualitativeState(subject.learning_state)}</p>
                    <p className="muted">
                      اثبات رسمی: {subject.proof_state ?? "وضعیت مستقل در دسترس نیست"}
                    </p>
                    <p className="muted">
                      Claim انسانی: {subject.reviewed_claim?.claim_state ?? "ثبت نشده"}
                    </p>
                    <p>فعالیت‌های ثبت‌شده: {subject.learning_sources.length}</p>
                    <p>بازخوردهای ثبت‌شده: {subject.feedback_sources.length}</p>
                  </article>
                ))}
                {report.subjects.length === 0 ? (
                  <p className="muted">هنوز درس قابل‌نمایشی ثبت نشده است.</p>
                ) : null}
              </div>
            ) : null}
          </section>
        </>
      ) : null}
    </main>
  );
}

export function InstructorClassWorkspace({
  accessToken,
  organizationId,
  personId,
  data,
}: {
  accessToken: string;
  organizationId: string;
  personId: string;
  data: InstructorHomeResponse;
}) {
  const api = makeApi(accessToken);
  const [chosenClassId, setChosenClassId] = useState<string>();
  const [chosenSessionId, setChosenSessionId] = useState<string>();
  const [chosenPersonId, setChosenPersonId] = useState<string>();
  const classes = data.assigned_classes ?? [];
  const classId = classes.some((item) => item.id === chosenClassId)
    ? chosenClassId : classes[0]?.id;

  const roster = useQuery({
    queryKey: ["instructor-class-roster", organizationId, personId, classId],
    enabled: Boolean(classId),
    queryFn: async () => {
      const { data: result, error } = await api.GET(
        "/api/v1/class-offerings/{class_offering_id}/roster",
        { params: { path: { class_offering_id: classId ?? "" } } },
      );
      if (error || !result) throw new Error("فهرست فراگیران کلاس در دسترس نیست.");
      return result as InstructorRoster;
    },
  });
  const sessions = useQuery({
    queryKey: ["instructor-class-sessions", organizationId, personId, classId],
    enabled: Boolean(classId),
    queryFn: async () => {
      const { data: result, error } = await api.GET(
        "/api/v1/class-offerings/{class_offering_id}/sessions",
        { params: { path: { class_offering_id: classId ?? "" } } },
      );
      if (error || !result) throw new Error("دریافت جلسات کلاس ناموفق بود.");
      return result as InstructorSession[];
    },
  });
  const sessionId = sessions.data?.some((item) => item.session_id === chosenSessionId)
    ? chosenSessionId : sessions.data?.[0]?.session_id;
  const attendance = useQuery({
    queryKey: ["instructor-session-attendance", organizationId, personId, classId, sessionId],
    enabled: Boolean(classId && sessionId),
    queryFn: async () => {
      const { data: result, error } = await api.GET(
        "/api/v1/sessions/{session_id}/attendance",
        { params: { path: { session_id: sessionId ?? "" } } },
      );
      if (error || !result) throw new Error("دریافت حضور و غیاب ناموفق بود.");
      return result as InstructorAttendance;
    },
  });
  const activity = useQuery({
    queryKey: ["instructor-class-activity", organizationId, personId, classId],
    enabled: Boolean(classId),
    queryFn: async () => {
      const { data: result, error } = await api.GET(
        "/api/v1/class-offerings/{class_offering_id}/activity",
        { params: { path: { class_offering_id: classId ?? "" }, query: { limit: 50 } } },
      );
      if (error || !result) throw new Error("دریافت فعالیت‌های کلاس ناموفق بود.");
      return result as InstructorClassActivity;
    },
  });
  const learners = (roster.data?.members ?? []).filter(
    (item) => item.member_type === "CANDIDATE",
  );
  const selectedPersonId = learners.some((item) => item.person_id === chosenPersonId)
    ? chosenPersonId : learners[0]?.person_id;
  const report = useQuery({
    queryKey: ["instructor-class-report", organizationId, personId, classId, selectedPersonId],
    enabled: Boolean(classId && selectedPersonId),
    queryFn: async () => {
      const { data: result, error } = await api.GET(
        "/api/v1/class-offerings/{class_offering_id}/report-cards/{person_id}",
        {
          params: {
            path: {
              class_offering_id: classId ?? "",
              person_id: selectedPersonId ?? "",
            },
          },
        },
      );
      if (error || !result) throw new Error("دریافت کارنامه فراگیر ناموفق بود.");
      return result as CandidateClassReport;
    },
  });

  const errors = [roster, sessions, attendance, activity, report]
    .filter((query) => query.isError)
    .map((query) => query.error?.message ?? "دریافت اطلاعات ناموفق بود.");
  const busy = [roster, sessions, attendance, activity, report].some(
    (query) => query.isPending && query.fetchStatus === "fetching",
  );

  return (
    <InstructorClassView
      classes={classes}
      classId={classId}
      onClassChange={setChosenClassId}
      roster={roster.data}
      sessions={sessions.data}
      sessionId={sessionId}
      onSessionChange={setChosenSessionId}
      attendance={attendance.data}
      activity={activity.data}
      personId={selectedPersonId}
      onPersonChange={setChosenPersonId}
      report={report.data}
      busy={busy}
      errors={errors}
      practiceFeedbackPending={(data.practice_attempts ?? []).filter(
        (item) => (item.feedback_history ?? []).length === 0,
      ).length}
      assignmentFeedbackPending={(data.submissions ?? []).filter(
        (item) => !item.feedback_text,
      ).length}
    />
  );
}
